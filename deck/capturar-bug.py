#!/usr/bin/env python3
# Capturador de bugs: um botão de trás do controle do Deck (L4, R4, L5 ou R5) marca um bug na hora.
# Cada marca vira uma pasta em <saida>/AAAAMMDD-HHMMSS com:
#   tela-0.png   print no instante do aperto (gamescopectl screenshot)
#   tela-1.png   outro print 1 s depois (pra ver se o bug era de um quadro só)
#   jogo.txt     o log do jogo dos 30 s antes até 10 s depois do aperto
#   sessao.txt   as linhas do lançador no mesmo período (mem:, psi:, vigia)
#   resumo.txt   fps, objetos sem desenhar, piscadas e memória perto do aperto
# e uma linha em <saida>/indice.txt. Lê o controle pelo hidraw só olhando (não manda nada pra ele), em paralelo
# com o jogo, que também lê o hidraw direto. O jogo não usa os botões de trás.
#   python3 capturar-bug.py --log-jogo <hookshot_log.txt> --log-sessao <zelda-...log> --saida <pasta>
#                           --processo <regex do pgrep>
import collections
import datetime
import glob
import os
import re
import select
import shutil
import struct
import subprocess
import sys
import threading
import time

# Bits dos botões no relatório 0x09 do controle do Deck (28DE:1205), como no SDL (SDL_hidapi_steamdeck.c):
# palavra baixa nos bytes 8-11, alta nos 12-15.
L5, R5 = 0x00008000, 0x00010000   # palavra baixa
L4, R4 = 0x00000200, 0x00000400   # palavra alta
NOMES = {('L', L5): 'L5', ('L', R5): 'R5', ('H', L4): 'L4', ('H', R4): 'R4'}
ANTES_S, DEPOIS_S, INTERVALO_S, GUARDAR = 30, 10, 4, 100


def opcao(nome, padrao=None):
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao


LOG_JOGO = opcao('--log-jogo')
LOG_SESSAO = opcao('--log-sessao')
SAIDA = os.path.expanduser(opcao('--saida', '~/zelda-oot/bugs'))
PROCESSO = opcao('--processo', r'^\./(bin/)?hookshot$')

tamanhos = collections.deque(maxlen=ANTES_S + 5)   # (hora, tamanho do log do jogo), um por segundo


def tamanho(caminho):
    try:
        return os.path.getsize(caminho)
    except (OSError, TypeError):
        return 0


def log_do_jogo():
    # No 2.2 o jogo não cria hookshot_log.txt: a saída dele vai pro log do lançador.
    return LOG_JOGO if LOG_JOGO and os.path.exists(LOG_JOGO) else LOG_SESSAO


def jogo_aberto():
    return subprocess.run(['pgrep', '-f', PROCESSO], capture_output=True).returncode == 0


def controle():
    for dev in sorted(glob.glob('/dev/hidraw*')):
        try:
            sysfs = f'/sys/class/hidraw/{os.path.basename(dev)}/device'
            if '000028DE:00001205' not in open(f'{sysfs}/uevent').read().upper():
                continue
            if ':1.2/' not in os.path.realpath(sysfs) + '/':
                continue
            return os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            pass
    return None


def print_tela(caminho):
    subprocess.run(['gamescopectl', 'screenshot', caminho], capture_output=True, timeout=10)


def copiar_trecho(origem, destino, inicio):
    try:
        with open(origem, 'rb') as f, open(destino, 'wb') as d:
            f.seek(inicio)
            shutil.copyfileobj(f, d)
    except OSError:
        pass


def resumo(pasta, botao, hora):
    linhas = [f'bug marcado {hora:%Y-%m-%d %H:%M:%S} pelo botão {botao}']
    try:
        txt = open(f'{pasta}/jogo.txt', errors='replace').read().splitlines()
    except OSError:
        txt = []
    fps = [float(m.group(1)) for l in txt if (m := re.search(r'\(([0-9.]+) fps over', l))]
    if fps:
        linhas.append('fps nos 5 s antes e depois: ' + ' '.join(f'{x:.1f}' for x in fps[-10:]))
    faltando = [float(m.group(1)) for l in txt if (m := re.search(r'([0-9.]+) draws left out', l))]
    if faltando:
        linhas.append('objetos sem desenhar por quadro (programa não pronto): ' + ' '.join(f'{x:g}' for x in faltando[-10:]))
    for padrao in (r'aflash:', r'textures retired', r'starts empt', r'CRASH|FATAL|device lost', r'program loads at create'):
        achados = [l for l in txt if re.search(padrao, l)]
        if achados:
            linhas.append(f'{padrao}: {len(achados)} linhas; última: {achados[-1][:220]}')
    try:
        sessao = open(f'{pasta}/sessao.txt', errors='replace').read().splitlines()
        linhas += [l[:200] for l in sessao if l.startswith(('mem:', 'psi:', 'vigia'))][-6:]
    except OSError:
        pass
    open(f'{pasta}/resumo.txt', 'w').write('\n'.join(linhas) + '\n')
    return linhas


def capturar(botao):
    hora = datetime.datetime.now()
    pasta = f'{SAIDA}/{hora:%Y%m%d-%H%M%S}'
    os.makedirs(pasta, exist_ok=True)
    print_tela(f'{pasta}/tela-0.png')        # primeiro o print, antes de qualquer outra coisa
    print(f'bug: marcado {hora:%T} ({botao}) em {pasta}', flush=True)
    time.sleep(1)
    print_tela(f'{pasta}/tela-1.png')
    agora = time.time()
    inicio = next((t for h, t in tamanhos if h >= agora - 1 - ANTES_S), 0)
    sessao_antes = tamanho(LOG_SESSAO)
    time.sleep(DEPOIS_S - 1)
    copiar_trecho(log_do_jogo(), f'{pasta}/jogo.txt', inicio)
    # O log do lançador cresce devagar (uma linha mem: a cada 5 s): os últimos 60 KB cobrem bem mais que 40 s.
    copiar_trecho(LOG_SESSAO, f'{pasta}/sessao.txt', max(0, sessao_antes - 60000))
    linhas = resumo(pasta, botao, hora)
    with open(f'{SAIDA}/indice.txt', 'a') as f:
        f.write(f'{hora:%Y-%m-%d %H:%M:%S} {botao} {os.path.basename(pasta)} | ' + ' | '.join(linhas[1:3]) + '\n')
    pastas = sorted(p for p in glob.glob(f'{SAIDA}/2*') if os.path.isdir(p))
    for velha in pastas[:-GUARDAR]:
        shutil.rmtree(velha, ignore_errors=True)


def main():
    os.makedirs(SAIDA, exist_ok=True)
    fd, antes, ultimo, ultima_amostra, ultima_checagem = None, set(), 0.0, 0.0, 0.0
    inicio = time.time()
    while True:
        agora = time.time()
        if agora - ultima_amostra >= 1:
            tamanhos.append((agora, tamanho(log_do_jogo())))
            ultima_amostra = agora
        if agora - ultima_checagem >= 5:
            ultima_checagem = agora
            if agora - inicio > 60 and not jogo_aberto():
                return
        if fd is None:
            fd = controle()
            if fd is None:
                time.sleep(2)
                continue
        try:
            if not select.select([fd], [], [], 0.5)[0]:
                continue
            b = os.read(fd, 64)
        except OSError:
            os.close(fd)
            fd = None
            continue
        if len(b) < 16 or b[2] != 0x09:
            continue
        baixa, alta = struct.unpack_from('<II', b, 8)
        apertados = {n for (w, bit), n in NOMES.items() if (baixa if w == 'L' else alta) & bit}
        novos = apertados - antes
        antes = apertados
        if novos and agora - ultimo >= INTERVALO_S:
            ultimo = agora
            threading.Thread(target=capturar, args=(sorted(novos)[0],), daemon=True).start()


if __name__ == '__main__':
    main()

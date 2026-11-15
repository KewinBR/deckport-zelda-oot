#!/usr/bin/env python3
# Tabela de tamanhos (RESTBL) dos ícones de botão para o jogo montado, feita na abertura pelo rodar-zelda.sh.
# A tabela do mod de texturas (prompts-rsizetable.zs) traz os tamanhos das texturas reduzidas; a do Hookshot
# (prompts/rsizetable-hookshot.zs, a que o builder gerou) traz a entrada da fonte dos ícones, que muda de versão para
# versão: 20488 bytes no 2.1, 55376 no 2.2. Com a entrada de uma versão mais velha a fonte fica cortada e ícones somem
# (2026-11-13, 2.2: o botão de ação do anel vazio). Mesmo cálculo do projetos/zelda-oot/ferramentas/tabela_prompts.py,
# com o zstd de linha de comando (o SteamOS não tem o módulo zstandard).
#   juntar-tabela-prompts.py <tabela do mod .zs> <rsizetable-hookshot.zs> <saída .zs>
import os
import struct
import subprocess
import sys
import zlib

FONTE = b"Font2/Scalable/External.Nin_Ounce_NVN2.bfotf"


def ler(caminho):
    b = bytearray(subprocess.run(['zstd', '-dcq', caminho], capture_output=True, check=True).stdout)
    if b[:6] != b"RESTBL":
        raise SystemExit(caminho + ": não é uma tabela RESTBL")
    return b


def entrada(b, crc):
    n, = struct.unpack_from("<I", b, 14)
    for i in range(n):
        if struct.unpack_from("<I", b, 22 + 8 * i)[0] == crc:
            return 22 + 8 * i + 4
    raise SystemExit("sem entrada da fonte dos ícones na tabela")


def main():
    mod, hookshot, saida = sys.argv[1:4]
    a, h = ler(mod), ler(hookshot)
    crc = zlib.crc32(FONTE)
    antes, = struct.unpack_from("<I", a, entrada(a, crc))
    novo, = struct.unpack_from("<I", h, entrada(h, crc))
    struct.pack_into("<I", a, entrada(a, crc), max(antes, novo))
    tmp = saida + ".novo"
    # O jogo precisa do tamanho descompactado no cabeçalho do frame, como nas tabelas dele (e sem checksum). Pelo stdin o
    # zstd não escreve o tamanho: a primeira versão (2026-11-13) saiu assim e o jogo crashava ao carregar o terreno.
    subprocess.run(['zstd', '-19', '-qf', '--no-check', '--stream-size=%d' % len(a), '-o', tmp], input=bytes(a), check=True)
    os.replace(tmp, saida)
    print("tabela dos ícones: fonte %d -> %d bytes em %s" % (antes, max(antes, novo), saida))


if __name__ == "__main__":
    main()

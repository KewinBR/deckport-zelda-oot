"""Atualização automática do Deckport, sem tela. O lançador (rodar-zelda.sh) chama:

    atualizar.py aplicar     na abertura, antes do jogo: põe no lugar uma versão já baixada (segundos) e para uma
                             remontagem em andamento. Sai com 10 quando trocou o lançador ou a pasta do jogo (o lançador
                             abre de novo, com os arquivos novos).
    atualizar.py verificar   em segundo plano (systemd-run --user, fora da sessão do jogo): vê se há versão nova no
                             GitHub, baixa e confere o pacote (uns 10 MB) e o deixa pronto para a próxima abertura.
                             Se a versão nova muda a base (o Longshot), o jogo precisa ser montado de novo: espera o jogo
                             fechar e o Deck estar na tomada, e monta com o pacote novo numa pasta ao lado (uma a duas
                             horas). A pasta em uso não é tocada até a nova estar pronta.

Nada disso roda com ZELDA_ATUALIZAR=0 ou com "atualizar": false no config.json. Log: <raiz>/logs/atualizacao.log.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nucleo  # noqa: E402

ESTADO = nucleo.APPDIR / "atualizacao"     # pacote/ (a versão nova extraída) e estado.json
PACOTE_NOVO = ESTADO / "pacote" / nucleo.APP
UNIDADE = "zelda-oot-deck-atualizar"
TROCOU = 10


def log(msg: str) -> None:
    print(time.strftime("%F %T ") + msg, flush=True)


def versao_tupla(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)) or (0,)


def ler_estado() -> dict:
    try:
        return json.loads((ESTADO / "estado.json").read_text())
    except (OSError, ValueError):
        return {}


def gravar_estado(e: dict) -> None:
    ESTADO.mkdir(parents=True, exist_ok=True)
    t = ESTADO / "estado.json.novo"
    t.write_text(json.dumps(e, indent=2, ensure_ascii=False))
    t.replace(ESTADO / "estado.json")


def base_do_pacote(pacote: Path) -> str:
    """A identidade da base do pacote ('Longshot v3.0.0-rc.5 + <soma do patch>'), pelo código dele (que é de
    outra versão: roda à parte)."""
    r = subprocess.run([sys.executable, "-I", "-c",
                        "import sys; sys.path.insert(0, sys.argv[1]); import nucleo; print(nucleo.identidade_base())",
                        str(pacote / "instalador")], stdout=subprocess.PIPE, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def jogo_aberto() -> bool:
    r = subprocess.run(["pgrep", "-f", r"^\./(bin/)?(hookshot|longshot)$"], stdout=subprocess.DEVNULL)
    if r.returncode == 0:
        return True
    try:
        return time.time() - os.stat("/tmp/zelda-abrindo").st_mtime < 60
    except OSError:
        return False


def na_tomada() -> bool:
    pasta = Path("/sys/class/power_supply")
    achou_bateria = False
    for p in pasta.glob("*"):
        try:
            tipo = (p / "type").read_text().strip()
            if tipo == "Mains" and (p / "online").read_text().strip() == "1":
                return True
            achou_bateria |= tipo == "Battery"
        except OSError:
            continue
    return not achou_bateria   # (sem bateria nenhuma: um PC)


def ligado() -> bool:
    return os.environ.get("ZELDA_ATUALIZAR", "1") != "0" and nucleo.ler_config().get("atualizar", True) is not False


# ---- verificar: baixar a versão nova
def ultimo_release() -> dict:
    # (ZELDA_RELEASE_URL: um JSON no mesmo formato, para testar sem publicar; file:// também serve)
    url = os.environ.get("ZELDA_RELEASE_URL") or f"https://api.github.com/repos/{nucleo.REPO}/releases/latest"
    pedido = urllib.request.Request(url,
                                    headers={"User-Agent": "deckport-zelda-oot", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(pedido, timeout=20) as r:
        return json.load(r)


def baixar_pacote(rel: dict) -> Path:
    tag = rel["tag_name"]
    anexo = next(a for a in rel["assets"] if a["name"].startswith(nucleo.APP + "-") and a["name"].endswith(".tar.gz"))
    ESTADO.mkdir(parents=True, exist_ok=True)
    arq = ESTADO / anexo["name"]
    pedido = urllib.request.Request(anexo["browser_download_url"], headers={"User-Agent": "deckport-zelda-oot"})
    h = hashlib.sha256()
    with urllib.request.urlopen(pedido, timeout=60) as r, open(arq, "wb") as f:
        for bloco in iter(lambda: r.read(1 << 20), b""):
            f.write(bloco)
            h.update(bloco)
    digest = (anexo.get("digest") or "").removeprefix("sha256:")
    if digest and digest != h.hexdigest():
        arq.unlink(missing_ok=True)
        raise RuntimeError(f"o pacote {anexo['name']} não confere com a soma do GitHub")
    destino = ESTADO / "pacote.novo"
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir()
    with tarfile.open(arq) as t:
        try:
            t.extractall(destino, filter="data")
        except TypeError:   # (Python sem o filtro)
            if any(m.name.startswith(("/", "..")) or ".." in Path(m.name).parts for m in t.getmembers()):
                raise RuntimeError("o pacote baixado tem caminhos fora da pasta")
            t.extractall(destino)
    arq.unlink(missing_ok=True)
    if not (destino / nucleo.APP / "instalador" / "nucleo.py").is_file():
        raise RuntimeError("o pacote baixado não tem o instalador")
    shutil.rmtree(ESTADO / "pacote", ignore_errors=True)
    destino.replace(ESTADO / "pacote")
    log(f"versão {tag} baixada e conferida")
    return PACOTE_NOVO


def verificar() -> int:
    c = nucleo.ler_config()
    if not c.get("raiz") or not c.get("jogo"):
        return 0   # sem instalação feita pelo instalador: não há o que atualizar
    atual = c.get("versao") or nucleo.versao_do_pacote()
    try:
        rel = ultimo_release()
    except Exception as e:  # sem rede: tenta na próxima abertura
        log(f"sem como ver se há versão nova ({e})")
        return 0
    tag = rel.get("tag_name", "")
    if versao_tupla(tag) <= versao_tupla(atual):
        return 0
    e = ler_estado()
    if e.get("versao") == tag and e.get("tipo") in ("leve", "pronto") and nucleo.versao_do_pacote(PACOTE_NOVO) == tag:
        return 0   # já pronta: entra na próxima abertura
    if nucleo.versao_do_pacote(PACOTE_NOVO) != tag:
        log(f"há versão nova: {tag} (instalada {atual})")
        baixar_pacote(rel)
    base_nova = base_do_pacote(PACOTE_NOVO)
    if not base_nova or not (PACOTE_NOVO / "instalador" / "atualizar.py").is_file():
        log(f"o pacote de {tag} não traz a atualização automática; fica como está")
        return 0
    if base_nova == c.get("base"):
        gravar_estado({"versao": tag, "tipo": "leve"})
        log(f"{tag} fica para a próxima abertura")
        return 0
    gravar_estado({"versao": tag, "tipo": "remontar", "base": base_nova})
    log(f"{tag} muda a base ({c.get('base')} -> {base_nova}): o jogo será montado de novo quando ele estiver fechado "
        f"e o Deck na tomada")
    avisou = False
    while jogo_aberto() or not na_tomada():
        if not avisou:
            log("esperando o jogo fechar e o Deck ir para a tomada")
            avisou = True
        time.sleep(60)
    # a montagem roda com o código do pacote novo, que sabe baixar e montar a base dele
    r = subprocess.run([sys.executable, "-I", str(PACOTE_NOVO / "instalador" / "atualizar.py"), "remontar"])
    return r.returncode


# ---- remontar (roda com o código do pacote novo)
def remontar() -> int:
    c = nucleo.ler_config()
    raiz, jogo = Path(c["raiz"]), Path(c["jogo"])
    novo = raiz / "jogo-novo"
    if not nucleo.exefs_da_pasta(jogo):
        log(f"a pasta {jogo} não guarda o código do jogo: rode o instalador com o .nup para a versão nova")
        gravar_estado({**ler_estado(), "erro": "sem exefs"})
        return 1
    livre = shutil.disk_usage(raiz).free
    if livre < nucleo.ESPACO_REFAZER:
        log(f"sem espaço para montar a versão nova: {livre / 1024 ** 3:.0f} GB livres, precisa de "
            f"{nucleo.ESPACO_REFAZER / 1024 ** 3:.0f} GB em {raiz}. Tenta de novo na próxima abertura")
        return 1
    origem = nucleo.Jogo(jogo, 0, "pasta", nucleo.versao_da_pasta(jogo))
    try:   # o idioma do jogo que o jogador escolheu na instalação
        linhas = [l.strip() for l in (jogo / "language.txt").read_text().splitlines()]
        idioma = next((l for l in linhas if l and not l.startswith("#")), "pt-BR")
    except OSError:
        idioma = "pt-BR"
    inst = nucleo.Instalacao(origem, nucleo.Local("", raiz.parent, livre, False), nucleo.Progresso(),
                             lambda *a: None, idioma)
    inst.raiz = raiz
    ini = time.time()
    log(f"montando {nucleo.identidade_base()} em {novo}")
    try:
        hs = inst._hookshot()
        if nucleo.marca_da_pasta(novo) != nucleo.identidade_base():
            shutil.rmtree(novo, ignore_errors=True)
            inst._montar(hs, novo)
            inst._renderizador(novo)
    except Exception as e:
        log(f"a montagem parou: {e}")
        return 1
    gravar_estado({**ler_estado(), "tipo": "pronto", "novo": str(novo)})
    log("montagem pronta em %.0f min; entra na próxima abertura" % ((time.time() - ini) / 60))
    return 0


# ---- aplicar (na abertura)
def parar_remontagem() -> None:
    amb = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
    r = subprocess.run(["systemctl", "--user", "is-active", "--quiet", UNIDADE], env=amb)
    if r.returncode == 0:
        subprocess.run(["systemctl", "--user", "stop", UNIDADE], env=amb)
        log("atualização em segundo plano parada para o jogo abrir (continua depois)")


def trocar_pasta(c: dict, novo: Path) -> None:
    raiz, jogo = Path(c["raiz"]), Path(c["jogo"])
    # (a pasta que o jogador montou antes do port, jogo_de_fora, fica onde está, intacta: a nova vai para raiz/jogo)
    final = nucleo.trocar_jogo(raiz, novo, jogo)
    c.update({"jogo": str(final), "jogo_de_fora": False, "base": base_do_pacote(PACOTE_NOVO)})
    nucleo.gravar_config(c)
    nucleo.CAMINHOS.write_text(f'ZELDA_BASE="{raiz}"\nZELDA_JOGO="{final}"\nZELDA_SCRIPTS="{nucleo.APPDIR / "deck"}"\n')


def aplicar() -> int:
    parar_remontagem()
    e = ler_estado()
    if not e or nucleo.versao_do_pacote(PACOTE_NOVO) != e.get("versao"):
        return 0
    c = nucleo.ler_config()
    if not c.get("raiz") or versao_tupla(e["versao"]) <= versao_tupla(c.get("versao") or nucleo.versao_do_pacote()):
        shutil.rmtree(ESTADO, ignore_errors=True)
        return 0
    if e.get("tipo") == "remontar":
        return 0   # ainda não montado: segue na versão atual
    if e.get("tipo") == "pronto":
        novo = Path(e["novo"])
        if nucleo.marca_da_pasta(novo) != base_do_pacote(PACOTE_NOVO):
            log(f"a pasta {novo} não está completa; a montagem continua depois")
            return 0
        trocar_pasta(c, novo)
    # o port novo no lugar (lançador, ajudantes, ferramentas, patches, instalador), com o código do pacote novo. (O
    # renderizador está na pasta do jogo, montado com ela: muda só pela remontagem)
    r = subprocess.run([sys.executable, "-I", "-c",
                        "import sys; sys.path.insert(0, sys.argv[1]); import nucleo; nucleo.instalar_app()",
                        str(PACOTE_NOVO / "instalador")])
    if r.returncode != 0:
        log("não deu para copiar a versão nova; segue na atual")
        return 0
    c["versao"] = e["versao"]
    nucleo.gravar_config(c)
    shutil.rmtree(ESTADO, ignore_errors=True)
    log(f"atualizado para {e['versao']}")
    return TROCOU


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("aplicar", "verificar", "remontar"):
        print(__doc__)
        return 2
    if not ligado():
        return 0
    try:
        return {"aplicar": aplicar, "verificar": verificar, "remontar": remontar}[sys.argv[1]]()
    except Exception as e:  # a atualização nunca impede o jogo de abrir
        log(f"erro na atualização ({sys.argv[1]}): {e!r}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

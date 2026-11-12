"""Desinstala o Deckport do Zelda: Ocarina of Time.

    python3 ~/.local/share/zelda-oot-deck/instalador/desinstalar.py            tira o port e mantém o jogo montado
    python3 ~/.local/share/zelda-oot-deck/instalador/desinstalar.py --com-jogo tira também o jogo montado pelo instalador

O que sai: o atalho da Steam e as artes dele, o lançador e o Hookshot baixado (~/.local/share/zelda-oot-deck), a
configuração (~/.config/zelda-oot-deck), os mods gerados e os logs.
O que fica: os saves (~/.local/share/hookshot), o .nup do jogo e, sem --com-jogo, a pasta do jogo montada, que volta
ao renderizador original do Hookshot. Uma pasta que o jogador já tinha montado antes do port nunca é apagada.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import steam  # noqa: E402

APP = "zelda-oot-deck"
CONFIG_DIR = Path.home() / ".config" / APP
APPDIR = Path.home() / ".local" / "share" / APP


def devolver_original(jogo: Path) -> None:
    """Volta o renderizador e a tabela dos ícones que o Hookshot tinha posto na pasta do jogo."""
    guardado = jogo / "bin" / "hookshot_vk.so.hookshot"
    if guardado.exists():
        guardado.replace(jogo / "bin" / "hookshot_vk.so")
        print(f"renderizador original do Hookshot de volta em {jogo / 'bin'}")
    tabela = jogo / "prompts" / "rsizetable-hookshot.zs"
    if tabela.exists():
        tabela.replace(jogo / "prompts" / "rsizetable.zs")


def main() -> int:
    com_jogo = "--com-jogo" in sys.argv[1:]
    try:
        c = json.loads((CONFIG_DIR / "config.json").read_text())
    except (OSError, ValueError):
        c = {}
    raiz = Path(c["raiz"]) if c.get("raiz") else None
    jogo = Path(c["jogo"]) if c.get("jogo") else None
    de_fora = bool(c.get("jogo_de_fora"))

    n = steam.remover_atalho()
    print(f"atalho da Steam: {n} entrada(s) removida(s)")

    if jogo and jogo.is_dir():
        dentro = raiz is not None and jogo.resolve().is_relative_to(raiz.resolve())
        if com_jogo and dentro and not de_fora:
            shutil.rmtree(jogo)
            print(f"jogo montado apagado: {jogo}")
        else:
            devolver_original(jogo)
            print(f"jogo mantido: {jogo}")

    if raiz and raiz.is_dir() and raiz.name == APP:
        for item in raiz.iterdir():
            if jogo and item.resolve() == jogo.resolve():
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()
        if not any(raiz.iterdir()):
            raiz.rmdir()
        print(f"mods e logs apagados em {raiz}")

    for pasta in (APPDIR, CONFIG_DIR, Path.home() / ".local" / "share" / f"{APP}-instalador"):
        if pasta.is_dir():
            shutil.rmtree(pasta)
            print(f"apagado: {pasta}")
    print("Pronto. Os saves continuam em ~/.local/share/hookshot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

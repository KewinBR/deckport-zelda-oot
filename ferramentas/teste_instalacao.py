"""Roda a instalação sem tela, para teste: mostra cada mudança de etapa e de progresso.

    python3 ferramentas/teste_instalacao.py <.nup ou pasta montada> <destino> [--parar-na-etapa N --depois S] [--sem-atalho]

Use com HOME apontando para uma pasta de teste: o port, a config e o Hookshot baixado vão para dentro dela, e nada do
jogo de verdade nem o atalho da Steam do jogador são tocados (com --sem-atalho).
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "instalador"))
import nucleo  # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    origem, destino = Path(args[0]), Path(args[1])
    parar = int(args[args.index("--parar-na-etapa") + 1]) if "--parar-na-etapa" in args else -1
    depois = float(args[args.index("--depois") + 1]) if "--depois" in args else 0
    if origem.is_dir():
        jogo = nucleo.Jogo(origem, 0, "pasta", nucleo.versao_da_pasta(origem))
    else:
        jogo = nucleo.Jogo(origem, origem.stat().st_size, "nup")
    destino.mkdir(parents=True, exist_ok=True)
    local = nucleo.Local("teste", destino, shutil.disk_usage(destino).free, False)
    if "--sem-atalho" in args:
        def atalho(raiz, port):
            print("(atalho da Steam pulado)")
    else:
        import steam
        atalho = steam.criar_atalho
    p = nucleo.Progresso()
    inst = nucleo.Instalacao(jogo, local, p, atalho)
    inicio = time.time()
    inst.start()
    visto, na_etapa = None, None
    while inst.is_alive():
        time.sleep(2)
        with p._trava:
            estado = (p.etapa, round(p.fracao, 2), p.texto)
            total, resta = p.total, p.restante_s
        if estado != visto:
            print(f"{time.time() - inicio:7.0f}s etapa {estado[0]} {estado[1]:.2f} total {total:.3f} "
                  f"resta {resta:.0f}s {estado[2]}", flush=True)
            visto = estado
        if estado[0] == parar:
            na_etapa = na_etapa or time.time()
            if time.time() - na_etapa >= depois:
                print("cancelando, como pedido", flush=True)
                inst.cancelar()
                inst.join(60)
                break
    print(f"fim em {time.time() - inicio:.0f}s: pronto={p.pronto} erro={p.erro!r}")
    return 0 if p.pronto or parar >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())

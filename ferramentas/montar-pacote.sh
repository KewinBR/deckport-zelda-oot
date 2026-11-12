#!/usr/bin/env bash
# Monta o pacote da versão: dist/zelda-oot-deck-vX.Y.Z.tar.gz com o renderizador do port (compilado na VPS), o lançador, os ajudantes, as ferramentas dos mods e o instalador. Nada do jogo entra.
#   bash ferramentas/montar-pacote.sh v0.1.0
set -euo pipefail
versao=${1:?versão, ex.: v0.1.0}
raiz=$(cd -- "$(dirname -- "$0")/.." && pwd)
vps=${VPS:-kewin-vps}
dist=$raiz/dist
pkg=$dist/zelda-oot-deck
rm -rf "$pkg"; mkdir -p "$pkg/renderizador"
scp -q "$vps:zelda-oot/hookshot_vk-210.so" "$pkg/renderizador/hookshot_vk.so"
cp -r "$raiz/instalador" "$raiz/deck" "$raiz/arte" "$raiz/patches" "$pkg/"
cp "$raiz/rodar-zelda.sh" "$raiz/instalar.sh" "$raiz/LICENSE" "$raiz/README.md" "$raiz/README.pt-BR.md" "$pkg/"
rm -rf "$pkg/instalador/__pycache__"
echo "$versao" > "$pkg/VERSAO"
# fim de linha do Linux em tudo o que roda no Deck (no Windows a cópia de trabalho pode estar com CRLF)
find "$pkg" -type f \( -name "*.sh" -o -name "*.py" -o -name "*.h" -o -name "*.patch" -o -name "*.md" -o -name "*.Dockerfile" \) -exec sed -i 's/\r$//' {} +
# conferência: nenhum arquivo do jogo (texturas, pacotes, tabelas, imagem do executável, dados de save)
if find "$pkg" -type f | grep -qiE '\.(nup|nsp|xci|bntx|zs|bfotf|blarc|byml|bgyml|sarc|bin)$'; then
    echo "ERRO: arquivo do jogo no pacote:"; find "$pkg" -type f | grep -iE '\.(nup|nsp|xci|bntx|zs|bfotf|blarc|byml|bgyml|sarc|bin)$'; exit 1
fi
# tar pelo Python: no Windows o tar perde o bit de execução; aqui os executáveis saem 755 e o resto 644.
python - "$dist" "$versao" <<'PY'
import os, sys, tarfile
dist, versao = sys.argv[1], sys.argv[2]
exe = {"rodar-zelda.sh", "instalar.sh", "renderizador/hookshot_vk.so"}
def ajusta(ti):
    rel = ti.name.split("/", 1)[1] if "/" in ti.name else ""
    ti.mode = 0o755 if ti.isdir() or rel in exe else 0o644
    ti.uid = ti.gid = 0; ti.uname = ti.gname = ""
    return ti
with tarfile.open(os.path.join(dist, f"zelda-oot-deck-{versao}.tar.gz"), "w:gz") as t:
    t.add(os.path.join(dist, "zelda-oot-deck"), "zelda-oot-deck", filter=ajusta)
PY
ls -la "$dist/zelda-oot-deck-$versao.tar.gz"

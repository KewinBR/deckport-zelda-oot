#!/bin/bash
# Compila só o longshot_vk.so (renderizador Deckport) da árvore ls-220 na imagem deckport-build:noble
# (imagem-build/Dockerfile: Ubuntu 24.04, glibc 2.39, roda no Deck; pacotes já instalados, sem rede para apt).
# Log em ~/zelda-oot/build-vk-ls.log
set -e
# A marca do port nao pode faltar: sem o menu e a tela de abertura do Deckport na arvore, nao compila.
for m in "dp::paint_startup" "dp::paint(c)"; do
  grep -q "$m" ${ARVORE:-$HOME/zelda-oot/ls-220}/gpu/vk/vk_menu.cpp || { echo "ERRO: falta $m em vk_menu.cpp. Rode patches/patch_menu_deckport.py e patches/patch_tela_abertura.py na arvore."; exit 1; }
done
nice -n 15 docker run --rm -v ${ARVORE:-$HOME/zelda-oot/ls-220}:/src -v $HOME/zelda-oot/src:$HOME/zelda-oot/src -w /src -e HOME=/tmp deckport-build:noble bash -c "
set -e
bash scripts/linux/deps.sh
if [ -f builder/linux/linux_tools.py ]; then
  # (Longshot rc.5 em diante: as ferramentas vêm do tools.lock, baixadas pelo linux_tools.py, que exporta EMSDK, RX_CPM etc.)
  export LONGSHOT_BUILDER_HOME=/src/build-linux/builder-home
  eval \"\$(/src/build-linux/deps/python/bin/python3 -I builder/linux/linux_tools.py env --install)\"
else
  export EMSDK=/src/build-linux/deps/emsdk RX_CPM=/src/build-linux/deps/cpm
fi
OOT_WORK=/src/build-linux/vk-work RX_MARCH=x86-64-v3 RX_VK_ONLY=1 RX_RELEASE=1 /src/build-linux/deps/python/bin/python3 -I nx2/build.py --standalone --jobs 6
ls -la /src/build-linux/vk-work/sa/build/longshot_vk.so
chown -R $(id -u):$(id -g) /src/build-linux
"

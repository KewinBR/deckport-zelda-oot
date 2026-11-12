#!/usr/bin/env bash
# Traz do repositório de trabalho (steam-deck, privado) o que este repositório publica: o lançador, os ajudantes do
# Deck, as ferramentas dos mods e os patches do renderizador. Roda no PC do Kewin antes de montar um pacote.
set -euo pipefail
raiz=$(cd -- "$(dirname -- "$0")/.." && pwd)
Z=${ZELDA_TRABALHO:-/c/Dev/steam-deck/projetos/zelda-oot}
SC=${SCRIPTS_TRABALHO:-/c/Dev/steam-deck/scripts}
mkdir -p "$raiz/deck/ferramentas" "$raiz/patches/deckport_menu"
cp "$Z/rodar-zelda.sh" "$raiz/rodar-zelda.sh"
cp "$SC/ligar-imu.py" "$SC/congelar-no-menu-steam.py" "$SC/sem-thp.py" "$raiz/deck/"
cp "$Z/ferramentas/reduzir_texturas.py" "$Z/ferramentas/reduzir_vegetacao.py" "$Z/ferramentas/tabela_prompts.py" "$raiz/deck/ferramentas/"
cp "$Z"/patches/patch_*.py "$Z"/patches/deckport-210.patch "$raiz/patches/"
cp "$Z"/patches/deckport_menu/vk_deckport_menu.h "$Z"/patches/deckport_menu/vk_deckport_startup.h "$raiz/patches/deckport_menu/"
cp "$Z/imagem-build.Dockerfile" "$Z/build-vk-210.sh" "$raiz/patches/"
echo sincronizado

#!/usr/bin/env bash
# Traz do repositório de trabalho (steam-deck, privado) o que este repositório publica: o lançador, os ajudantes do
# Deck, as ferramentas dos mods e os patches do renderizador. Roda no PC do Kewin antes de montar um pacote.
set -euo pipefail
raiz=$(cd -- "$(dirname -- "$0")/.." && pwd)
Z=${ZELDA_TRABALHO:-/c/Dev/steam-deck/projetos/zelda-oot}
SC=${SCRIPTS_TRABALHO:-/c/Dev/steam-deck/scripts}
mkdir -p "$raiz/deck/ferramentas" "$raiz/patches/deckport_menu"
cp "$Z/rodar-zelda.sh" "$raiz/rodar-zelda.sh"
cp "$SC/ligar-imu.py" "$SC/congelar-no-menu-steam.py" "$SC/sem-thp.py" "$SC/capturar-bug.py" "$SC/juntar-tabela-prompts.py" "$raiz/deck/"
cp "$Z/ferramentas/reduzir_texturas.py" "$Z/ferramentas/reduzir_vegetacao.py" "$Z/ferramentas/tabela_prompts.py" "$raiz/deck/ferramentas/"
# O patch do renderizador sobre a base do instalador (BASE_PATCH em instalador/nucleo.py): o instalador o aplica nas
# fontes do builder do Longshot. Os patch_*.py ficam para quem quiser refazer à mão (o patch_800p.py o instalador usa).
base=$(grep '^BASE_VERSAO = ' "$raiz/instalador/nucleo.py" | cut -d'"' -f2)
rm -f "$raiz/patches/deckport-210.patch" "$raiz/patches/build-vk-210.sh"
find "$raiz/patches" -maxdepth 1 -name "deckport-longshot-*.patch" ! -name "deckport-longshot-$base.patch" -delete
cp "$Z"/patches/patch_*.py "$Z/patches/deckport-longshot-$base.patch" "$raiz/patches/"
cp "$Z"/patches/deckport_menu/vk_deckport_menu.h "$Z"/patches/deckport_menu/vk_deckport_startup.h "$raiz/patches/deckport_menu/"
cp "$Z/imagem-build.Dockerfile" "$Z/build-vk-ls.sh" "$raiz/patches/"
echo sincronizado

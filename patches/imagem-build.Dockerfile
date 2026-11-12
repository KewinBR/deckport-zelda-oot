# Ambiente de build do renderizador Deckport (hookshot_vk.so): Ubuntu 24.04 (glibc 2.39, roda no Deck: 2.41), g++ 13 do
# repositório principal, sem PPA (o Launchpad caiu em 2026-11-11 e o build parava). Pacotes do CI oficial do Hookshot.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends g++-13 libstdc++-13-dev \
  git ca-certificates curl xz-utils zstd file unzip python3 \
  build-essential gcc-12 g++-12 libstdc++-12-dev nasm meson ninja-build cmake pkg-config \
  libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxss-dev libxfixes-dev libxinerama-dev \
  libxkbcommon-dev libwayland-dev wayland-protocols libdecor-0-dev libegl-dev libgles-dev libdrm-dev libgbm-dev \
  libpulse-dev libasound2-dev libpipewire-0.3-dev libudev-dev libdbus-1-dev libxft-dev libfontconfig1-dev zlib1g-dev \
  && rm -rf /var/lib/apt/lists/* && git config --system --add safe.directory "*"

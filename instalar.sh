#!/usr/bin/env bash
# Instalador do Deckport do Zelda: Ocarina of Time, para o Modo Desktop do Steam Deck.
# Baixa a última versão do port (uns 20 MB; nada do jogo) e abre o instalador.
# Pelo Konsole:  curl -L https://github.com/KewinBR/deckport-zelda-oot/releases/latest/download/instalar.sh | bash
set -euo pipefail
repo=KewinBR/deckport-zelda-oot
dest=$HOME/.local/share/zelda-oot-deck-instalador
mkdir -p "$dest"
url=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" |
      python3 -c "import json,sys; r=json.load(sys.stdin); print(next(a['browser_download_url'] for a in r['assets'] if a['name'].startswith('zelda-oot-deck-') and a['name'].endswith('.tar.gz')))")
echo "Baixando $url"
curl -fL --progress-bar -o "$dest/pacote.tar.gz" "$url"
rm -rf "$dest/zelda-oot-deck"
tar -xzf "$dest/pacote.tar.gz" -C "$dest"
rm -f "$dest/pacote.tar.gz"
exec python3 "$dest/zelda-oot-deck/instalador/instalador.py"

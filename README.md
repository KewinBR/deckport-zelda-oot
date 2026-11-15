<p align="center"><img src="arte/logo-vertical.png" width="420" alt="The Legend of Zelda: Ocarina of Time, Deckport (STEAMDECK VERSION)"></p>

<p align="center"><a href="README.pt-BR.md">Português</a> • <b>English</b></p>

# Deckport: The Legend of Zelda: Ocarina of Time

**Deckport** is a Steam Deck port of the Ocarina of Time remake (Switch 2), with no emulator. It runs on
[Longshot](https://git.magicbean.dev/MagicBeanDev/Longshot), by MagicBeanDev, the continuation of NotRexed's Hookshot,
which recompiles the game for PC. Deckport adds the Deck-specific work: an adjusted renderer, content cuts for the
device's memory and CPU, its own menu, and an installer that needs no keyboard or mouse.

**This is a test version.** The game is playable, but it has known defects, listed below. It was opened so that more
people can test more areas of the game.

**You need your own copy of the game**, as a `.nup` file. This repository has no game files and nothing from the game
is downloaded.

## What works

- The game is playable on the Steam Deck LCD, at 20 to 30 fps in most of the areas tested (Kokiri Forest, Hyrule
  Field, Lon Lon Ranch, Castle Town, Kakariko).
- Full screen at 16:10, at the Deck's resolution.
- Steam Deck button icons in the game's texts and menus.
- A port menu in the game's style, with presets and options for textures, vegetation distance, grass and shadows.
- The Deck's gyroscope, and the Steam button pauses the game.
- Each session keeps a log with fps, memory and memory pressure, for anyone who wants to report a problem. The back
  buttons (L4, R4, L5, R5) save a screenshot and the log of that moment.

## Known defects

- **Memory at the limit.** The game uses almost all of the Deck's memory. In a session of almost an hour the swap
  filled up, and the port closed the game before the Deck could freeze. Save often.
- **Objects without textures, or missing for a few seconds,** the first time in each area, while its shaders are
  prepared.
- **Flicker.** Grass can turn white for one frame, mostly when turning the camera in open areas.
- **Wrong fog** in some areas, such as the Castle Town market.
- **The port's start-up screen is off in this version.** With Longshot's renderer it hung in front of the game in Game
  Mode, so the game now opens straight to the title screen.
- **Only the beginning of the game was tested.** Other Deck owners report GPU hangs in later areas.
- Building the game on the Deck itself takes one to two hours. The build already prepares the shaders with the
  port's renderer, so the first start does not repeat that work.
- **Building from a `.nup` uses Longshot's own code**, and the installer has not yet done it from start to finish in
  our tests. Building from an already built folder (the same builder, only without reading the `.nup`) was tested. If
  it fails, open an issue with `zelda-oot-deck/logs/montagem.log`.

## What you need

- A Steam Deck (LCD or OLED) with SteamOS.
- The `.nup` file of your copy of the game, with update v131072 (the one Hookshot asked for).
- 45 GB free for the build. Once installed, the game takes about 35 GB.
- If you already built the game with **Hookshot** or **Longshot**, you can point to that folder. The installer builds
  the game again with Longshot from the files the folder keeps, without the `.nup`, and on the same drive about 20 GB
  free is enough. Your folder stays as it is.

## How to install

1. On the Deck, switch to Desktop Mode.
2. Download [Instalar-Zelda-OoT.desktop](https://github.com/KewinBR/deckport-zelda-oot/releases/latest) and open it.
   Or, in Konsole:
   ```bash
   curl -L https://github.com/KewinBR/deckport-zelda-oot/releases/latest/download/instalar.sh | bash
   ```
3. The installer finds the `.nup` on the Deck and the SD card, asks where to install and does the rest: it downloads
   the official Longshot (v3.0.0-rc.3, with its SHA-256 checked), builds the game, installs the port's renderer,
   generates the Deck's textures and vegetation, and creates the Steam shortcut.
4. Go back to Game Mode and launch it from your library.

The installer changes nothing in the system. Everything stays in your home folder and, if you choose it, on the SD
card. If you played on Hookshot, your saves are copied over to Longshot during the install; Hookshot's save folder
stays as it was.

## Updating and uninstalling

To update, run the installer again (step 2 above). It downloads the latest version and keeps the work already done:
the built game and the textures are not made again.

To uninstall, in Konsole:
```bash
python3 ~/.local/share/zelda-oot-deck/instalador/desinstalar.py
```
This removes the Steam shortcut, the port, the downloaded Longshot, its settings, the generated mods and the logs.
Your saves stay in `~/.local/share/longshot`, and the built game folder stays too, back on Longshot's original
renderer. Add `--com-jogo` to also delete the game folder the installer built. A folder you built yourself before the
port is never deleted.

## How to report a problem

Open an issue and attach the log of the session where the problem happened. The logs are in `zelda-oot-deck/logs/`,
inside the location you chose at install time. Say which area of the game and what you were doing.

## What is Longshot's and what is Deckport's

Longshot (and Hookshot before it) does the heavy lifting: recompiling the game, translating the shaders and drawing
with Vulkan. The Deck button icons are also its work. Deckport replaces the renderer with a version changed for the
Deck, and adds the launcher, the mods generated from your copy of the game, the menu and the installer.

The renderer changes are in [patches/](patches/): `deckport-longshot-5e072fc8.patch` is the whole difference on top
of Longshot commit 5e072fc8, and `build-vk-ls.sh` shows how it is built. The installer applies `patch_800p.py` to
Longshot's builder, so the 1424x800 output also works in the handheld profile.

## Credits and license

- [Longshot](https://git.magicbean.dev/MagicBeanDev/Longshot), by MagicBeanDev and contributors, under GPL-3.0.
- Hookshot, by NotRexed and contributors, under GPL-3.0, which Longshot continues.
- Deckport by Kewin Lima.
- Fonts: Cinzel Decorative and Barlow, under the SIL Open Font License.

This repository is distributed under GPL-3.0, the same license as Longshot and Hookshot. The Legend of Zelda is a
trademark of Nintendo. This project is not affiliated with Nintendo.

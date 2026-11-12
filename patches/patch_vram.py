# Deckport: RX_VK_VRAM_MB vence o preset de qualidade do menu (como RX_VK_MIRROR_MB já vence, vk_memory.cpp).
# No Deck o preset 3 dava 4,8 GB de texturas; com a GPU (~6 GB, da mesma RAM) e o jogo (~4 GB) o kernel matava o jogo
# por falta de memória depois de ~10 min. Uso: python3 patch_vram.py gpu/vk/vk_texture.cpp
import sys
p = sys.argv[1]
s = open(p).read()
old = 'const bool preset_budget = opts.vram_mb > 0 && preset_caps_memory();'
assert s.count(old) == 1, 'preset_budget'
s = s.replace(old, 'const bool preset_budget = opts.vram_mb > 0 && !getenv("RX_VK_VRAM_MB") && preset_caps_memory();   // (Deckport)', 1)
open(p, 'w').write(s)
print('ok')

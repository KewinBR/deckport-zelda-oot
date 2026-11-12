# Deckport: o menu do port não abre mais no botão Steam (Guide). No Deck o jogo lê o controle direto e o botão Steam
# é da Steam (menu dela, e o congelar-no-menu-steam pausa o jogo). Fica só o combo View+Menu juntos, que o executável
# já esconde do jogo (host/nn_hid.c). Uso: python3 patch_menu.py gpu/vk/vk_menu.cpp
import sys
p = sys.argv[1]
s = open(p).read()
old = '    if (pad(HOS_PAD_GUIDE) || chord_now) press[0] = true;'
assert s.count(old) == 1, 'guide'
s = s.replace(old, '    if (chord_now) press[0] = true;   // (Deckport: sem o Guide, o botão Steam é da Steam)', 1)
open(p, 'w').write(s)
print('ok')

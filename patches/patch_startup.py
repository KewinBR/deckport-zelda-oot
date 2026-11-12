# Deckport: a tela de abertura (preparação dos shaders) com a marca do port: o logo "Steamdeck Version" no lugar do
# gancho do Hookshot e "DECKPORT" no lugar de "HOOKSHOT". A linha da versão segue dizendo Hookshot (crédito).
# O logo é desenhado pelo renderizador (gpu/vk/vk_startup_paint.h) a partir de assets/hookshot.png (nx2/logo_rgba.py, PNG
# RGBA 8 bits): só o hookshot_vk.so muda, o jogo não precisa ser compilado de novo.
# Uso: python3 patch_startup.py <árvore do Hookshot> <logo.png>
import shutil
import sys
root, logo = sys.argv[1], sys.argv[2]
shutil.copyfile(logo, root + '/assets/hookshot.png')
p = root + '/gpu/vk/vk_startup_paint.h'
s = open(p).read()
for a, b in (('constexpr int kLogoH = 112;', 'constexpr int kLogoH = 200;   // (Deckport: o logo do port, mais largo que alto)'),
             ('spaced(dc, "HOOKSHOT", cx, Y(0), S(7), true);', 'spaced(dc, "DECKPORT", cx, Y(0), S(7), true);')):
    assert s.count(a) == 1, a
    s = s.replace(a, b)
open(p, 'w').write(s)
print('ok')

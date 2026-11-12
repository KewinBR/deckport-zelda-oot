# Deckport: 16:10 (Steam Deck, 1280x800) sem barras. O widescreen do Hookshot (host/hos_main.c, nx2/oot_wide.py) só
# aceita telas mais largas que 16:9 (Hor+). Num 16:10 a imagem do jogo toma a forma da tela na altura do jogo
# (2304x1440), as câmeras 16:9 a razão 1,6 (um pouco menos de lado, como num 16:10 nativo) e a interface, que lá é
# espremida na horizontal pro meio 16:9, aqui é espremida na vertical (fica 16:9 no meio, 5% acima e abaixo livres).
# Ligado por HOS_ASPECT=1.6 (rodar-zelda.sh). Os vídeos pré-renderizados ainda esticam 11% na vertical (a fazer).
# Uso: python3 patch_1610.py <usr/share/hookshot do AppImage extraído, ou a árvore do Hookshot>
import sys
root = sys.argv[1]

p = root + '/host/hos_main.c'
s = open(p).read()
a = '        if (want > game * 1.01) {'
assert s.count(a) == 1, 'hos_main want'
s = s.replace(a, '        if (want > game * 1.01 || (want > 1.3f && want < game * 0.99)) {   /* (Deckport: 16:10 too) */', 1)
a = '            double r = want > 32.0 / 9.0 ? 32.0 / 9.0 : want;'
assert s.count(a) == 1, 'hos_main r'
open(p, 'w').write(s)

p = root + '/nx2/oot_wide.py'
s = open(p).read()
a = ('"if (%s) { float _row[4]; memcpy(_row, c->vreg[1], 16); for (int _k = 0; _k < 4; _k++) _row[_k] *= _q; "\n'
     '       "memcpy(c->vreg[1], _row, 16); } } } }   /* (nx2/oot_wide.py: HUD in the middle 16:9) */"')
assert s.count(a) == 1, 'oot_wide HUD'
b = ('"if (%s) { float _row[4]; const int _v = _q > 1.0f ? 4 : 1; const float _f = _q > 1.0f ? 1.0f / _q : _q; "\n'
     '       "memcpy(_row, c->vreg[_v], 16); for (int _k = 0; _k < 4; _k++) _row[_k] *= _f; "\n'
     '       "memcpy(c->vreg[_v], _row, 16); } } } }   /* (nx2/oot_wide.py: HUD in the middle 16:9; Deckport: a taller screen squeezes its rows) */"')
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('ok')

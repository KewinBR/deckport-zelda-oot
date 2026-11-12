# Deckport: saída 1424x800, a altura da tela do Steam Deck. Com HOS_ASPECT=1.6 a imagem fica 1280x800 (a tela nativa) e a
# cena 960x600, contra 2304x1440 e 1728x1080 na saída do jogo (1440). O pool de render targets (hos_rt_pool_size) escala
# pelos pixels da saída, então encolhe junto.
# v2.1.0: a saída aceita qualquer tamanho ("<largura>x<altura>", HOS_OUTPUT_RES=1424x800), mas só no modo dock; aqui o
#   HOS_OUTPUT_RES vale também no perfil portátil. ATENÇÃO: o "5" antigo virou 5120x2880 na v2.1.0.
# v2.0.12: acrescentava o modo 5 (1424x800) à tabela, valendo no portátil (HOS_OUTPUT_RES=5).
# Uso: python3 patch_800p.py <raiz do Hookshot do builder, ex. appimg-210/squashfs-root/usr/share/hookshot>
import sys, os
p = os.path.join(sys.argv[1], 'host', 'nn_applet.c')
s = open(p).read()

new = '        if (!handheld() && (e || ini_text("output_res", text, sizeof text))) hos_output_parse(e ? e : text, &output_w, &output_h);'
if new in s:   # (v2.1.0 em diante)
    s = s.replace(new, '        /* (Deckport: HOS_OUTPUT_RES in the handheld profile too, the Deck\'s 1424x800) */\n'
                       '        if ((!handheld() || e) && (e || ini_text("output_res", text, sizeof text))) hos_output_parse(e ? e : text, &output_w, &output_h);', 1)
    open(p, 'w').write(s)
    print('ok (v2.1.0)')
    sys.exit(0)

a = '''        static const char *const names[] = {"2048x1152 (the game's)", "2560x1440", "3840x2160", "1920x1080", "5120x1440"};
        v = getenv("HOS_OUTPUT_RES") ? atoi(getenv("HOS_OUTPUT_RES")) : ini_option("output_res", 0);
        if ((unsigned)v >= sizeof names / sizeof *names || handheld()) v = 0;'''
assert s.count(a) == 1, 'output_mode'
s = s.replace(a, '''        static const char *const names[] = {"2048x1152 (the game's)", "2560x1440", "3840x2160", "1920x1080", "5120x1440",
                                            "1424x800 (Steam Deck, Deckport)"};
        v = getenv("HOS_OUTPUT_RES") ? atoi(getenv("HOS_OUTPUT_RES")) : ini_option("output_res", 0);
        /* (Deckport: 5, the Deck's 800 lines, stays in the handheld profile too) */
        if ((unsigned)v >= sizeof names / sizeof *names || (handheld() && v != 5)) v = 0;''', 1)

a = '''    case 4: return height ? 1440 : 5120;
'''
assert s.count(a) == 1, 'hos_output_size'
s = s.replace(a, a + '''    case 5: return height ? 800 : 1424;   /* (Deckport: 16:9 at 800 lines; HOS_ASPECT=1.6 makes the picture 1280 x 800) */
''', 1)
open(p, 'w').write(s)
print('ok (v2.0.12)')

# Deckport: o menu do port no visual do jogo (patches/deckport_menu/vk_deckport_menu.h), na v2.1.0 do Hookshot (menu em
# Dear ImGui, fontes do próprio jogo). Põe o cabeçalho em gpu/vk/, acrescenta as opções do Deckport (opts.dp_*, gravadas no
# hookshot_options.ini como deckport_*), e troca o desenho e a navegação da página de opções pelos do Deckport
# (RX_VK_DECKPORT_MENU=0 volta ao do Hookshot). Passos já aplicados são pulados.
# Uso: python3 patch_menu_deckport.py <raiz do Hookshot>
import os, shutil, sys
root = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
shutil.copy(os.path.join(here, 'deckport_menu', 'vk_deckport_menu.h'), os.path.join(root, 'gpu/vk/vk_deckport_menu.h'))


def edit(rel, pairs):
    p = os.path.join(root, rel)
    s = open(p, encoding='utf-8').read()
    for a, b, tag in pairs:
        if b in s:
            continue   # (já aplicado)
        assert s.count(a) == 1, (rel, tag, s.count(a))
        s = s.replace(a, b, 1)
    open(p, 'w', encoding='utf-8').write(s)


edit('gpu/vk/vk_menu.h', [(
    '    int mic = 1;',
    '    int dp_preset = 1;    // (Deckport) predefinição: 0 Qualidade, 1 Equilibrado, 2 Desempenho, 3 Bateria, 4 Personalizado\n'
    '    int dp_distance = 2;  // (Deckport) distância de desenho: 0 Perto .. 4 Original (rodar-zelda.sh: o mod de vegetação)\n'
    '    int dp_grass = 0;     // (Deckport) grama: 0 50%, 1 75%, 2 original\n'
    '    int dp_shadows = 1;   // (Deckport) sombras: 0 original, 1 média (RX_VK_SHADOW_DIV=2), 2 baixa (4)\n'
    '    int dp_textures = 1;  // (Deckport) texturas: 0 altas (mod 1024), 1 médias (mod 512)\n'
    '    int mic = 1;', 'opcoes')])

edit('gpu/vk/vk_menu.cpp', [
    ('    TAB_PAGE = TAB_MOTION + 1   // (hookshot: the Controls page\'s rows, above its grid; no tab shows them)\n',
     '    TAB_PAGE = TAB_MOTION + 1,   // (hookshot: the Controls page\'s rows, above its grid; no tab shows them)\n'
     '    TAB_DECKPORT = TAB_PAGE + 1   // (Deckport: as opções do menu do port, gravadas no ini; nenhuma aba do Hookshot as mostra)\n',
     'tab'),
    ('''    // (Restart and Quit stay the table's last two''',
     '''    {TAB_DECKPORT, "Deckport preset", &opts.dp_preset, 0, 4, 1, nullptr, "", nullptr, false, true},
    {TAB_DECKPORT, "Deckport distance", &opts.dp_distance, 0, 4, 1, nullptr, "", nullptr, false, true},
    {TAB_DECKPORT, "Deckport grass", &opts.dp_grass, 0, 2, 1, nullptr, "", nullptr, false, true},
    {TAB_DECKPORT, "Deckport shadows", &opts.dp_shadows, 0, 2, 1, nullptr, "", nullptr, false, true},
    {TAB_DECKPORT, "Deckport textures", &opts.dp_textures, 0, 1, 1, nullptr, "", nullptr, false, true},
    // (Restart and Quit stay the table's last two''', 'linhas'),
    ('void draw_menu(ui::Ctx& c) {\n',
     '#include "vk_deckport_menu.h"\n'
     'void draw_menu(ui::Ctx& c) {\n'
     '    if (dp::on() && page == 0) {   // (Deckport: a tela inteira, no visual do jogo)\n'
     '        menu_ox = 0;\n'
     '        hits.clear(0, 0, c.w, c.h);\n'
     '        dp::paint(c);\n'
     '        return;\n'
     '    }\n', 'desenho'),
    ('''    } else if (open_now.load()) {
        if (mouse) {   // (the mouse: see the top of this file)''',
     '''    } else if (open_now.load() && dp::on() && page == 0) {   // (Deckport: a navegação do menu do port)
        const bool y_pad = listening != 1 && (pad_press >> HOS_PAD_NORTH & 1) != 0;
        dp::tick(press, tab_left, tab_right, y_pad, mouse, mx, my, mouse ? ptr.pressed : 0, mine);
    } else if (open_now.load()) {
        if (mouse) {   // (the mouse: see the top of this file)''', 'navegação'),
    ('    if (pad(HOS_PAD_GUIDE) || chord_now) press[0] = true;',
     '    if (chord_now) press[0] = true;   // (Deckport: sem o Guide, o botão Steam é da Steam)', 'guide'),
])
print('ok')

#!/usr/bin/env python3
"""Deckport: a tela de abertura animada do port (deckport_menu/vk_deckport_startup.h) no lugar da tela do Hookshot.
Uso: patch_tela_abertura.py <árvore do Hookshot> <logo do port .png>
O logo (arte do jogo, fora do git) vira o assets/hookshot.png da árvore; o nx2/build.py o embute no hookshot_vk.so.
Só o renderizador muda. Idempotente. Se uma âncora sumir numa versão nova do Hookshot, o patch para com erro,
e o build-vk-210.sh também recusa compilar sem a marca "dp::paint_startup" na árvore."""
import os
import shutil
import sys

root, logo = sys.argv[1], sys.argv[2]
aqui = os.path.dirname(os.path.abspath(__file__))
shutil.copyfile(logo, os.path.join(root, "assets", "hookshot.png"))
shutil.copyfile(os.path.join(aqui, "deckport_menu", "vk_deckport_startup.h"), os.path.join(root, "gpu", "vk", "vk_deckport_startup.h"))


def troca(arq, pares, marca):
    p = os.path.join(root, arq)
    s = open(p, encoding="utf-8").read()
    if marca in s:
        print(arq + ": já aplicado")
        return
    for a, b in pares:
        assert s.count(a) == 1, "%s: âncora não encontrada (ou repetida): %s" % (arq, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print(arq + ": ok")


troca("gpu/vk/vk_menu.cpp", [(
    "void draw_startup(ui::Ctx& c) {\n",
    '#include "vk_deckport_startup.h"\n'
    "void draw_startup(ui::Ctx& c) {\n"
    "    if (dp::startup_on()) {   // (Deckport: a tela de abertura do port)\n"
    "        StartupView dv;\n"
    "        {\n"
    "            std::lock_guard lk(startup_mu);\n"
    "            dv = startup;\n"
    "        }\n"
    "        dp::paint_startup(c, dv, startup_fade.load(std::memory_order_relaxed));\n"
    "        return;\n"
    "    }\n")], "dp::paint_startup")
# a tela dura o bastante para a animação de entrada terminar, e é desenhada a 60 quadros por segundo
troca("gpu/vk/vk_main.cpp", [
    ("            if (finished || paint_stop.load()) break;\n            Sleep(33);\n",
     "            if ((finished && secs >= deckport_startup_min()) || paint_stop.load()) break;\n            Sleep(16);\n"),
    ("    std::thread painter([t0, painted] {\n",
     "    std::thread painter([t0, painted] {\n"
     "        auto deckport_startup_min = [] {   // (Deckport: a animação de entrada inteira, vk_deckport_startup.h kStartupMin)\n"
     '            const char* e = getenv("RX_VK_DECKPORT_STARTUP");\n'
     "            return !e || atoi(e) != 0 ? 4.2 : 0.0;\n"
     "        };\n")], "deckport_startup_min")
# (teste, opcional) com RX_VK_DP_STARTUP_T a tela é desenhada nas capturas sem janela (RX_VK_SHOT_MENU=1);
# se a âncora sumir numa versão nova, só avisa
try:
    troca("gpu/vk/vk_menu.cpp", [(
        "    const bool fps = opts.show_fps && !startup_on.load(std::memory_order_acquire);\n"
        "    if (!open && !fps) return;\n"
        "    if (!ui::begin(w, h)) return;\n"
        "    ui::Ctx c = ui_ctx(w, h);\n"
        "    if (open) draw_menu(c);\n",
        "    const bool dp_test = dp::startup_test();   // (Deckport: a tela de abertura nas capturas de teste)\n"
        "    const bool fps = opts.show_fps && !startup_on.load(std::memory_order_acquire) && !dp_test;\n"
        "    if (!open && !fps && !dp_test) return;\n"
        "    if (!ui::begin(w, h)) return;\n"
        "    ui::Ctx c = ui_ctx(w, h);\n"
        "    if (dp_test) draw_startup(c);\n"
        "    if (open) draw_menu(c);\n")], "dp::startup_test()")
except AssertionError as e:
    print("aviso (só o modo de teste):", e)

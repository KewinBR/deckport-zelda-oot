#!/usr/bin/env python3
"""Deckport: RX_VK_AFLASH_DUMP=<pasta> faz o contador de piscadas (patch_aflash.py) gravar a imagem de cada piscada.

Para cada piscada contada (as 40 primeiras e depois uma a cada 8, até 160 arquivos) grava <pasta>/af_<present>.ppm:
os três quadros 64x36 lado a lado (o anterior, o da piscada, o seguinte) e, embaixo, as células que dispararam em
branco. Serve para ver o que o contador está contando: piscada de verdade ou efeito do jogo (fogo, fada, partículas).
O contador sozinho já enganou: a mesma variante deu 13 e 608 na mesma cena (2026-11-12).

Uso: patch_aflash_dump.py <árvore do Hookshot>. Precisa do patch_aflash.py já aplicado. Idempotente.
"""
import os
import sys

p = os.path.join(sys.argv[1], "gpu", "vk", "vk_replay.cpp")
s = open(p, encoding="utf-8").read()
if "RX_VK_AFLASH_DUMP" in s:
    print("já aplicado")
    sys.exit(0)


def troca(a, b):
    global s
    assert s.count(a) == 1, "âncora não encontrada (ou repetida): " + a[:80]
    s = s.replace(a, b)


# as células que dispararam, guardadas durante a contagem
troca("            int hits = 0, up = 0;\n",
      "            int hits = 0, up = 0;\n"
      "            static std::vector<uint8_t> af_mask;   // (Deckport: RX_VK_AFLASH_DUMP)\n"
      "            af_mask.assign((size_t)kAfW * kAfH, 0);\n")
troca("                if (dab > 48 && dbc > 48 && dac < 16) hits++, up += fb[i * 4 + 1] > fa[i * 4 + 1];\n",
      "                if (dab > 48 && dbc > 48 && dac < 16) hits++, up += fb[i * 4 + 1] > fa[i * 4 + 1], af_mask[i] = 255;\n")
troca("            if (hits >= 40) {\n"
      "                flashes++, flashes_total++, up_total += up * 2 > hits;\n",
      "            if (hits >= 40) {\n"
      "                flashes++, flashes_total++, up_total += up * 2 > hits;\n"
      "                {   // (Deckport) RX_VK_AFLASH_DUMP=<dir>: the three frames side by side and the cells that fired, as a PPM\n"
      '                    static const char* dir = getenv("RX_VK_AFLASH_DUMP");\n'
      "                    static int dumped = 0;\n"
      "                    if (dir && dumped < 160 && (flashes_total <= 40 || flashes_total % 8 == 0)) {\n"
      "                        char path[512];\n"
      '                        snprintf(path, sizeof path, "%s/af_%08lld.ppm", dir, (long long)pb);\n'
      '                        if (FILE* f = fopen(path, "wb")) {\n'
      '                            fprintf(f, "P6\\n%u %u\\n255\\n", kAfW * 3, kAfH * 2);\n'
      "                            const std::vector<uint8_t>* fr[3] = {&fa, &fb, &fc};\n"
      "                            for (uint32_t y = 0; y < kAfH; y++)\n"
      "                                for (int k = 0; k < 3; k++)\n"
      "                                    for (uint32_t x = 0; x < kAfW; x++) fwrite(fr[k]->data() + ((size_t)y * kAfW + x) * 4, 1, 3, f);\n"
      "                            for (uint32_t y = 0; y < kAfH; y++)\n"
      "                                for (int k = 0; k < 3; k++)\n"
      "                                    for (uint32_t x = 0; x < kAfW; x++) {\n"
      "                                        const uint8_t v = k == 1 ? af_mask[(size_t)y * kAfW + x] : 0;\n"
      "                                        const uint8_t px[3] = {v, v, v};\n"
      "                                        fwrite(px, 1, 3, f);\n"
      "                                    }\n"
      "                            fclose(f);\n"
      "                            dumped++;\n"
      "                        }\n"
      "                    }\n"
      "                }\n")

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")

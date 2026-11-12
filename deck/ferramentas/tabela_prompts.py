#!/usr/bin/env python3
"""Junta a tabela de tamanhos do nosso mod de texturas com a dos ícones de botão do Hookshot.

O Hookshot v2.1.0 troca os ícones de botão do jogo pelos do controle em uso (pasta prompts/ do jogo: switch, xbox,
ps4, ps5, steamdeck). A fonte dos ícones que ele gera é maior que a do jogo, então ele serve uma tabela de tamanhos
própria (prompts/rsizetable.zs) com a entrada da fonte aumentada. Se um mod traz a tabela de tamanhos, o Hookshot serve
a do mod e desiste da fonte: os ícones nos textos e no HUD ficam os do Switch ("prompts: a mod has the resource size
table: the game's own icons in texts"). O nosso mod de texturas traz essa tabela (reduzir_texturas.py).

Saída: a tabela do mod com a entrada da fonte copiada da tabela do Hookshot. Ela vai para prompts/rsizetable.zs do
jogo (o rodar-zelda.sh copia a da opção de texturas escolhida) e a tabela sai de dentro do mod.

    tabela_prompts.py <tabela do mod .zs> <prompts/rsizetable.zs do Hookshot> <saída .zs>
"""
import struct
import sys
import zlib

import zstandard

FONTE = b"Font2/Scalable/External.Nin_Ounce_NVN2.bfotf"


def ler(caminho):
    b = bytearray(zstandard.ZstdDecompressor().decompress(open(caminho, "rb").read(), max_output_size=1 << 27))
    assert b[:6] == b"RESTBL", caminho + ": não é uma tabela RESTBL"
    return b


def entrada(b, crc):
    n, = struct.unpack_from("<I", b, 14)
    lo, hi = 0, n   # (as entradas ficam em ordem de hash)
    while lo < hi:
        m = (lo + hi) // 2
        h, = struct.unpack_from("<I", b, 22 + 8 * m)
        if h == crc:
            return 22 + 8 * m + 4
        if h < crc:
            lo = m + 1
        else:
            hi = m
    for i in range(n):   # (se a ordem não for a esperada)
        if struct.unpack_from("<I", b, 22 + 8 * i)[0] == crc:
            return 22 + 8 * i + 4
    raise SystemExit("sem entrada da fonte dos ícones na tabela")


def main():
    mod, hookshot, saida = sys.argv[1:4]
    a, h = ler(mod), ler(hookshot)
    crc = zlib.crc32(FONTE)
    antes, = struct.unpack_from("<I", a, entrada(a, crc))
    novo, = struct.unpack_from("<I", h, entrada(h, crc))
    struct.pack_into("<I", a, entrada(a, crc), max(antes, novo))
    open(saida, "wb").write(zstandard.ZstdCompressor(level=19).compress(bytes(a)))
    print("fonte dos ícones: %d -> %d bytes; %s" % (antes, max(antes, novo), saida))


if __name__ == "__main__":
    main()

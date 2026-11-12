# Deckport: mod de vegetação mais leve pro Steam Deck. Nos Foliage/ResFoliageScene/*.bgyml (um por área) multiplica a
# densidade da grama (TurfDensity), o mínimo de folhas por tufo (TurfMinBlades) e as distâncias da vegetação
# (Dist_* em LodSetting e LodSetting_hh, o portátil). O valor fica dentro da própria entrada do dict no BYML v7, então
# a troca é no lugar (4 bytes) e o arquivo mantém o tamanho (a tabela de tamanhos não muda). Chave que a área não tem
# segue o padrão do código do jogo (Hyrule Field não tem LodSetting: só a densidade muda lá).
#
# Uso: python reduzir_vegetacao.py <romfs> --saida <mod>/romfs [--densidade 0.5] [--folhas 0.67] [--distancia 0.6]
#      --simular: só lista o que mudaria
import argparse, os, struct, glob


def patch(b, fatores):
    """fatores: {chave: fator}. Devolve (bytes, [(caminho, antes, depois)])."""
    b = bytearray(b)
    le = b[:2] == b"YB"
    E = "<" if le else ">"
    u32 = lambda o: struct.unpack_from(E + "I", b, o)[0]

    def strtab(o):
        if not o:
            return []
        n = u32(o) >> 8 if le else u32(o) & 0xFFFFFF
        offs = [u32(o + 4 + 4 * i) for i in range(n)]
        return [bytes(b[o + x:b.index(b"\0", o + x)]).decode("utf8", "replace") for x in offs]

    keys = strtab(u32(4))
    mud = []

    def node(o, path):
        t = b[o]
        n = u32(o) >> 8 if le else u32(o) & 0xFFFFFF
        if t == 0xC0:
            ts = b[o + 4:o + 4 + n]
            base = o + 4 + ((n + 3) & ~3)
            for i in range(n):
                if ts[i] in (0xC0, 0xC1):
                    node(u32(base + 4 * i), path + "[%d]" % i)
        elif t == 0xC1:
            for i in range(n):
                e = o + 4 + 8 * i
                k = keys[u32(e) & 0xFFFFFF if le else u32(e) >> 8]
                tt = b[e + 3]
                if tt in (0xC0, 0xC1):
                    node(u32(e + 4), path + "/" + k)
                elif k in fatores or any(k.startswith(p[:-1]) for p in fatores if p.endswith("*")):
                    f = fatores.get(k) or next(fatores[p] for p in fatores if p.endswith("*") and k.startswith(p[:-1]))
                    if tt == 0xD2:
                        v = struct.unpack_from(E + "f", b, e + 4)[0]
                        nv = v * f
                        struct.pack_into(E + "f", b, e + 4, nv)
                        mud.append((path + "/" + k, round(v, 3), round(nv, 3)))
                    elif tt == 0xD1:
                        v = struct.unpack_from(E + "i", b, e + 4)[0]
                        nv = max(1, int(round(v * f)))
                        struct.pack_into(E + "i", b, e + 4, nv)
                        mud.append((path + "/" + k, v, nv))

    root = u32(12)
    if root:
        node(root, "")
    return bytes(b), mud


def dicionarios(romfs):
    """Os dicionários zstd do jogo (Pack/ZsDic.pack.zs, um SARC): {id: ZstdCompressionDict}."""
    import zstandard
    b = zstandard.ZstdDecompressor().decompress(open(os.path.join(romfs, "Pack", "ZsDic.pack.zs"), "rb").read(),
                                                 max_output_size=1 << 28)
    out = {}
    for nome, dado in sarc_entradas(b):
        d = zstandard.ZstdCompressionDict(dado)
        out[d.dict_id()] = d
    return out


def sarc_entradas(b):
    """[(nome, bytes)] de um SARC (little endian)."""
    hl = struct.unpack_from("<H", b, 4)[0]
    doff = struct.unpack_from("<I", b, 0xC)[0]
    n = struct.unpack_from("<H", b, hl + 6)[0]
    sfnt = hl + 12 + 16 * n
    out = []
    for i in range(n):
        e = hl + 12 + 16 * i
        attr, s, f = struct.unpack_from("<III", b, e + 4)
        nome = ""
        if attr & 0x01000000:
            o = sfnt + 8 + (attr & 0xFFFF) * 4
            nome = b[o:b.index(b"\0", o)].decode()
        out.append((nome, b[doff + s:doff + f]))
    return out


def pack(romfs, saida, fatores, simular):
    """Pack/Foliage.pack.zs: é de lá que o jogo lê os ResFoliageScene (os .bgyml soltos ficam sem uso). Troca no lugar
    dentro do SARC e comprime de novo com o mesmo dicionário."""
    import zstandard
    p = os.path.join(romfs, "Pack", "Foliage.pack.zs")
    raw = open(p, "rb").read()
    did = zstandard.get_frame_parameters(raw).dict_id
    dic = dicionarios(romfs)[did]
    b = bytearray(zstandard.ZstdDecompressor(dict_data=dic).decompress(raw, max_output_size=1 << 30))
    hl = struct.unpack_from("<H", b, 4)[0]
    doff = struct.unpack_from("<I", b, 0xC)[0]
    n = struct.unpack_from("<H", b, hl + 6)[0]
    sfnt = hl + 12 + 16 * n
    tot = 0
    for i in range(n):
        e = hl + 12 + 16 * i
        attr, s, f = struct.unpack_from("<III", b, e + 4)
        nome = ""
        if attr & 0x01000000:
            o = sfnt + 8 + (attr & 0xFFFF) * 4
            nome = bytes(b[o:b.index(b"\0", o)]).decode()
        if "ResFoliageScene" not in nome:
            continue
        nb, mud = patch(bytes(b[doff + s:doff + f]), fatores)
        if mud:
            b[doff + s:doff + f] = nb
            tot += len(mud)
            print("pack:", nome.split("/")[-1].split(".")[0], "; ".join("%s %s->%s" % (c.split("/", 1)[-1], x, y) for c, x, y in mud))
    if saida and not simular:
        q = os.path.join(saida, "Pack", "Foliage.pack.zs")
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "wb").write(zstandard.ZstdCompressor(level=16, dict_data=dic).compress(bytes(b)))
    print("pack: %d valores (dicionário %d)" % (tot, did))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("romfs")
    ap.add_argument("--saida")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--densidade", type=float, default=0.5)
    ap.add_argument("--folhas", type=float, default=0.67)
    ap.add_argument("--distancia", type=float, default=0.6)
    a = ap.parse_args()
    fatores = {"TurfDensity": a.densidade, "TurfMinBlades": a.folhas, "Dist_*": a.distancia}
    fs = sorted(glob.glob(os.path.join(a.romfs, "Foliage", "ResFoliageScene", "*.bgyml")))
    tot = 0
    for p in fs:
        nb, mud = patch(open(p, "rb").read(), fatores)
        if not mud:
            continue
        tot += len(mud)
        print(os.path.basename(p).split(".")[0], "; ".join("%s %s->%s" % (c.split("/", 1)[-1], x, y) for c, x, y in mud))
        if a.saida and not a.simular:
            q = os.path.join(a.saida, "Foliage", "ResFoliageScene", os.path.basename(p))
            os.makedirs(os.path.dirname(q), exist_ok=True)
            open(q, "wb").write(nb)
    print("%d valores em %d áreas (arquivos soltos)" % (tot, len(fs)))
    pack(a.romfs, a.saida, fatores, a.simular)


if __name__ == "__main__":
    main()

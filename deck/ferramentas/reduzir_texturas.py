# Deckport: mod de texturas reduzidas pro Steam Deck. Em cada Tex/*.bntx.zs 2D cujo lado passa de --max (1024), tira os
# níveis de mipmap de cima até caber, sem desembaralhar nada: no block linear do Tegra cada nível já está no arranjo dele,
# então o nível 1 vira o 0 recortando os dados a partir dele e acertando largura, altura, número de níveis, a lista de
# onde cada nível começa, o tamanho da imagem, o bloco BRTD, a tabela de relocação (_RLT) e o tamanho do arquivo.
# O jogo carrega menos memória (o arquivo e o pool da GPU) e o renderizador copia menos.
#
# Uso (precisa só do zstandard; no Deck do jogador roda com o Python que vem no Hookshot):
#   python reduzir_texturas.py <romfs> --simular            mede quanto economiza, sem escrever nada
#   python reduzir_texturas.py <romfs> --saida <mod>/romfs    escreve os .bntx.zs reduzidos e a tabela de tamanhos nova
#   opções: --max 1024, --so <padrão no nome>, --jobs 4
# Fica de fora (copiado como está): arrays e cubemaps com camadas que não fecham no alinhamento, texturas 3D, formatos
# que a tabela abaixo não conhece, textura com um nível só (lightmaps RBake_*).
import argparse, os, struct, sys, glob
from concurrent.futures import ProcessPoolExecutor
import zstandard

# formato BNTX (byte alto): bloco em pixels e bytes por bloco
FMT = {0x02: (1, 1, 1), 0x07: (1, 1, 2), 0x09: (1, 1, 2), 0x0a: (1, 1, 2), 0x0b: (1, 1, 4), 0x0c: (1, 1, 4),
       0x0e: (1, 1, 4), 0x0f: (1, 1, 4), 0x12: (1, 1, 8), 0x14: (1, 1, 8),
       0x1a: (4, 4, 8), 0x1b: (4, 4, 16), 0x1c: (4, 4, 16), 0x1d: (4, 4, 8), 0x1e: (4, 4, 16), 0x1f: (4, 4, 16),
       0x20: (4, 4, 16),
       0x2d: (4, 4, 16), 0x2e: (5, 4, 16), 0x2f: (5, 5, 16), 0x30: (6, 5, 16), 0x31: (6, 6, 16), 0x32: (8, 5, 16),
       0x33: (8, 6, 16), 0x34: (8, 8, 16), 0x35: (10, 5, 16), 0x36: (10, 6, 16), 0x37: (10, 8, 16),
       0x38: (10, 10, 16), 0x39: (12, 10, 16), 0x3a: (12, 12, 16)}


def bh_for(h, blk_h, bh_log2):
    """Altura do bloco de GOBs de um nível de altura h, partindo da do nível 0 (o Tegra encolhe nos níveis menores)."""
    rows = -(-h // blk_h)
    gobs = -(-rows // 8)
    bh = 1 << bh_log2
    while bh > 1 and gobs <= bh // 2:
        bh //= 2
    return bh.bit_length() - 1


def reduzir(b, maxdim):
    """Devolve (bytes novos, bytes economizados, motivo) ou (None, 0, motivo)."""
    if b[:4] != b"BNTX":
        return None, 0, "não é BNTX"
    if b.count(b"BRTI") != 1:
        return None, 0, "mais de uma textura"
    i = b.find(b"BRTI")
    u8 = lambda o: b[i + o]
    u16 = lambda o: struct.unpack_from("<H", b, i + o)[0]
    u32 = lambda o: struct.unpack_from("<I", b, i + o)[0]
    u64 = lambda o: struct.unpack_from("<Q", b, i + o)[0]
    dim, tile, mips, fmt = u8(0x11), u16(0x12), u16(0x16), u32(0x1C)
    w, h, d, arr, lay, isz = u32(0x24), u32(0x28), u32(0x2C), u32(0x30), u32(0x34), u32(0x50)
    if max(w, h) <= maxdim:
        return None, 0, "já cabe"
    if mips < 2:
        return None, 0, "um nível só"
    if tile != 0 or d != 1 or dim not in (2, 3):   # (2: 2D, 3: cubemap/array em camadas; 3D tem d > 1)
        return None, 0, "tile/3D"
    if (fmt >> 8) not in FMT:
        return None, 0, "formato %x" % fmt
    bw, bhp, bpb = FMT[fmt >> 8]
    k = 0
    while k < mips - 1 and max(max(1, w >> k), max(1, h >> k)) > maxdim:
        k += 1
    po = u64(0x70)
    offs = list(struct.unpack_from("<%dQ" % mips, b, po))
    off0 = offs[0]
    rel_k = offs[k] - off0
    if arr > 1:
        if isz % arr:
            return None, 0, "camadas sem passo inteiro"
        stride = isz // arr
        nstride = stride - rel_k
        nbh = bh_for(max(1, h >> k), bhp, lay & 7)
        if nstride <= 0 or nstride % (512 << nbh):
            return None, 0, "camadas fora do alinhamento"
        data = b"".join(b[off0 + l * stride + rel_k: off0 + (l + 1) * stride] for l in range(arr))
    else:
        data = b[off0 + rel_k: off0 + isz]
    nisz = len(data)
    nmips = mips - k
    nw, nh = max(1, w >> k), max(1, h >> k)
    nlay = (lay & ~7) | bh_for(nh, bhp, lay & 7)

    j = b.find(b"BRTD")
    rlt_old = struct.unpack_from("<I", b, 0x18)[0]
    al = lambda x, a: (x + a - 1) // a * a
    rlt_new = al(off0 + nisz, 0x1000) if rlt_old % 0x1000 == 0 else al(off0 + nisz, 8)
    out = bytearray(b[:off0]) + data
    out += b"\0" * (rlt_new - len(out))
    rlt = bytearray(b[rlt_old:])
    out += rlt
    # cabeçalho: tabela de relocação e tamanho do arquivo
    struct.pack_into("<I", out, 0x18, rlt_new)
    struct.pack_into("<I", out, 0x1C, len(out))
    # BRTD: o bloco vai até a tabela de relocação
    old_brtd = struct.unpack_from("<Q", b, j + 8)[0]
    new_brtd = old_brtd - (rlt_old - rlt_new)
    struct.pack_into("<I", out, j + 4, 0)
    struct.pack_into("<Q", out, j + 8, new_brtd)
    # _RLT: a própria posição e o tamanho da seção que cobre o BRTD
    struct.pack_into("<I", out, rlt_new + 4, rlt_new)
    nsec = struct.unpack_from("<I", out, rlt_new + 8)[0]
    for s in range(nsec):
        e = rlt_new + 0x10 + 0x18 * s
        pos, size = struct.unpack_from("<II", out, e + 8)
        if pos == j:
            struct.pack_into("<I", out, e + 12, size - (rlt_old - rlt_new))
    # BRTI: tamanho, níveis, largura, altura, bloco de GOBs, tamanho da imagem, lista dos níveis
    struct.pack_into("<H", out, i + 0x16, nmips)
    struct.pack_into("<I", out, i + 0x24, nw)
    struct.pack_into("<I", out, i + 0x28, nh)
    struct.pack_into("<I", out, i + 0x34, nlay)
    struct.pack_into("<I", out, i + 0x50, nisz)
    nof = [o - rel_k for o in offs[k:]] + [0] * k
    struct.pack_into("<%dQ" % mips, out, po, *nof)
    return bytes(out), isz - nisz, "reduzida %dx%d -> %dx%d (%d níveis a menos)" % (w, h, nw, nh, k)


def um(args):
    p, maxdim, saida = args
    dz = zstandard.ZstdDecompressor()
    raw = open(p, "rb").read()
    b = dz.decompress(raw, max_output_size=1 << 31)
    try:
        nb, ganho, motivo = reduzir(b, maxdim)
    except Exception as e:   # (um arquivo estranho não derruba o lote)
        nb, ganho, motivo = None, 0, "erro: %s" % e
    if nb is not None and saida:
        q = os.path.join(saida, "Tex", os.path.basename(p))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "wb").write(zstandard.ZstdCompressor(level=6).compress(nb))
    return os.path.basename(p), len(b), (len(nb) if nb else len(b)), ganho, motivo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("romfs")
    ap.add_argument("--max", type=int, default=1024)
    ap.add_argument("--saida")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--so")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--tabela")
    ap.add_argument("--progresso", action="store_true")   # (linhas "@@ feitas total", para o instalador)
    a = ap.parse_args()
    fs = sorted(glob.glob(os.path.join(a.romfs, "Tex", "*.bntx.zs")))
    if a.so:
        fs = [f for f in fs if a.so in os.path.basename(f)]
    saida = None if a.simular else a.saida
    total = ganho = n = 0
    motivos = {}
    mudados = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for nome, antes, depois, g, motivo in ex.map(um, [(f, a.max, saida) for f in fs], chunksize=16):
            total += antes
            feitas = sum(motivos.values()) + 1
            if a.progresso and feitas % 64 == 0:
                print("@@ %d %d" % (feitas, len(fs)), flush=True)
            motivos[motivo.split(" ")[0]] = motivos.get(motivo.split(" ")[0], 0) + 1
            if g:
                n += 1
                ganho += g
                mudados[nome] = (antes, depois)
    print("%d texturas, %d reduzidas; %.0f MB de %.0f MB a menos (descomprimido)" % (len(fs), n, ganho / 2**20, total / 2**20))
    for m, c in sorted(motivos.items(), key=lambda x: -x[1]):
        print("  %6d %s" % (c, m))
    if saida and mudados:
        # A tabela de tamanhos (RESTBL): "RESTBL", versão, tamanho do nome, n entradas por hash, n por nome; as por
        # hash são (CRC-32 do caminho, tamanho) em ordem de hash. Lida e escrita aqui mesmo, sem a biblioteca restbl,
        # para rodar no Deck só com o Python do Hookshot. --tabela <arquivo>: onde gravar (padrão: dentro do mod).
        import zlib, bisect
        rp = glob.glob(os.path.join(a.romfs, "System", "Resource", "ResourceSizeTable.*.rsizetable.zs"))[0]
        t = bytearray(zstandard.ZstdDecompressor().decompress(open(rp, "rb").read(), max_output_size=1 << 27))
        assert t[:6] == b"RESTBL", "tabela de tamanhos em formato desconhecido"
        n_hash, = struct.unpack_from("<I", t, 14)
        hashes = [struct.unpack_from("<I", t, 22 + 8 * i)[0] for i in range(n_hash)]
        mudou = 0
        for nome, (antes, depois) in mudados.items():
            crc = zlib.crc32(("Tex/" + nome[:-3]).encode())
            i = bisect.bisect_left(hashes, crc)
            if i < n_hash and hashes[i] == crc:
                velho, = struct.unpack_from("<I", t, 22 + 8 * i + 4)
                if velho:
                    struct.pack_into("<I", t, 22 + 8 * i + 4, max(depois, velho - (antes - depois)))
                    mudou += 1
        q = a.tabela or os.path.join(saida, "System", "Resource", os.path.basename(rp))
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "wb").write(zstandard.ZstdCompressor(level=19).compress(bytes(t)))
        print("tabela de tamanhos: %d entradas menores" % mudou)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deckport: cópia dos dados pequenos lidos de blocos sem espelho (RX_VK_BIND_SNAPSHOT_KB).

O problema (medido no Deck, 2026-11-12): um bloco de memória do jogo sem espelho de VRAM é lido pela GPU na própria
memória do jogo, enquanto o jogo já escreve o quadro seguinte. Sai um quadro com folhas brancas, HUD embaralhado ou
luz errada. Espelhar tudo (RX_VK_MIRROR_MB=2048) tira 90% das piscadas (182 -> 19 na mesma cena), mas custa 1,3 GB
de memória num aparelho que já está no limite: o espelho copia o bloco inteiro, e os blocos têm de 16 a 240 MB.

A correção: uma leitura de até N KB num bloco sem espelho recebe uma cópia dos seus bytes, como estavam no envio
(as páginas das capturas por cima da memória atual), no stream da gravação, e o desenho usa a cópia. O que cada
desenho lê por quadro é pouco (constantes, instâncias, índices pequenos); as ligações grandes, de dezenas de MB, são
geometria parada e continuam lendo a memória do jogo. Ligações escritas pela GPU não são copiadas.

RX_VK_BIND_SNAPSHOT_KB=<KB>: o tamanho máximo copiado (0 ou sem a variável: desligado, como antes).
A cada 600 envios o log diz quantas ligações foram copiadas e quantas ficaram de fora pelo tamanho.

Uso: patch_bind_snapshot.py <árvore do Hookshot>. Idempotente; para com erro se uma âncora sumir.
"""
import os
import sys

p = os.path.join(sys.argv[1], "gpu", "vk", "vk_memory.cpp")
s = open(p, encoding="utf-8").read()
if "RX_VK_BIND_SNAPSHOT_KB" in s:
    print("já aplicado")
    sys.exit(0)


def troca(a, b):
    global s
    assert s.count(a) == 1, "âncora não encontrada (ou repetida): " + a[:90]
    s = s.replace(a, b)


# 1. o ajudante, antes do gpu_buffer_bind
troca(
    "BufferRef gpu_buffer_bind(uint64_t gpu, uint64_t size, bool written) {\n",
    '''// (Deckport) RX_VK_BIND_SNAPSHOT_KB: a read binding of a pool with no mirror, up to that many KB, is served from a copy
// of its bytes as submitted, in the recording's stream (patches/patch_bind_snapshot.py)
uint64_t bind_snapshot_max() {
    static const uint64_t n = [] {
        const char* e = getenv("RX_VK_BIND_SNAPSHOT_KB");
        const uint64_t kb = e ? (uint64_t)std::max(0, atoi(e)) : 0;
        if (kb) logf("vk: read bindings of pools with no mirror copied as submitted, up to %llu KB each (RX_VK_BIND_SNAPSHOT_KB)",
                     (unsigned long long)kb);
        return kb << 10;
    }();
    return n;
}
int64_t st_snap_binds, st_snap_bytes, st_snap_big, st_snap_big_bytes, st_snap_failed;
int64_t st_snap_gpu, st_snap_again;
/// (pools_mu held) the copy, or nothing: over the size, a pool the GPU writes, no recording, no room in its stream.
/// A pool the GPU wrote in guest memory in the last 4000 submissions is left alone: the copy is made on the CPU while
/// the replay records, before the GPU has run the writes recorded ahead of it, and would hold the bytes from before
/// them (measured: copying those too took a scene from 182 flashes to 1,577). The same range bound again in a
/// submission gets the copy made for it before (one recording held 98 MB of copies without this)
BufferRef bind_snapshot(const Pool& p, uint64_t gpu, uint64_t guest, uint64_t size) {
    const uint64_t max = bind_snapshot_max();
    if (!max || !size) return {};
    if (size > max) {
        st_snap_big++, st_snap_big_bytes += size;
        return {};
    }
    if (p.direct_write_epoch && mirror_epoch - p.direct_write_epoch < 4000) {
        st_snap_gpu++;
        return {};
    }
    struct Made { uint64_t stamp = 0; std::unordered_map<uint64_t, BufferRef> at; };
    static thread_local Made made;
    if (made.stamp != mirror_epoch) made.stamp = mirror_epoch, made.at.clear();
    const uint64_t key = guest * 0x9E3779B97F4A7C15ull ^ size;
    if (const auto it = made.at.find(key); it != made.at.end() && it->second.size == size) {
        st_snap_again++;
        return it->second;
    }
    static thread_local std::vector<uint8_t> tmp;
    if (tmp.size() < size) tmp.resize(size);
    if (!host->gpu_read(gpu, tmp.data(), size)) return {};
    if (capture_on() && captures_seen.load(std::memory_order_relaxed)) {   // (as memory_read_as_submitted, the lock held already)
        for (uint64_t page = guest >> kPageShift; page < (guest + size + 4095) >> kPageShift; page++) {
            const CapEntry e = cap_entry(page);
            if (!e.gen || e.gen != page_gen(page)) continue;
            auto b = cap_bufs.find(e.gen);
            if (b == cap_bufs.end() || !b->second.map) continue;
            const uint64_t a = std::max(page << kPageShift, guest), z = std::min((page + 1) << kPageShift, guest + size);
            std::memcpy(tmp.data() + (a - guest), (const uint8_t*)b->second.map + (uint64_t)e.slot * 4096 + (a - (page << kPageShift)), z - a);
        }
    }
    const BufferRef r = stream_copy(tmp.data(), size);
    if (r) st_snap_binds++, st_snap_bytes += size, made.at[key] = r;
    else st_snap_failed++;
    return r;
}

BufferRef gpu_buffer_bind(uint64_t gpu, uint64_t size, bool written) {
''')

# 2. o caminho rápido (sem a trava): com a cópia ligada, a leitura de um bloco sem espelho vai para o caminho com a trava
troca(
    "        if (!mirror_on() || !mirror_upload || p->mstate == Pool::MIRROR_REFUSED || p->mstate == Pool::MIRROR_WANTED)\n"
    "            return remember({p->buffer, off, size, 0});\n"
    "        if (p->mstate == Pool::MIRROR_ON && p->synced_epoch == mirror_epoch && p->sync_seg <= texture_segment())\n"
    "            return remember({p->mirror, off, size, 0});\n",
    "        const bool snap = bind_snapshot_max() && mirror_upload && p->mstate != Pool::MIRROR_ON;   // (Deckport: below, under the lock)\n"
    "        if (!snap && (!mirror_on() || !mirror_upload || p->mstate == Pool::MIRROR_REFUSED || p->mstate == Pool::MIRROR_WANTED))\n"
    "            return remember({p->buffer, off, size, 0});\n"
    "        if (p->mstate == Pool::MIRROR_ON && p->synced_epoch == mirror_epoch && p->sync_seg <= texture_segment())\n"
    "            return remember({p->mirror, off, size, 0});\n")

# 3. sem espelho nenhum (RX_VK_MIRROR=0) ou bloco recusado
troca(
    "    if (!mirror_on() || !mirror_upload || p->mstate == Pool::MIRROR_REFUSED) {\n"
    "        if (written) note_direct_write(*p, off, size);\n",
    "    if (!mirror_on() || !mirror_upload || p->mstate == Pool::MIRROR_REFUSED) {\n"
    "        if (!written && mirror_upload && p->direct_write_epoch != mirror_epoch)   // (Deckport)\n"
    "            if (const BufferRef r = bind_snapshot(*p, gpu, guest, size)) return r;\n"
    "        if (written) note_direct_write(*p, off, size);\n")

# 4. bloco que queria espelho e não coube no limite
troca(
    "    if (p->mstate != Pool::MIRROR_ON) {\n"
    "        auto& e = direct_by_pool[p->lo];\n",
    "    if (p->mstate != Pool::MIRROR_ON) {\n"
    "        if (!written && p->direct_write_epoch != mirror_epoch)   // (Deckport)\n"
    "            if (const BufferRef r = bind_snapshot(*p, gpu, guest, size)) return r;\n"
    "        auto& e = direct_by_pool[p->lo];\n")

# 5. a linha do log, junto das outras a cada 600 envios
troca(
    '            logf("vk:   read live, by pool:%s", s.c_str());\n',
    '            logf("vk:   read live, by pool:%s", s.c_str());\n'
    "            if (bind_snapshot_max()) {   // (Deckport)\n"
    "                static int64_t l_n, l_b, l_big, l_bigb;\n"
    '                logf("vk:   bind snapshots (600 submits): %lld copied, %.1f MB; %lld over the size left in guest memory, %.0f MB; %lld with no room; in all %lld bound again, %lld of pools the GPU writes",\n'
    "                     (long long)(st_snap_binds - l_n), (st_snap_bytes - l_b) / 1048576.0, (long long)(st_snap_big - l_big),\n"
    "                     (st_snap_big_bytes - l_bigb) / 1048576.0, (long long)st_snap_failed, (long long)st_snap_again, (long long)st_snap_gpu);\n"
    "                l_n = st_snap_binds, l_b = st_snap_bytes, l_big = st_snap_big, l_bigb = st_snap_big_bytes;\n"
    "            }\n")

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")

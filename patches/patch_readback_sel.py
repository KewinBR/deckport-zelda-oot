# Deckport: espera seletiva dos resultados da GPU (gpu/vk/vk_replay.cpp, readback de buffers).
# RX_VK_NO_READBACK_WAIT=1 tira todas as esperas: +fps no Deck, mas o medidor de exposição do OoT é lido antes da hora
# e a exposição pisca (o comentário "white flashes" do próprio Hookshot). Com a espera, o fps cai uns 25% em Kokiri.
#   RX_VK_READBACK_ONLY=<tamanhos>   espera só pelos readbacks desses tamanhos (hex ou decimal, separados por vírgula)
#   RX_VK_READBACK_SKIP=<tamanhos>   espera por todos menos esses
# Os dois valem com RX_VK_NO_READBACK_WAIT ausente. Uso: python3 patch_readback_sel.py <árvore do Hookshot>
import sys, os
p = os.path.join(sys.argv[1], 'gpu', 'vk', 'vk_replay.cpp')
s = open(p).read()
marca = '(Deckport: RX_VK_READBACK_ONLY'
if marca in s:
    print('já aplicado'); sys.exit(0)
antes = '''        if (!off && (memory_writeback_value(host->gpu_guest(gpu), size, &ever), ever)) {
            memory_note_readback(host->gpu_guest(gpu), size);   // (PR 430: the CPU may write it back: memory_rb_refresh)'''
assert s.count(antes) == 1, 'trecho do readback não achado'
depois = '''        // (Deckport: RX_VK_READBACK_ONLY / RX_VK_READBACK_SKIP, lists of sizes: wait only for, or for all but, those readbacks.
        // The Deck's frame lost ~25% to the waits; OoT's exposure meter needs its wait, the culling ranges do not)
        static const std::vector<uint64_t> rb_only = [] { std::vector<uint64_t> v; if (const char* e = getenv("RX_VK_READBACK_ONLY"))
            for (const char* q = e; *q;) { char* end; const uint64_t x = strtoull(q, &end, 0); if (end == q) break; v.push_back(x); q = *end ? end + 1 : end; }
            return v; }();
        static const std::vector<uint64_t> rb_skip = [] { std::vector<uint64_t> v; if (const char* e = getenv("RX_VK_READBACK_SKIP"))
            for (const char* q = e; *q;) { char* end; const uint64_t x = strtoull(q, &end, 0); if (end == q) break; v.push_back(x); q = *end ? end + 1 : end; }
            return v; }();
        const bool rb_sel = (!rb_only.empty() && std::find(rb_only.begin(), rb_only.end(), (uint64_t)size) == rb_only.end()) ||
                            std::find(rb_skip.begin(), rb_skip.end(), (uint64_t)size) != rb_skip.end();
        if (!off && !rb_sel && (memory_writeback_value(host->gpu_guest(gpu), size, &ever), ever)) {
            memory_note_readback(host->gpu_guest(gpu), size);   // (PR 430: the CPU may write it back: memory_rb_refresh)'''
s = s.replace(antes, depois, 1)
if '#include <algorithm>' not in s:
    s = '#include <algorithm>\n' + s
open(p, 'w').write(s)
print('ok')

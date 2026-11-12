# Deckport: o relatório dos marcadores (trava da GPU, RX_VK_CHECKPOINTS) diz também o código nativo de cada estágio do
# programa (o mesmo "its code:" do RX_VK_SKIP_CODE), pra achar o shader que trava sem reproduzir a cena com dump.
# Guardado uma vez por programa, só com os marcadores ligados. Uso: python3 patch_markercodes.py gpu/vk/vk_draw.cpp
import sys
p = sys.argv[1]
s = open(p).read()

a = 'std::atomic<uint32_t> checkpoint_n{0};\n'
assert s.count(a) == 1, 'checkpoint_n'
s = s.replace(a, a + '''// (Deckport) each marked program's stage codes, for the report (program_code_keys, noted once a program at its first draw)
std::mutex marker_codes_mu;
std::unordered_map<uint64_t, std::string> marker_codes;
std::string marker_codes_of(uint64_t key) {
    std::lock_guard lk(marker_codes_mu);
    const auto it = marker_codes.find(key);
    return it == marker_codes.end() ? std::string() : it->second;
}
''', 1)

a = '''        logf("vk:   %s: marker %u (%s %016llx, frame %llu)", what, s, checkpoint_kind(k.kind), (unsigned long long)k.prog,
             (unsigned long long)k.frame);'''
assert s.count(a) == 1, 'line'
s = s.replace(a, '''        const std::string codes = (k.kind == 'd' || k.kind == 'c' || k.kind == 'i') ? marker_codes_of(k.prog) : std::string();
        logf("vk:   %s: marker %u (%s %016llx, frame %llu)%s%s", what, s, checkpoint_kind(k.kind), (unsigned long long)k.prog,
             (unsigned long long)k.frame, codes.empty() ? "" : "; its code:", codes.c_str());''', 1)

a = '''        static const char* skip_code_list = getenv("RX_VK_SKIP_CODE");'''
assert s.count(a) == 1, 'skip_code'
s = s.replace(a, '''        if (checkpoints_on()) {   // (Deckport: the codes for the markers' report)
            std::lock_guard lk(marker_codes_mu);
            if (marker_codes.find(cp->key) == marker_codes.end()) marker_codes.emplace(cp->key, program_code_keys(s));
        }
''' + a, 1)
open(p, 'w').write(s)
print('ok')

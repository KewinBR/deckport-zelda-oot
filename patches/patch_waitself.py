# Deckport: RX_VK_WAIT_GPU=-1 espera o trabalho de GPU do próprio quadro no present (o 1 espera só o anterior).
# No APU do Deck o jogo escreve o medidor de exposição do quadro seguinte antes de a GPU ler o atual: flashes pretos e
# brancos ao girar a câmera. Ideia da issue #1186 do Hookshot (myylkn), onde tirou todos os flashes.
# Uso: python3 patch_waitself.py gpu/vk/vk_replay.cpp
import sys
p = sys.argv[1]
s = open(p).read()
old = '''            if (ahead > 0) {
                const uint64_t old = values[presents % ahead];
                values[presents % ahead] = value;
                if (old) wait_value(old);
            }'''
assert s.count(old) == 1, 'wait_gpu'
s = s.replace(old, old + '''
            else if (ahead < 0) wait_value(value);   // (Deckport: -1, o próprio quadro, issue #1186)''', 1)
# (v2.0.12 em diante: o valor passou a ser limitado a 0..8 e o -1 virava 0, sem espera nenhuma: a piscada voltou, até na
# interface, 2026-11-10. Sem este trecho o patch aplica e não faz nada.)
clamp = 'return (int)std::clamp<long>(count, 0, capacity);'
if clamp in s:
    s = s.replace(clamp, 'return (int)std::clamp<long>(count, -1, capacity);   // (Deckport: -1 kept, the frame itself; '
                         'v2.0.12 clamped it to 0)', 1)
open(p, 'w').write(s)
print('ok')

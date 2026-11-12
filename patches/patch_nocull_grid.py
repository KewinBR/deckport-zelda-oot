# Deckport: o NOCULL (RX_VK_MESH_NOCULL) troca o "visível" do task shader de culling 2c56dc1006942f74 por verdadeiro, mas
# o laço que percorre as células da grade de profundidade continua no programa: a eliminação de código morto não tira um
# laço (as variáveis do laço usam umas às outras). No Rancho Lon Lon, virando a câmera para a paisagem, um desenho com esse
# task shader passou do tempo da GPU e ela foi reiniciada (2026-11-10, três vezes no mesmo save, com programas diferentes,
# sempre com o 2c56dc1006942f74). Aqui a grade passa a ter uma célula só: as leituras do tamanho dela (cbuf 3, offsets
# 3088 e 3092) viram 1, e o laço roda uma vez. O resultado do laço já não decide nada (o NOCULL desenha tudo).
# RX_VK_MESH_NOCULL_GRID=0 desliga.
# Uso: python3 patch_nocull_grid.py gpu/vk/vk_shader.cpp
import sys
p = sys.argv[1]
s = open(p).read()
a = '''    if (made) Shader::Optimization::DeadCodeEliminationPass(program);
    static std::atomic<int> told{0};'''
b = '''    int grid = 0;   // (Deckport, patches/patch_nocull_grid.py: a grade de uma célula só, o laço roda uma vez)
    static const bool grid_on = !getenv("RX_VK_MESH_NOCULL_GRID") || atoi(getenv("RX_VK_MESH_NOCULL_GRID")) != 0;
    if (made && grid_on)
        for (Block* block : program.blocks)
            for (Inst& inst : block->Instructions()) {
                const Opcode op = inst.GetOpcode();
                // (o shader lê largura e altura juntas, GetCbufU32x2 #3, #3088, e tira cada uma com CompositeExtractU32x2:
                // o limite do laço é min(..., largura - 1). Com 1, o laço roda uma vez)
                if (op == Opcode::CompositeExtractU32x2) {
                    const Value src = inst.Arg(0).Resolve();
                    if (src.IsImmediate()) continue;
                    const Inst* c = src.InstRecursive();
                    if (c->GetOpcode() != Opcode::GetCbufU32x2) continue;
                    const Value bank = c->Arg(0).Resolve(), off = c->Arg(1).Resolve();
                    if (!bank.IsImmediate() || !off.IsImmediate() || bank.U32() != 3 || off.U32() != 3088) continue;
                    inst.ReplaceUsesWith(Value{1u});
                    grid++;
                    continue;
                }
                if (op != Opcode::GetCbufU32 && op != Opcode::GetCbufF32) continue;
                const Value bank = inst.Arg(0).Resolve(), off = inst.Arg(1).Resolve();
                if (!bank.IsImmediate() || !off.IsImmediate() || bank.U32() != 3) continue;
                if (off.U32() != 3088 && off.U32() != 3092) continue;
                inst.ReplaceUsesWith(op == Opcode::GetCbufF32 ? Value{1.0f} : Value{1u});
                grid++;
            }
    if (made) Shader::Optimization::DeadCodeEliminationPass(program);
    if (grid) {
        static std::atomic<int> told_grid{0};
        if (told_grid++ < 8) logf("vk: task code %016llx: grid read %d times, made 1x1 (RX_VK_MESH_NOCULL_GRID)", (unsigned long long)code_key, grid);
    }
    static std::atomic<int> told{0};'''
assert s.count(a) == 1, 'nocull'
s = s.replace(a, b, 1)
# o cache de programas (hookshot_programs.bin) não sabe da mudança: um carimbo a mais faz ele começar de novo, uma vez
a2 = '''    const uint64_t translator = HOOKSHOT_SHADER_STAMP;
    add(&translator, sizeof translator);
'''
b2 = a2 + '''    if (!getenv("RX_VK_MESH_NOCULL_GRID") || atoi(getenv("RX_VK_MESH_NOCULL_GRID")) != 0) add("deckport-grid-2", 15);   // (patch_nocull_grid.py)
'''
assert s.count(a2) == 1, 'stamp'
s = s.replace(a2, b2, 1)
open(p, 'w').write(s)
print('ok')

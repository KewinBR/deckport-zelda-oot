# Deckport: RX_VK_MESH_NOCULL=<código de task shader,...> (padrão 2c56dc1006942f74).
# O task shader de culling do OoT (grade de oclusão, issue 817) roda por segundos no RDNA2 e a GPU é reiniciada.
# No fim dele, "visível" = (resultado & 1) | (cbuf3[2320] & 4): o bit 4 é a chave do próprio jogo pra desenhar tudo.
# Este patch troca essa decisão por "sempre visível" e roda a eliminação de código morto: os laços somem, nada some.
# Uso: python3 patch_nocull.py gpu/vk/vk_shader.cpp
import sys
p = sys.argv[1]
s = open(p).read()

inc_anchor = '#include "shader_recompiler/ir_opt/oot_visual_workaround.h"'
assert s.count(inc_anchor) == 1
s = s.replace(inc_anchor, inc_anchor + '\n#include "shader_recompiler/ir_opt/passes.h"', 1)

fn_anchor = '// ---- (hookshot) The program cache, hookshot_programs.bin beside the executable'
assert s.count(fn_anchor) == 1
fn = r'''// (Deckport) RX_VK_MESH_NOCULL=<task shader code key prefixes,...> (default 2c56dc1006942f74; "0": off). OoT's meshlet
// culling task shader walks every cell of a coarse depth grid its meshlet covers, reading four words a cell from c3 by a
// dynamic index: on RDNA 2 one draw runs past the kernel's 10 s and the GPU is reset (Hookshot issue 817). Its answer is
// visible = (result & 1) | (c3[2320] & 4), bit 4 being the game's own "draw everything". That comparison becomes true,
// and dead code elimination takes the grid walk with it: every meshlet is drawn (the rasterizer clips what is off
// screen), none is left out. A name under RX_VK_MESH, so the program cache starts again when it changes.
bool mesh_nocull_wanted(uint64_t code_key) {
    static const std::string list = getenv("RX_VK_MESH_NOCULL") ? getenv("RX_VK_MESH_NOCULL") : "2c56dc1006942f74";
    if (list.empty() || list == "0") return false;
    char hex[24];
    snprintf(hex, sizeof hex, "%016llx", (unsigned long long)code_key);
    for (size_t at = 0; at < list.size();) {
        const size_t e = list.find(',', at);
        const std::string k = list.substr(at, e == std::string::npos ? std::string::npos : e - at);
        if (!k.empty() && !strncmp(hex, k.c_str(), k.size())) return true;
        at = e == std::string::npos ? list.size() : e + 1;
    }
    return false;
}

bool reads_c3_2320_bit4(const Shader::IR::Value& v) {   // (BitwiseAnd32 of #4 and GetCbufU32 #3, #2320, through Identity)
    using namespace Shader::IR;
    const Value r = v.Resolve();
    if (r.IsImmediate()) return false;
    const Inst* and_ = r.InstRecursive();
    if (and_->GetOpcode() != Opcode::BitwiseAnd32) return false;
    bool four = false, cbuf = false;
    for (size_t i = 0; i < 2; i++) {
        const Value a = and_->Arg(i).Resolve();
        if (a.IsImmediate()) {
            four = four || a.U32() == 4;
            continue;
        }
        const Inst* c = a.InstRecursive();
        if (c->GetOpcode() != Opcode::GetCbufU32) continue;
        const Value bank = c->Arg(0).Resolve(), off = c->Arg(1).Resolve();
        cbuf = cbuf || (bank.IsImmediate() && off.IsImmediate() && bank.U32() == 3 && off.U32() == 2320);
    }
    return four && cbuf;
}

void mesh_nocull(Shader::IR::Program& program, uint64_t code_key) {
    using namespace Shader::IR;
    if (!mesh_nocull_wanted(code_key)) return;
    int made = 0;
    for (Block* block : program.blocks)
        for (Inst& inst : block->Instructions()) {
            if (inst.GetOpcode() != Opcode::INotEqual) continue;
            const Value zero = inst.Arg(1).Resolve();
            if (!zero.IsImmediate() || zero.U32() != 0) continue;
            const Value orv = inst.Arg(0).Resolve();
            if (orv.IsImmediate()) continue;
            const Inst* o = orv.InstRecursive();
            if (o->GetOpcode() != Opcode::BitwiseOr32) continue;
            if (!reads_c3_2320_bit4(o->Arg(0)) && !reads_c3_2320_bit4(o->Arg(1))) continue;
            inst.ReplaceUsesWith(Value{true});
            made++;
        }
    if (made) Shader::Optimization::DeadCodeEliminationPass(program);
    static std::atomic<int> told{0};
    if (told++ < 8)
        logf("vk: task code %016llx: culling %s (RX_VK_MESH_NOCULL)", (unsigned long long)code_key,
             made ? "off, every meshlet drawn" : "pattern not found, left as it is");
}

'''
s = s.replace(fn_anchor, fn + fn_anchor, 1)

call_old = '''            task_t = translate(env, true, true);
            dump_ir(p, "task", task_t->program, task->key);'''
assert s.count(call_old) == 1, "task call"
s = s.replace(call_old, '''            task_t = translate(env, true, true);
            mesh_nocull(task_t->program, task->key);   // (Deckport)
            dump_ir(p, "task", task_t->program, task->key);''', 1)
open(p, 'w').write(s)
print('ok')

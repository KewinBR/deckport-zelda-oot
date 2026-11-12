#!/usr/bin/env python3
"""Deckport: deixa o build do hookshot_vk.so receber opções de otimização por variável de ambiente.
RX_VK_OPT (padrão O2), RX_VK_CXX_EXTRA (ex.: "-flto=thin -fprofile-instr-use=x.profdata"), RX_VK_LD_EXTRA.
Uso: patch_build_opt.py <árvore do hookshot>. Idempotente."""
import sys, os
p = os.path.join(sys.argv[1], "nx2", "build.py")
s = open(p, encoding="utf-8").read()
if "RX_VK_CXX_EXTRA" in s:
    print("já aplicado"); sys.exit(0)
a = '"-std=c++20", "-O2", "-g0", "-DNDEBUG", "-Wno-everything", "-DVK_NO_PROTOTYPES", "-DMKWVK_BUILDING",'
b = '"-std=c++20", "-" + os.environ.get("RX_VK_OPT", "O2"), *os.environ.get("RX_VK_CXX_EXTRA", "").split(), "-g0", "-DNDEBUG", "-Wno-everything", "-DVK_NO_PROTOTYPES", "-DMKWVK_BUILDING",'
assert s.count(a) == 1, "flags do renderizador não encontradas"
s = s.replace(a, b)
a = '"-fuse-ld=lld", "-shared", "-o", vdll,'
b = '"-fuse-ld=lld", "-shared", *os.environ.get("RX_VK_LD_EXTRA", "").split(), "-o", vdll,'
assert s.count(a) == 1, "link do renderizador não encontrado"
s = s.replace(a, b)
open(p, "w", encoding="utf-8").write(s)
print("ok")

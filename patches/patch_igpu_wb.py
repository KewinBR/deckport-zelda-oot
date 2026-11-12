# Deckport: a ideia da issue 1126 do Hookshot (drpowerup), corrigida. Sem espelho (GPU integrada) as páginas que a
# GPU escreve não entravam na tabela de write-back (wb_pages), e a espera do PR 645 (a cópia de uma página que a GPU
# ainda escreve espera essa escrita) nunca agia: o medidor de exposição era lido antes da GPU terminar o quadro.
# O patch original anotava as páginas com o valor da gravação em curso; take_capture esperava esse valor, que só é
# enviado depois dela: o jogo travou no carregamento (Deck, 2026-11-09). Aqui a espera só vale pra um valor anterior
# ao da gravação que usa a captura. Uso: python3 patch_igpu_wb.py gpu/vk/vk_memory.cpp
import sys
p = sys.argv[1]
s = open(p).read()

a = '''        if (mirror_on()) { auto& e = direct_by_pool[p->lo]; e.first++, e.second = mirror_upload ? (int)p->mstate : 9; direct_bytes_by_pool[p->lo] += size; }
'''
assert s.count(a) == 1, 'direct bind'
s = s.replace(a, a + '''        // (Deckport, issue 1126's idea: GPU results written in place with no mirror (integrated GPUs) noted as the mirror path
        // does, so the capture's wait for a page still being written back covers them; take_capture skips a value not yet
        // submitted)
        static const bool igpu_wb = getenv("RX_VK_IGPU_WB") && atoi(getenv("RX_VK_IGPU_WB")) != 0;   // (opt-in while tested)
        if (igpu_wb && written && size <= (1u << 20))
            wb_pages_note(p->lo + off, p->lo + std::min(off + size, p->hi - p->lo), mem_rec_value);
''', 1)

a = '''    if (c->late_value && c->map) {   // (the pages a submission still on the GPU writes back: see capture_make)'''
assert s.count(a) == 1, 'take_capture'
s = s.replace(a, '''    if (c->late_value && c->map && c->late_value < value) {   // (the pages a submission still on the GPU writes back: see
                                                              // capture_make; Deckport: never the one being recorded)''', 1)
open(p, 'w').write(s)
print('ok')

# Deckport: RX_VK_SHADOW_DIV=<n> (2 por padrão; 1 desliga). O jogo cria um mapa de sombra de 12288x12288 (D16, 288 MB) e
# desenha nele com viewport e scissor em pixels desse tamanho. Aqui a imagem nasce com 1/n do lado (6144: 72 MB, 1/4 dos
# pixels no passo de sombra) e os passos que desenham só nela (sem cor) têm viewport, scissor e clears divididos por n.
# Quem lê a sombra lê em coordenadas de 0 a 1: a imagem menor serve igual, com a sombra um pouco menos nítida.
# A imagem não tem mais a forma da memória do jogo: nada é enviado da memória pra ela (a primeira vez ela é limpa com 0,
# o que o jogo ainda não desenhou) nem lido dela de volta, e cópias entre ela e outras texturas são puladas (com aviso).
# Só profundidade, 2D, um nível, uma camada, a partir de 8192 de lado (o jogo cria o de 12288 primeiro como textura comum, não como alvo: as_target não serve de filtro).
# Uso: python3 patch_shadowdiv.py <raiz do Hookshot>   (gpu/vk/vk_texture.h, vk_texture.cpp, vk_draw.cpp, vk_xfer.cpp)
import sys, os
root = sys.argv[1]


def edit(rel, pairs):
    p = os.path.join(root, rel)
    s = open(p).read()
    for a, b, tag in pairs:
        assert s.count(a) == 1, (rel, tag, s.count(a))
        s = s.replace(a, b, 1)
    open(p, 'w').write(s)


edit('gpu/vk/vk_texture.h', [(
    '    uint32_t skip = 0;        // top levels of the texture left out (huge textures: RX_VK_TEX_MAX_DIM, _MAX_MB)\n',
    '    uint32_t skip = 0;        // top levels of the texture left out (huge textures: RX_VK_TEX_MAX_DIM, _MAX_MB)\n'
    '    uint32_t shrink = 0;      // (Deckport, RX_VK_SHADOW_DIV) a huge depth target made 1/shrink of its size\n', 'campo')])

edit('gpu/vk/vk_texture.cpp', [
    ('''    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.flags = flags;
    ci.imageType = x.type;''',
     '''    {   // (Deckport, patches/patch_shadowdiv.py: the 12288 x 12288 shadow map made smaller)
        static const uint32_t sdiv = getenv("RX_VK_SHADOW_DIV") ? (uint32_t)std::max(1, atoi(getenv("RX_VK_SHADOW_DIV"))) : 2u;
        if (sdiv > 1 && is_depth_format(x.format) && !(x.aspect & VK_IMAGE_ASPECT_STENCIL_BIT) &&
            x.type == VK_IMAGE_TYPE_2D && x.levels == 1 && x.layers == 1 && x.samples == VK_SAMPLE_COUNT_1_BIT &&
            !x.sparse && x.width >= 8192 && x.height >= 8192) {
            static int told;
            if (told++ < 8)
                logf("vk: depth target %ux%u made %ux%u (RX_VK_SHADOW_DIV=%u: its passes' viewport and scissor divided)", x.width,
                     x.height, x.width / sdiv, x.height / sdiv, sdiv);
            x.width /= sdiv, x.height /= sdiv, x.shrink = sdiv;
        }
    }
    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.flags = flags;
    ci.imageType = x.type;''', 'criação'),
    ('''    if (tex.bc) return false;   // (no CPU path into BC3)
''',
     '''    if (tex.bc) return false;   // (no CPU path into BC3)
    if (tex.shrink) {   // (Deckport, RX_VK_SHADOW_DIV: not the guest's shape: cleared once, never uploaded)
        if (!tex.uploaded) {
            VkCommandBuffer cmd = upload_cmd();
            full_barrier(cmd);
            const VkClearDepthStencilValue z{0.0f, 0};
            const VkImageSubresourceRange r{VK_IMAGE_ASPECT_DEPTH_BIT, 0, tex.levels, 0, tex.layers};
            vkCmdClearDepthStencilImage(cmd, tex.image, VK_IMAGE_LAYOUT_GENERAL, &z, 1, &r);
            full_barrier(cmd);
        }
        return up_route = UP_GPU, true;
    }
''', 'envio'),
    ('''bool flush_record(Flush& f) {
    Texture& t = *f.t;
''', '''bool flush_record(Flush& f) {
    Texture& t = *f.t;
    if (t.shrink) return f.ok = false;   // (Deckport, RX_VK_SHADOW_DIV: not the guest's shape)
''', 'leitura'),
])

edit('gpu/vk/vk_draw.cpp', [
    ('''    float vx = s.viewport[0][0], vy = s.viewport[0][1], vw = s.viewport[0][2], vh = s.viewport[0][3];
    if (vw == 0.0f && vh == 0.0f) vx = 0, vy = 0, vw = (float)at.width, vh = (float)at.height;''',
     '''    float vx = s.viewport[0][0], vy = s.viewport[0][1], vw = s.viewport[0][2], vh = s.viewport[0][3];
    // (Deckport, RX_VK_SHADOW_DIV: a pass into a shrunk depth target alone: the game's pixels divided)
    const int32_t shr = (at.depth && at.depth->shrink > 1 && !at.n) ? (int32_t)at.depth->shrink : 1;
    if (shr > 1) vx /= (float)shr, vy /= (float)shr, vw /= (float)shr, vh /= (float)shr;
    if (vw == 0.0f && vh == 0.0f) vx = 0, vy = 0, vw = (float)at.width, vh = (float)at.height;''', 'viewport'),
    ('''        const int32_t x0 = std::max(0, s.scissor[0]), y0 = std::max(0, s.scissor[1]);
        const int32_t x1 = std::min<int32_t>(s.scissor[0] + s.scissor[2], (int32_t)at.width);
        const int32_t y1 = std::min<int32_t>(s.scissor[1] + s.scissor[3], (int32_t)at.height);''',
     '''        const int32_t x0 = std::max(0, s.scissor[0] / shr), y0 = std::max(0, s.scissor[1] / shr);
        const int32_t x1 = std::min<int32_t>((s.scissor[0] + s.scissor[2] + shr - 1) / shr, (int32_t)at.width);
        const int32_t y1 = std::min<int32_t>((s.scissor[1] + s.scissor[3] + shr - 1) / shr, (int32_t)at.height);''', 'scissor'),
    ('''    clear_after_draws(cmd);
    begin_pass(cmd, at);
    const VkRect2D rect = clear_rect(s, at.width, at.height);''',
     '''    clear_after_draws(cmd);
    begin_pass(cmd, at);
    const uint32_t cshr = at.depth->shrink > 1 && !at.n ? at.depth->shrink : 1;   // (Deckport, RX_VK_SHADOW_DIV)
    VkRect2D rect = clear_rect(s, at.width * cshr, at.height * cshr);
    if (cshr > 1) {
        const uint32_t x1 = std::min(at.width, (rect.offset.x + rect.extent.width + cshr - 1) / cshr);
        const uint32_t y1 = std::min(at.height, (rect.offset.y + rect.extent.height + cshr - 1) / cshr);
        rect.offset.x /= (int32_t)cshr, rect.offset.y /= (int32_t)cshr;
        rect.extent.width = x1 > (uint32_t)rect.offset.x ? x1 - rect.offset.x : 0;
        rect.extent.height = y1 > (uint32_t)rect.offset.y ? y1 - rect.offset.y : 0;
    }''', 'clear'),
])

edit('gpu/vk/vk_xfer.cpp', [
    ('''    if (!resolve(p.dst, &p.dv, p.has_dv != 0, p.dr, d, true)) return;
''', '''    if (!resolve(p.dst, &p.dv, p.has_dv != 0, p.dr, d, true)) return;
    if (s.tex->shrink || d.tex->shrink) {   // (Deckport, RX_VK_SHADOW_DIV: not the guest's shape)
        warn(8, "texture copy with a shrunk depth target (RX_VK_SHADOW_DIV): skipped");
        return;
    }
''', 't2t'),
    ('''    const bool astc = to_image && p.tex && vk_format(view_nvn_format(p.tex, p.has_view ? &p.view : nullptr)).astc;
''', '''    const bool astc = to_image && p.tex && vk_format(view_nvn_format(p.tex, p.has_view ? &p.view : nullptr)).astc;
    if (p.tex)
        if (Texture* st_ = texture_get(p.tex, false); st_ && st_->shrink) {   // (Deckport, RX_VK_SHADOW_DIV)
            warn(9, "buffer copy with a shrunk depth target (RX_VK_SHADOW_DIV): skipped");
            return;
        }
''', 'b2t'),
])
print('ok')

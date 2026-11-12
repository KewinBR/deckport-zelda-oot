# Deckport: alvo de profundidade grande e ainda zerado vira um clear na GPU, em vez do envio pela CPU.
# Ao entrar no castelo o jogo cria um alvo de profundidade de 12288x12288 (NVN 0x32, 288 MB, o mapa de sombra) e o
# renderizador o envia pela CPU (o envio pela GPU deixa de fora formatos de profundidade): "slow upload 3501 ms" no Deck,
# 3,5 s parado no carregamento. O jogo ainda não desenhou nele, a memória é toda zero: limpar a imagem com 0 dá o mesmo
# resultado. Só textura nova (sem faixa suja), só profundidade, só a partir de 16 MB, e só se a memória do jogo não tiver
# cópia capturada (memory_has_shadow), como o envio pela GPU. RX_VK_DEPTH_ZERO=0 desliga.
# Uso: python3 patch_depthzero.py gpu/vk/vk_texture.cpp
import sys
p = sys.argv[1]
s = open(p).read()
a = '''    if (tex.bc) return false;   // (no CPU path into BC3)
'''
assert s.count(a) == 1, 'bc'
s = s.replace(a, a + r'''    {   // (Deckport, patches/patch_depthzero.py) a new big depth target still all zero: cleared on the GPU, not unswizzled on
        // the CPU (the 12288x12288 shadow target as the castle loads: 3.5 s on the Deck)
        static const bool on = !getenv("RX_VK_DEPTH_ZERO") || atoi(getenv("RX_VK_DEPTH_ZERO")) != 0;
        if (on && !dirty && !tex.uploaded && is_depth_format(tex.format) && !(tex.aspect & VK_IMAGE_ASPECT_STENCIL_BIT) &&
            total >= (16u << 20) && !(tex.gpu < (1ull << 40) && memory_has_shadow(tex.gpu, total))) {
            bool zero = true;
            std::vector<uint8_t> part;
            for (uint64_t at = 0; at < total && zero; at += (1u << 20)) {
                const uint64_t n = std::min<uint64_t>(1u << 20, total - at);
                uint64_t avail = 0;
                const uint8_t* d = host->gpu_ptr(tex.gpu + at, &avail);
                if (!d || avail < n) part.assign(n, 1), host->gpu_read(tex.gpu + at, part.data(), n), d = part.data();
                const uint64_t* w = (const uint64_t*)d;
                for (uint64_t i = 0; i < n / 8; i++)
                    if (w[i]) { zero = false; break; }
                for (uint64_t i = n / 8 * 8; zero && i < n; i++)
                    if (d[i]) zero = false;
            }
            if (zero) {
                VkCommandBuffer cmd = upload_cmd();
                full_barrier(cmd);
                const VkClearDepthStencilValue z{0.0f, 0};
                const VkImageSubresourceRange r{VK_IMAGE_ASPECT_DEPTH_BIT, 0, tex.levels, 0, tex.layers};
                vkCmdClearDepthStencilImage(cmd, tex.image, VK_IMAGE_LAYOUT_GENERAL, &z, 1, &r);
                full_barrier(cmd);
                static int told;
                if (told++ < 20)
                    logf("vk: depth target #%u %ux%u NVN %#x (%llu MB) all zero: cleared on the GPU, not uploaded (RX_VK_DEPTH_ZERO)",
                         tex.id, tex.width, tex.height, tex.nvn_format, (unsigned long long)(total >> 20));
                return up_route = UP_GPU, true;
            }
        }
    }
''', 1)
open(p, 'w').write(s)
print('ok')

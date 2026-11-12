# Deckport: RX_VK_AFLASH=1, um detector de flash que não espera a GPU. O RX_VK_FLASH do Hookshot lê cada quadro com
# wait_value e isso esconde o flash de tempo do Deck (o jogo zera o medidor de exposição antes da GPU usar). Aqui cada
# present copia uma miniatura 64x36 da imagem final pra um de 8 buffers, e só lê os quadros que a GPU já terminou
# (vk_timeline_completed, sem bloquear). Flash: um quadro diferente dos dois vizinhos numa área onde eles concordam
# (o mesmo critério do RX_VK_FLASH: 48 de diferença, 40 células). Log: cada flash e um resumo a cada 600 quadros lidos.
# Uso: python3 patch_aflash.py gpu/vk/vk_replay.cpp
import sys
p = sys.argv[1]
s = open(p).read()

a = 'VmaAllocation shot_image_alloc = nullptr;\n'
assert s.count(a) == 1, 'shot_image_alloc'
s = s.replace(a, a + r'''
// (Deckport) RX_VK_AFLASH=1: flashes counted without waiting for the GPU (patches/patch_aflash.py)
constexpr uint32_t kAfW = 64, kAfH = 36, kAfRing = 8;
VkImage af_image = VK_NULL_HANDLE;
VmaAllocation af_image_alloc = nullptr;
VkBuffer af_bufs[kAfRing] = {};
VmaAllocation af_allocs[kAfRing] = {};
void* af_maps[kAfRing] = {};
uint64_t af_values[kAfRing] = {};
int64_t af_presents[kAfRing] = {};
bool aflash_on() {
    static const bool on = getenv("RX_VK_AFLASH") && atoi(getenv("RX_VK_AFLASH")) != 0;
    return on;
}
bool aflash_init();
void aflash_read(uint64_t done);
''', 1)

a = 'bool offscreen_init() {\n'
assert s.count(a) == 1, 'offscreen_init'
s = s.replace(a, r'''bool aflash_init() {
    if (af_image) return true;
    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.imageType = VK_IMAGE_TYPE_2D;
    ci.format = VK_FORMAT_R8G8B8A8_UNORM;
    ci.extent = {kAfW, kAfH, 1};
    ci.mipLevels = ci.arrayLayers = 1;
    ci.samples = VK_SAMPLE_COUNT_1_BIT;
    ci.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    if (!create_image(ci, af_image, af_image_alloc)) return false;
    for (uint32_t i = 0; i < kAfRing; i++)
        if (!create_buffer((uint64_t)kAfW * kAfH * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT, true, af_bufs[i], af_allocs[i], &af_maps[i]))
            return false;
    logf("vk: RX_VK_AFLASH: flashes counted from a 64x36 copy of each present, read once the GPU is past it (no wait)");
    return true;
}
void aflash_read(uint64_t done) {
    // (the finished slots in present order; a gap (a slot still busy when its turn came) starts the run again)
    static std::vector<uint8_t> fa, fb;
    static int64_t pa = -2, pb = -2;
    static int64_t frames = 0, flashes = 0, flashes_total = 0, up_total = 0;
    for (;;) {
        int pick = -1;
        for (uint32_t i = 0; i < kAfRing; i++)
            if (af_values[i] && af_values[i] <= done && (pick < 0 || af_presents[i] < af_presents[pick])) pick = (int)i;
        if (pick < 0) return;
        const uint8_t* m = (const uint8_t*)af_maps[pick];
        std::vector<uint8_t> fc(m, m + (size_t)kAfW * kAfH * 4);
        const int64_t pc = af_presents[pick];
        af_values[pick] = 0;
        frames++;
        if (pb == pc - 1 && pa == pc - 2) {
            int hits = 0, up = 0;
            for (uint32_t i = 0; i < kAfW * kAfH; i++) {
                int dab = 0, dbc = 0, dac = 0;
                for (int ch = 0; ch < 3; ch++) {
                    const int a = fa[i * 4 + ch], b = fb[i * 4 + ch], c = fc[i * 4 + ch];
                    dab = std::max(dab, std::abs(a - b)), dbc = std::max(dbc, std::abs(b - c)), dac = std::max(dac, std::abs(a - c));
                }
                if (dab > 48 && dbc > 48 && dac < 16) hits++, up += fb[i * 4 + 1] > fa[i * 4 + 1];
            }
            if (hits >= 40) {
                flashes++, flashes_total++, up_total += up * 2 > hits;
                static int told = 0;
                if (told++ < 200)
                    logf("vk: aflash at present %lld: %d of %u cells, %s", (long long)pb, hits, kAfW * kAfH,
                         up * 2 > hits ? "brighter" : "darker");
            }
        }
        pa = pb, fa.swap(fb);
        pb = pc, fb = std::move(fc);
        if (frames % 600 == 0) {
            logf("vk: aflash: %lld flashes in the last 600 frames read (%lld in all, %lld brighter; %.1f per 1000)", (long long)flashes,
                 (long long)flashes_total, (long long)up_total, flashes_total * 1000.0 / frames);
            flashes = 0;
        }
    }
}
bool offscreen_init() {
''', 1)

a = '        if (src && (dev.offscreen || shots) && offscreen_init()) {\n'
assert s.count(a) == 1, 'present block'
s = s.replace(a, r'''        if (aflash_on()) {   // (Deckport: RX_VK_AFLASH)
            aflash_read(vk_timeline_completed());
            const uint32_t slot = (uint32_t)(presents % kAfRing);
            if (src && !af_values[slot] && aflash_init()) {
                image_barrier(r.cmd, af_image, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
                blit_crop(r.cmd, src, sw, sh, crop, af_image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, kAfW, kAfH);
                image_barrier(r.cmd, af_image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
                const VkBufferImageCopy c{0, 0, 0, {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1}, {0, 0, 0}, {kAfW, kAfH, 1}};
                vkCmdCopyImageToBuffer(r.cmd, af_image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, af_bufs[slot], 1, &c);
                af_values[slot] = value, af_presents[slot] = presents;
            }
        }
''' + a, 1)
open(p, 'w').write(s)
print('ok')

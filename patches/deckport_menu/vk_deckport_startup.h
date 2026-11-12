// (Deckport) A tela de abertura do port, animada, no lugar da tela do Hookshot enquanto os shaders são preparados.
// Pedido do Kewin: fundo preto, o logo do jogo aparece, um flare passa revelando "STEAMDECK VERSION" e só então
// entra a barra dos shaders. Depois disso, brilhos discretos no logo e um reflexo correndo na barra.
// O logo é o assets/hookshot.png da árvore (trocado pelo patch_tela_abertura.py pelo logo do port, 640x478, com
// "STEAMDECK VERSION" na faixa de baixo: kSv*). Incluído em vk_menu.cpp, dentro do namespace anônimo, antes do
// draw_startup. RX_VK_DECKPORT_STARTUP=0 volta à tela do Hookshot. RX_VK_DP_STARTUP_T=<segundos> congela a animação
// num instante (para capturas de teste).
#pragma once

namespace dp {

bool startup_on() {
    static int v = -1;
    if (v < 0) {
        const char* e = getenv("RX_VK_DECKPORT_STARTUP");
        v = !e || atoi(e) != 0;
    }
    return v != 0;
}

// (onde "STEAMDECK VERSION" fica no logo, em fração da largura e da altura da imagem)
constexpr float kSvX0 = 210.0f / 640, kSvY0 = 407.0f / 478, kSvY1 = 441.0f / 478;
// (a linha do tempo, em segundos desde o primeiro quadro)
constexpr float kLogo0 = 0.35f, kLogo1 = 1.75f;   // (o logo aparece)
constexpr float kFl0 = 2.05f, kFl1 = 3.15f;       // (o flare atravessa e revela a faixa)
constexpr float kFlOut = 0.7f;                    // (o flare some)
constexpr float kBar0 = 3.3f, kBarIn = 0.6f;      // (a barra entra)
constexpr float kStartupMin = 4.2f;               // (a tela dura pelo menos isso: vk_main.cpp)

inline float st_clamp(float x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
inline float st_out(float x) { x = 1 - st_clamp(x); return 1 - x * x * x; }
inline float st_smooth(float x) { x = st_clamp(x); return x * x * (3 - 2 * x); }
inline ImU32 st_col(float a, int r = 255, int g = 255, int b = 255) { return IM_COL32(r, g, b, (int)(st_clamp(a) * 255 + 0.5f)); }

/// Um flare: halo, risco horizontal comprido, risco vertical curto e o miolo. r o raio do halo, a a força (0 a 1)
void st_flare(ui::Ctx& c, ImVec2 p, float r, float a) {
    if (a <= 0 || r <= 0) return;
    ImDrawList* d = c.d;
    for (int i = 14; i >= 1; i--) d->AddCircleFilled(p, r * i / 14.0f, st_col(a * 0.05f, 255, 232, 180), 48);
    const ImU32 mid = st_col(a * 0.9f, 255, 246, 222), end = st_col(0, 255, 246, 222);
    const float L = r * 4.2f, T = std::max(1.0f, r * 0.07f);
    d->AddRectFilledMultiColor(ImVec2(p.x - L, p.y - T), ImVec2(p.x, p.y + T), end, mid, mid, end);
    d->AddRectFilledMultiColor(ImVec2(p.x, p.y - T), ImVec2(p.x + L, p.y + T), mid, end, end, mid);
    const float V = r * 1.3f, W = std::max(1.0f, r * 0.045f);
    d->AddRectFilledMultiColor(ImVec2(p.x - W, p.y - V), ImVec2(p.x + W, p.y), end, end, mid, mid);
    d->AddRectFilledMultiColor(ImVec2(p.x - W, p.y), ImVec2(p.x + W, p.y + V), mid, mid, end, end);
    d->AddCircleFilled(p, r * 0.16f, st_col(a), 24);
}

/// O logo em pedaços: tudo menos a faixa "STEAMDECK VERSION", e a faixa só até onde o flare já passou (reveal, 0 a 1)
void st_logo(ui::Ctx& c, ImTextureData* logo, float x0, float top, float lw, float lh, float a, float reveal) {
    const ImU32 col = st_col(a);
    auto piece = [&](float ua, float va, float ub, float vb) {
        c.d->AddImage(logo->GetTexRef(), ImVec2(x0 + lw * ua, top + lh * va), ImVec2(x0 + lw * ub, top + lh * vb), ImVec2(ua, va),
                      ImVec2(ub, vb), col);
    };
    piece(0, 0, 1, kSvY0);
    piece(0, kSvY0, kSvX0, kSvY1);
    piece(0, kSvY1, 1, 1);
    if (reveal > 0) {
        c.d->PushClipRect(ImVec2(x0, top), ImVec2(x0 + lw * (kSvX0 + (1 - kSvX0) * reveal), top + lh), true);
        piece(kSvX0, kSvY0, 1, kSvY1);
        c.d->PopClipRect();
    }
}

/// Os textos da tela (vk_progress.h startup_view, em inglês) em português, como o menu do port
std::string st_pt(std::string t) {
    static const char* const kMap[][2] = {
        {"Closing", "Fechando"},
        {"Keeping what is prepared for the next start", "O que já foi preparado fica guardado para a próxima vez"},
        {"Starting the game", "Iniciando o jogo"},
        {"Preparing shaders", "Preparando os shaders"},
        {"Building pipelines", "Montando os pipelines"},
        {"Loading pipelines", "Carregando os pipelines"},
        {"This happens once after an update. Closing the window keeps what is done.",
         "Isso acontece uma vez depois de cada atualização. Se fechar o jogo, o que já foi feito fica guardado."},
        {"Reading the game's shaders", "Lendo os shaders do jogo"},
        {"Reading the pipeline notes", "Lendo as anotações dos pipelines"},
        {"Loading the shader cache", "Carregando o cache de shaders"},
        {"a few seconds left", "faltam alguns segundos"},
    };
    for (const auto& m : kMap)
        if (t == m[0]) return m[1];
    int a = 0, b = 0;
    char buf[64];
    if (sscanf(t.c_str(), "STEP %d OF %d", &a, &b) == 2) return snprintf(buf, sizeof buf, "Etapa %d de %d", a, b), buf;
    if (sscanf(t.c_str(), "about %d s left", &a) == 1 && t.find(" s left") != std::string::npos)
        return snprintf(buf, sizeof buf, "faltam uns %d s", a), buf;
    if (sscanf(t.c_str(), "about %d min left", &a) == 1) return snprintf(buf, sizeof buf, "faltam uns %d min", a), buf;
    if (t.find(" / ") != std::string::npos)   // ("16,300 / 38,809 shaders": o ponto de milhar)
        for (char& ch : t)
            if (ch == ',') ch = '.';
    return t;
}

/// (teste) RX_VK_DP_STARTUP_T definido: a tela é desenhada mesmo sem janela (capturas RX_VK_SHOT_MENU), com números de exemplo
bool startup_test() {
    static const bool on = getenv("RX_VK_DP_STARTUP_T") != nullptr;
    return on;
}

void paint_startup(ui::Ctx& c, const StartupView& view, float fade) {
    using clk = std::chrono::steady_clock;
    static const clk::time_point t0 = clk::now();
    static const float forced = getenv("RX_VK_DP_STARTUP_T") ? (float)atof(getenv("RX_VK_DP_STARTUP_T")) : -1.0f;
    StartupView v = view;
    if (startup_test() && v.title.empty()) {
        v.version = "v2.1.0", v.step = "STEP 1 OF 2", v.title = "Preparing shaders", v.pct = "42%", v.fraction = 0.42;
        v.left = "16,300 / 38,809 shaders", v.right = "about 4 min left", v.hint = "This happens once after an update. Closing the window keeps what is done.";
    }
    v.step = st_pt(v.step), v.title = st_pt(v.title), v.left = st_pt(v.left), v.right = st_pt(v.right), v.hint = st_pt(v.hint);
    const float t = forced >= 0 ? forced : std::chrono::duration<float>(clk::now() - t0).count();
    const float s = c.s, w = c.w, h = c.h, cx = w * 0.5f, k = s * 0.86f;
    c.d->AddRectFilled(ImVec2(0, 0), ImVec2(w, h), IM_COL32(0, 0, 0, 255));

    // o logo: aparece crescendo de leve para o lugar
    float aspect = 1;
    ImTextureData* logo = ui::logo(&aspect);
    const float lh = 168 * s, lw = lh * aspect, top = h * 0.5f - 180 * s, x0 = cx - lw * 0.5f;
    const float in = st_out((t - kLogo0) / (kLogo1 - kLogo0));
    const float reveal = st_smooth((t - kFl0) / (kFl1 - kFl0));
    if (logo && in > 0) {
        const float sc = 1.06f - 0.06f * in;
        st_logo(c, logo, cx - lw * sc * 0.5f, top + lh * 0.5f - lh * sc * 0.5f, lw * sc, lh * sc, in, reveal);
    } else if (!logo) {
        ui::spaced(c, c.f.heading, 42 * k, ImVec2(cx, top + lh * 0.5f), ui::alpha(ui::rgba(246, 232, 204), in), "DECKPORT", 6 * k);
    }

    // a barra e os textos, que entram depois do flare (o fundo é preto: um preto por cima faz a entrada)
    float y = top + lh + 14 * s;
    const float bar_in = st_clamp((t - kBar0) / kBarIn);
    if (bar_in > 0) {
        const std::string credit = "Deckport, feito a partir do Hookshot " + v.version;
        ui::text_centre(c, c.f.body, 14.5f * k, ImVec2(cx, y), ui::kDim, credit.c_str());
        if (!v.title.empty()) {
            y += 34 * k;
            if (!v.step.empty()) {
                ui::text_centre(c, c.f.body, 15 * k, ImVec2(cx, y), ui::kAccent, v.step.c_str());
            }
            ui::text_centre(c, c.f.heading, 24 * k, ImVec2(cx, y + 20 * k), ui::kInk, v.title.c_str());
            const float bx0 = cx - 270 * k, bx1 = cx + 270 * k, by = y + 64 * k;
            float under = by;
            if (v.fraction >= 0) {
                const float bh = 26 * k, pad = 4 * k, fx = bx0 + pad + (bx1 - bx0 - 2 * pad) * (float)std::min(v.fraction, 1.0);
                c.d->AddRectFilled(ImVec2(bx0, by), ImVec2(bx1, by + bh), ui::kCellDark);
                c.d->AddRect(ImVec2(bx0, by), ImVec2(bx1, by + bh), ui::kEdge, 0, std::max(1.0f, s));
                if (fx > bx0 + pad) {
                    ui::gold(c, ImVec2(bx0 + pad, by + pad), ImVec2(fx, by + bh - pad));
                    // (um reflexo correndo no ouro, da esquerda para a direita)
                    const float bw = 46 * k, sx = bx0 + (bx1 - bx0 + 2 * bw) * (fmodf(t, 2.4f) / 2.4f) - bw;
                    const ImU32 hi = st_col(0.38f, 255, 252, 236), no = st_col(0, 255, 252, 236);
                    c.d->PushClipRect(ImVec2(bx0 + pad, by + pad), ImVec2(fx, by + bh - pad), true);
                    c.d->AddRectFilledMultiColor(ImVec2(sx - bw, by), ImVec2(sx, by + bh), no, hi, hi, no);
                    c.d->AddRectFilledMultiColor(ImVec2(sx, by), ImVec2(sx + bw, by + bh), hi, no, no, hi);
                    c.d->PopClipRect();
                }
                const float split = std::max(fx, bx0 + pad);
                c.d->PushClipRect(ImVec2(bx0, by), ImVec2(split, by + bh), true);
                ui::text_mid_centre(c, c.f.strong, 15 * k, cx, by + bh * 0.5f, ui::kGoldInk, v.pct.c_str());
                c.d->PopClipRect();
                c.d->PushClipRect(ImVec2(split, by), ImVec2(bx1, by + bh), true);
                ui::text_mid_centre(c, c.f.strong, 15 * k, cx, by + bh * 0.5f, ui::kInk, v.pct.c_str());
                c.d->PopClipRect();
                under = by + bh;
            }
            const float px = 16.5f * k;
            ui::text(c, c.f.body, px, ImVec2(v.fraction >= 0 ? bx0 : cx - ui::size_of(c.f.body, px, v.left.c_str()).x * 0.5f, under + 12 * k),
                     ui::kSoft, v.left.c_str());
            if (!v.right.empty())
                ui::text(c, c.f.body, px, ImVec2(bx1 - ui::size_of(c.f.body, px, v.right.c_str()).x, under + 12 * k), ui::kSoft, v.right.c_str());
            if (!v.hint.empty()) ui::text_centre(c, c.f.body, 15.5f * k, ImVec2(cx, by + 92 * k), ui::kDim, v.hint.c_str());
        }
        if (bar_in < 1) c.d->AddRectFilled(ImVec2(0, top + lh + 6 * s), ImVec2(w, h), st_col(1 - bar_in, 0, 0, 0));
    }

    if (logo) {
        // o flare que revela a faixa: anda junto da borda revelada, e no fim abre e some
        if (t > kFl0 && t < kFl1 + kFlOut) {
            const float out = t < kFl1 ? 0 : (t - kFl1) / kFlOut;
            const float a = t < kFl1 ? st_clamp((t - kFl0) / 0.18f) : 1 - out;
            st_flare(c, ImVec2(x0 + lw * (kSvX0 + (1 - kSvX0) * reveal), top + lh * (kSvY0 + kSvY1) * 0.5f), lh * 0.34f * (1 + 0.6f * out), a);
        }
        // depois, brilhos discretos em pontos do logo, cada um no seu ritmo
        static const float kTw[][2] = {{0.10f, 0.31f}, {0.475f, 0.04f}, {0.92f, 0.45f}, {0.985f, 0.865f}, {0.19f, 0.42f}, {0.60f, 0.33f}};
        if (t > kStartupMin)
            for (int i = 0; i < 6; i++) {
                const float period = 3.4f + 0.9f * i, ph = fmodf(t + i * 1.7f, period);
                if (ph < 0.9f) st_flare(c, ImVec2(x0 + lw * kTw[i][0], top + lh * kTw[i][1]), lh * 0.06f, sinf(ph / 0.9f * 3.14159f) * 0.85f);
            }
    }
    if (fade > 0) c.d->AddRectFilled(ImVec2(0, 0), ImVec2(w, h), st_col(std::min(fade, 1.0f), 0, 0, 0));
}

} // namespace dp

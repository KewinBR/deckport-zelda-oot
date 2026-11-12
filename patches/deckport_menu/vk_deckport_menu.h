// (Deckport) O menu do port no visual do menu de Sistema do jogo: abas em cima (L1/R1), coluna de seções à esquerda,
// pergaminho com as opções à direita, dicas de botão no rodapé. Desenho aprovado pelo Kewin em 2026-11-10
// (projetos/zelda-oot/menu/menu-deckport.html no repo steam-deck). Ocupa a tela inteira, na resolução da janela.
// Desenhado com o Dear ImGui da v2.1.0 (fontes do próprio jogo: ui::Fonts). Incluído em vk_menu.cpp, dentro do
// namespace anônimo, antes do draw_menu: usa as opções do
// Hookshot (opts, rows, save, restart_state) e as do Deckport (opts.dp_*, linhas TAB_DECKPORT, gravadas no mesmo ini).
// As opções que mudam mods ou variáveis da abertura (texturas, grama, distância, sombras, idioma) valem ao reiniciar:
// "Aplicar e reiniciar" grava, deixa o arquivo deckport_reiniciar ao lado do ini e fecha o jogo; o rodar-zelda.sh vê o
// arquivo e abre o jogo de novo com as escolhas novas. RX_VK_DECKPORT_MENU=0 volta ao menu do Hookshot.
#pragma once

namespace dp {

bool on() {
    static int v = -1;
    if (v < 0) {
        const char* e = getenv("RX_VK_DECKPORT_MENU");
        v = !e || atoi(e) != 0;
    }
    return v != 0;
}

// ---------------------------------------------------------------- o modelo
struct Choice { const char* label; int v; };
enum Kind { K_VALUE, K_INFO, K_ACTION };
enum Action { A_NONE, A_RESTART, A_QUIT };
struct Item {
    const char* name;
    int* value;                      // (nullptr: informação ou ação)
    std::vector<Choice> ch;
    const char* help;
    Kind kind = K_VALUE;
    bool restart = false;            // (vale ao reiniciar)
    bool preset = false;             // (faz parte da predefinição: mexer vira Personalizado)
    const char* (*gain)(int idx) = nullptr;   // (ganho medido no Deck, para o valor escolhido)
    Action action = A_NONE;
    const char* info = nullptr;      // (K_INFO: o valor mostrado)
};
enum SecType { S_LIST, S_PRESET, S_MAP, S_ABOUT };
struct Section { const char* name; const char* title; SecType type; std::vector<Item> items; };
struct Tab { const char* name; std::vector<Section> secs; };

int lang = 0;   // (índice em kLangs: o language.txt ao lado do jogo)
int lang_start = 0;
struct Lang { const char* code; const char* name; };
const Lang kLangs[] = {{"pt-BR", "Português (Brasil)"}, {"en-US", "English (US)"}, {"en-GB", "English (UK)"},
                       {"es-419", "Español (Latinoamérica)"}, {"es", "Español (España)"}, {"fr", "Français"},
                       {"fr-CA", "Français (Canada)"}, {"de", "Deutsch"}, {"it", "Italiano"}, {"nl", "Nederlands"},
                       {"ru", "Russo"}, {"ja", "Japonês"}, {"ko", "Coreano"}, {"zh-Hans", "Chinês simplificado"}, {"zh-Hant", "Chinês tradicional"}};
// (os nomes em escrita não latina ficam em português: a fonte do menu só tem o alfabeto latino)
constexpr int kLangN = sizeof kLangs / sizeof kLangs[0];

// predefinições: resolução interna (valor do Hookshot), distância, grama, sombras, texturas
const char* const kPresets[] = {"Qualidade", "Equilibrado", "Desempenho", "Bateria", "Personalizado"};
const int kPresetVals[4][5] = {{1, 4, 2, 0, 0}, {2, 2, 0, 1, 1}, {3, 1, 0, 2, 1}, {4, 0, 0, 2, 1}};
int* preset_fields[5] = {&opts.resolution, &opts.dp_distance, &opts.dp_grass, &opts.dp_shadows, &opts.dp_textures};

const char* g_preset(int i) { return i == 1 ? "Medido no castelo: 19 a 20 fps, 6,5 GB livres" : nullptr; }
const char* g_shadows(int i) { return i == 1 ? "Medido no castelo: 300 MB a menos de memória de vídeo" : nullptr; }
const char* g_textures(int i) { return i == 1 ? "Medido: 6,2 GB a menos de texturas" : "Medido: 2,9 GB a menos que o original"; }
const char* g_distance(int i) { return i == 2 ? "Medido na Cidadela: 18,5 para 19,8 fps" : nullptr; }

std::vector<Tab> tabs;
std::vector<Choice> range(int lo, int hi, int step, const char* fmt) {
    std::vector<Choice> c;
    static std::deque<std::string> keep;   // (os textos ficam vivos enquanto o menu existir; deque: não muda de lugar)
    for (int v = lo; v <= hi; v += step) {
        char b[32];
        snprintf(b, sizeof b, fmt, v);
        keep.emplace_back(b);
    }
    size_t at = keep.size() - (size_t)((hi - lo) / step + 1);
    for (int v = lo; v <= hi; v += step) c.push_back({keep[at++].c_str(), v});
    return c;
}

void build() {
    if (!tabs.empty()) return;
    const std::vector<Choice> onoff = {{"Desligado", 0}, {"Ligado", 1}};
    const std::vector<Choice> noyes = {{"Não", 0}, {"Sim", 1}};
    std::vector<Choice> langs;
    for (int i = 0; i < kLangN; i++) langs.push_back({kLangs[i].name, i});

    Item preset{"Predefinição", &opts.dp_preset, {{"Qualidade", 0}, {"Equilibrado", 1}, {"Desempenho", 2}, {"Bateria", 3}},
                "Ajusta de uma vez a resolução e o mundo. Equilibrado é o padrão do port."};
    preset.gain = g_preset;
    Item res{"Resolução interna", &opts.resolution, {{"100% (800p)", 1}, {"75% (600p)", 2}, {"67% (536p)", 3}, {"50% (400p)", 4}},
             "Tamanho em que o mundo 3D é desenhado antes de ir para a tela. A interface continua nítida."};
    res.preset = true;
    Item sharp{"Nitidez", &opts.sharpness, range(0, 100, 10, "%d%%"),
               "Realce de contorno depois da ampliação. Use mais quando a resolução interna estiver baixa."};
    Item dist{"Distância de desenho", &opts.dp_distance, {{"Perto", 0}, {"Curta", 1}, {"Média", 2}, {"Longa", 3}, {"Original", 4}},
              "Até onde a vegetação e os detalhes aparecem. Quanto mais perto, mais leve."};
    dist.preset = dist.restart = true, dist.gain = g_distance;
    Item grass{"Densidade da grama", &opts.dp_grass, {{"Baixa (50%)", 0}, {"Média (75%)", 1}, {"Original", 2}},
               "Quantos tufos de grama o jogo planta por área. Hyrule Field é onde mais pesa."};
    grass.preset = grass.restart = true;
    Item shadows{"Sombras", &opts.dp_shadows, {{"Original", 0}, {"Média", 1}, {"Baixa", 2}},
                 "Tamanho do mapa de sombra do sol. Na Média as sombras ficam quase iguais e mais leves."};
    shadows.preset = shadows.restart = true, shadows.gain = g_shadows;
    Item tex{"Texturas", &opts.dp_textures, {{"Altas (1024)", 0}, {"Médias (512)", 1}},
             "Com Médias o castelo carregou e a Cidadela rodou inteira sem fechar. Altas pode faltar memória."};
    tex.preset = tex.restart = true, tex.gain = g_textures;
    Item fps{"Mostrar fps", &opts.show_fps, onoff, "Contador no canto superior direito. Vale na hora."};
    Item speed{"Velocidade do jogo", &opts.realtime, {{"Por quadro", 0}, {"Tempo real", 1}},
               "Abaixo de 30 fps: Tempo real mantém a velocidade do jogo; Por quadro deixa tudo mais lento junto."};
    Item text{"Idioma do jogo", &lang, langs, "Idioma dos textos, legendas e vozes do jogo."};
    text.restart = true;
    Item tspeed{"Velocidade do texto", &opts.text_speed, {{"Normal", 0}, {"2x", 1}, {"4x", 2}, {"Instantânea", 3}},
                "Quão rápido as falas aparecem na caixa de diálogo."};
    Item mic{"Microfone", &opts.mic, {{"Desligado", 0}, {"Padrão do sistema", 1}},
             "O que a ocarina ouve quando a opção de microfone do jogo está ligada."};
    Item screen{"Resolução da tela", nullptr, {}, "O Deck sempre mostra 1280 x 800, em 16:10, sem barras pretas.", K_INFO};
    screen.info = "1280 x 800";
    Item gyro{"Mirar com giroscópio", &opts.gyro, onoff,
              "Mexer o Deck move a mira do estilingue, do arco e do gancho, como no Switch."};
    Item gsx{"Sensibilidade horizontal", &opts.gyro_sens_x, range(50, 300, 25, "%d%%"), "Quanto a mira anda para os lados."};
    Item gsy{"Sensibilidade vertical", &opts.gyro_sens_y, range(50, 300, 25, "%d%%"), "Quanto a mira anda para cima e para baixo."};
    Item gix{"Inverter horizontal", &opts.gyro_inv_x, noyes, "Troca esquerda e direita da mira."};
    Item giy{"Inverter vertical", &opts.gyro_inv_y, noyes, "Troca cima e baixo da mira."};
    Item rum{"Vibração", &opts.rumble, {{"Desligada", 0}, {"25%", 25}, {"50%", 50}, {"75%", 75}, {"100%", 100}, {"125%", 125}, {"150%", 150}},
             "Força da vibração, em relação à do jogo."};
    Item dz{"Zona morta do analógico", &opts.stick_dead_zone, {{"Padrão", 0}, {"5%", 1}, {"10%", 2}, {"15%", 3}, {"20%", 4}, {"30%", 5}},
            "Quanto o analógico precisa sair do centro para contar. Aumente se o Link andar sozinho."};
    Item cx{"Inverter câmera horizontal", &opts.invert_cam_x, noyes, "Troca esquerda e direita ao girar a câmera."};
    Item cy{"Inverter câmera vertical", &opts.invert_cam_y, noyes, "Troca cima e baixo ao girar a câmera."};
    Item prompts{"Ícones de botão", &opts.prompts, {{"Automático", 0}, {"Steam Deck", 5}, {"Switch", 1}, {"Xbox", 2}, {"PlayStation 5", 4}},
                 "Os ícones de botão que o jogo mostra nos textos e menus."};
    prompts.restart = true;
    Item restart{"Reiniciar o jogo", nullptr, {}, "Fecha e abre o jogo de novo. Salve antes: aperte A duas vezes.", K_ACTION};
    restart.action = A_RESTART;
    Item quit{"Sair do jogo", nullptr, {}, "Volta para o Steam. Salve antes: aperte A duas vezes.", K_ACTION};
    quit.action = A_QUIT;

    tabs = {
        {"Gráficos", {{"Predefinição", "Predefinição", S_PRESET, {preset}},
                      {"Imagem", "Imagem", S_LIST, {screen, res, sharp}},
                      {"Mundo", "Mundo", S_LIST, {dist, grass, shadows, tex}},
                      {"Quadros", "Quadros por segundo", S_LIST, {fps, speed}}}},
        {"Jogo", {{"Idioma", "Idioma", S_LIST, {text, tspeed}}, {"Som", "Som", S_LIST, {mic}}}},
        {"Controle", {{"Botões", "Botões no Deck", S_MAP, {}},
                      {"Giroscópio", "Giroscópio", S_LIST, {gyro, gsx, gsy, gix, giy}},
                      {"Ajustes", "Ajustes", S_LIST, {rum, dz, cx, cy, prompts}}}},
        {"Sobre", {{"Deckport", "Sobre o port", S_ABOUT, {}}, {"Sistema", "Sistema", S_LIST, {restart, quit}}}},
    };
}

// ---------------------------------------------------------------- o estado
int tab = 0, zone = 0;          // (zone 0: a coluna das seções; 1: as linhas do pergaminho)
int sec[4] = {}, row[4] = {};
const Item* armed = nullptr;    // (Reiniciar ou Sair esperando a segunda vez)
bool msg_restarting = false;
int start_vals[8];              // (o que esta abertura usa: distância, grama, sombras, texturas, ícones)
int* restart_fields[] = {&opts.dp_distance, &opts.dp_grass, &opts.dp_shadows, &opts.dp_textures, &opts.prompts};
constexpr int kRestartFields = 5;

std::string game_dir() {
    const std::string p = ini_path();
    return p.substr(0, p.find_last_of("\\/") + 1);
}
void lang_read() {
    lang = 0;
    if (FILE* f = fopen((game_dir() + "language.txt").c_str(), "r")) {
        char line[128];
        while (fgets(line, sizeof line, f)) {
            char* s = line;
            while (*s == ' ' || *s == '\t') s++;
            if (*s == '#' || *s == '\n' || *s == '\r' || !*s) continue;
            size_t n = strcspn(s, " \t\r\n");
            for (int i = 0; i < kLangN; i++)
                if (strlen(kLangs[i].code) == n && !strncmp(s, kLangs[i].code, n)) lang = i;
            break;
        }
        fclose(f);
    }
}
void lang_write() {
    const std::string path = game_dir() + "language.txt";
    std::string out;
    bool done = false;
    if (FILE* f = fopen(path.c_str(), "r")) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            const char* s = line;
            while (*s == ' ' || *s == '\t') s++;
            const bool code = *s && *s != '#' && *s != '\n' && *s != '\r';
            if (code && !done) out += std::string(kLangs[lang].code) + "\n", done = true;
            else if (!code) out += line;
        }
        fclose(f);
    }
    if (!done) out = std::string("# The game's language.\n\n") + kLangs[lang].code + "\n";
    if (FILE* f = fopen(path.c_str(), "w")) fputs(out.c_str(), f), fclose(f);
}
bool started = false;
void start() {
    if (started) return;
    started = true;
    build();
    lang_read();
    lang_start = lang;
    for (int i = 0; i < kRestartFields; i++) start_vals[i] = *restart_fields[i];
}
std::vector<std::string> pending_names() {
    std::vector<std::string> v;
    static const char* names[] = {"Distância", "Grama", "Sombras", "Texturas", "Ícones de botão"};
    for (int i = 0; i < kRestartFields; i++)
        if (*restart_fields[i] != start_vals[i]) v.push_back(names[i]);
    if (lang != lang_start) v.push_back("Idioma");
    return v;
}

int choice_index(const Item& it) {
    if (!it.value || it.ch.empty()) return 0;
    int best = 0, dist = 1 << 30;
    for (size_t i = 0; i < it.ch.size(); i++) {
        const int d = std::abs(it.ch[i].v - *it.value);
        if (d < dist) dist = d, best = (int)i;
    }
    return best;
}
bool fixed(const Item& it) { return it.kind != K_VALUE || (it.value == &opts.resolution && row_fixed(&opts.resolution)); }
void preset_apply(int p) {
    if (p < 0 || p > 3) return;
    for (int i = 0; i < 5; i++) *preset_fields[i] = kPresetVals[p][i];
}
void preset_check() {
    const int p = opts.dp_preset;
    if (p < 0 || p > 3) return;
    for (int i = 0; i < 5; i++)
        if (*preset_fields[i] != kPresetVals[p][i]) { opts.dp_preset = 4; return; }
}
void quiet_restart_ask() {   // (o Hookshot não pergunta ao fechar: aqui é o Y que aplica)
    int now[mr::kMax];
    restart_values(now);
    restart_state.note(now);
    restart_state.choose_later(now);
}
void set(const Item& it, int dir) {
    if (fixed(it) || it.ch.empty()) return;
    const int i = choice_index(it), n = (int)it.ch.size();
    const int ni = std::min(std::max(i + dir, 0), n - 1);
    if (ni == i && *it.value == it.ch[i].v) return;
    *it.value = it.ch[ni].v;
    if (it.value == &opts.dp_preset) preset_apply(*it.value);
    else if (it.preset) preset_check();
    if (it.value == &lang) lang_write();
    if (it.value == &opts.mic && can_mic()) mic_chosen();
    quiet_restart_ask();
    save();
}

// ---------------------------------------------------------------- o desenho
uint32_t W = 1280, H = 800;
float K = 1.0f;
int S(float v) { return (int)lroundf(v * K); }
inline uint32_t rgb(int r, int g, int b) { return (uint32_t)r << 16 | (uint32_t)g << 8 | (uint32_t)b; }
inline uint32_t mix(uint32_t a, uint32_t b, float t) {
    t = std::min(std::max(t, 0.0f), 1.0f);
    auto c = [&](int sh) { return (uint32_t)lroundf(((a >> sh) & 255) * (1 - t) + ((b >> sh) & 255) * t) << sh; };
    return c(16) | c(8) | c(0);
}
ImDrawList* DL = nullptr;
ui::Fonts FN{};
inline ImU32 col(uint32_t c, float a = 1) {
    return IM_COL32((c >> 16) & 255, (c >> 8) & 255, c & 255, (int)lroundf(std::min(std::max(a, 0.0f), 1.0f) * 255));
}
void box(int x, int y, int w, int h, uint32_t c, float a = 1) {
    if (w > 0 && h > 0) DL->AddRectFilled(ImVec2((float)x, (float)y), ImVec2((float)(x + w), (float)(y + h)), col(c, a));
}
void vgrad(int x, int y, int w, int h, uint32_t c0, uint32_t c1) {
    const ImU32 a = col(c0), b = col(c1);
    DL->AddRectFilledMultiColor(ImVec2((float)x, (float)y), ImVec2((float)(x + w), (float)(y + h)), a, a, b, b);
}
void hfade(int x, int y, int w, int h, uint32_t c, float a0, float a1) {   // (faixa que esmaece da esquerda para a direita)
    const ImU32 l = col(c, a0), r = col(c, a1);
    DL->AddRectFilledMultiColor(ImVec2((float)x, (float)y), ImVec2((float)(x + w), (float)(y + h)), l, r, r, l);
}
void vfade(int x, int y, int w, int h, uint32_t c, float a0, float a1) {   // (de cima para baixo)
    const ImU32 t = col(c, a0), b = col(c, a1);
    DL->AddRectFilledMultiColor(ImVec2((float)x, (float)y), ImVec2((float)(x + w), (float)(y + h)), t, t, b, b);
}
void frame(int x, int y, int w, int h, uint32_t c, int t = 1, float a = 1) {
    box(x, y, w, t, c, a), box(x, y + h - t, w, t, c, a), box(x, y + t, t, h - 2 * t, c, a), box(x + w - t, y + t, t, h - 2 * t, c, a);
}
void glow(int x, int y, int w, int h) {   // (o contorno branco com brilho do item em foco, como no jogo)
    for (int i = 6; i >= 1; i--) frame(x - S(3) - i, y - S(3) - i, w + 2 * (S(3) + i), h + 2 * (S(3) + i), 0xffffff, 1, 0.07f * (7 - i));
    frame(x - S(3), y - S(3), w + 2 * S(3), h + 2 * S(3), 0xffffff, std::max(2, S(3)));
}
void disc(float cx, float cy, float r, uint32_t c, float a = 1) { DL->AddCircleFilled(ImVec2(cx, cy), r, col(c, a), 24); }
void rrect(int x, int y, int w, int h, int r, uint32_t c, float a = 1) {
    DL->AddRectFilled(ImVec2((float)x, (float)y), ImVec2((float)(x + w), (float)(y + h)), col(c, a), (float)r);
}
ImFont* face(bool bold) { return bold ? FN.strong : FN.body; }
int text_w(const char* s, float px, bool bold) { return (int)ceilf(ui::size_of(face(bold), (float)S(px), s).x); }
// (texto com o topo em y; align: 0 esquerda, 1 centro, 2 direita; sombra opcional)
void text(int x, int y, const char* s, float px, bool bold, uint32_t c, int align = 0, bool shadow = false) {
    const float size = (float)S(px);
    const float w = align ? ui::size_of(face(bold), size, s).x : 0;
    const float tx = align == 1 ? x - w * 0.5f : align == 2 ? x - w : (float)x;
    if (shadow) DL->AddText(face(bold), size, ImVec2(tx, (float)y + std::max(1, S(1))), col(0, 0.75f), s);
    DL->AddText(face(bold), size, ImVec2(tx, (float)y), col(c), s);
}
int wrap(int x, int y, int width, const char* s, float px, bool bold, uint32_t c, float lh = 1.35f) {
    const float size = (float)S(px);
    DL->AddText(face(bold), size, ImVec2((float)x, (float)y), col(c), s, nullptr, (float)width);
    return (int)ceilf(face(bold)->CalcTextSizeA(size, FLT_MAX, (float)width, s).y);
}
// glifo do Deck: círculo claro com a letra (A, B, X, Y, L, R, ≡) ou retângulo (L1, R1, L2, L4...)
int glyph(int x, int cy, const char* t, bool rect = false) {
    const uint32_t bg = rgb(243, 238, 228), fg = rgb(43, 33, 22);
    if (!rect) {
        const float r = K * 12;
        disc(x + r, (float)cy, r, bg);
        if (!strcmp(t, "=")) {   // (o botão Menu do Deck: três traços)
            for (int i = -1; i <= 1; i++) box((int)(x + r) - S(6), cy + i * S(4) - std::max(1, S(1)), S(12), std::max(2, S(2)), fg);
        } else {
            text((int)(x + r), cy - S(9), t, 14, true, fg, 1);
        }
        return (int)(2 * r);
    }
    const int w = text_w(t, 12, true) + S(10), h = S(20);
    rrect(x, cy - h / 2, w, h, S(4), bg);
    text(x + w / 2, cy - S(8), t, 12, true, fg, 1);
    return w;
}

// as áreas clicáveis desta pintura (o toque e o mouse: hit)
struct Rect { int x, y, w, h; };
Rect r_tabs[4], r_secs[8], r_rows[12], r_y, r_b, r_a;
int n_secs = 0, n_rows = 0;
bool in(const Rect& r, int x, int y) { return r.w > 0 && x >= r.x && y >= r.y && x < r.x + r.w && y < r.y + r.h; }

const uint32_t C_NIGHT = rgb(10, 6, 4), C_IVORY = rgb(246, 239, 224), C_INK = rgb(59, 40, 16), C_INK2 = rgb(90, 63, 23),
               C_GOLD = rgb(216, 166, 50), C_CREAM = rgb(240, 220, 174);

void paint_bar() {
    // faixa de couro com a borda de baixo recortada (colunas de 4 px)
    for (int x = 0; x < (int)W; x += 4) {
        const float fx = (float)x / K;
        const float edge = 74 + 6 * sinf(fx * 0.011f) + 3 * sinf(fx * 0.037f + 1.3f) + (fx < 90 || fx > 1190 ? 10 : 0);
        const int e = S(edge);
        vgrad(x, 0, 4, e, rgb(138, 108, 67), rgb(109, 82, 50));
        box(x, e, 4, S(3), rgb(40, 26, 12), 0.8f);
    }
    // espirais nas pontas
    for (int side = 0; side < 2; side++) {
        const float cx = side ? W - K * 22 : K * 22, cy = K * 92;
        for (float t = 0; t < 10.5f; t += 0.02f) {
            const float r = K * (2 + t * 1.1f);
            disc(cx + (side ? -1 : 1) * r * cosf(t), cy + r * sinf(t), K * 1.3f, rgb(200, 169, 110));
        }
    }
    text(S(30), S(14), "Deckport", 24, true, C_IVORY, 0, true);
    text(S(31), S(42), "STEAM DECK", 11, true, C_CREAM);
    // abas
    const int tw = S(150), total = tw * (int)tabs.size(), x0 = ((int)W - total) / 2;
    glyph(x0 - S(46), S(33), "L1", true);
    glyph(x0 + total + S(16), S(33), "R1", true);
    for (int i = 0; i < (int)tabs.size(); i++) {
        const int x = x0 + i * tw;
        if (i == tab) vgrad(x, 0, tw, S(66), rgb(95, 65, 37), rgb(75, 49, 26)), box(x, S(64), tw, S(2), rgb(42, 26, 12));
        text(x + tw / 2, S(19), tabs[i].name, 21, true, C_IVORY, 1, true);
        r_tabs[i] = {x, 0, tw, S(66)};
    }
    // canto direito: a predefinição em uso
    text((int)W - S(28), S(16), kPresets[std::min(std::max(opts.dp_preset, 0), 4)], 19, true, C_IVORY, 2, true);
    text((int)W - S(28), S(42), "predefinição", 13, false, C_CREAM, 2);
}

void paint_column() {
    const Tab& t = tabs[tab];
    const int x = S(38), y = S(122), w = S(318), h = (int)H - S(122) - S(74);
    vgrad(x, y, w, h, rgb(51, 38, 26), rgb(36, 26, 18));
    frame(x, y, w, h, rgb(74, 55, 36));
    frame(x + S(10), y + S(10), w - S(20), h - S(20), 0xffffff, 1, 0.06f);
    n_secs = (int)t.secs.size();
    int by = S(160);
    for (int i = 0; i < n_secs; i++) {
        if (i == 1 && n_secs > 2) {   // (ornamento entre o primeiro e os outros, como Load / Options no jogo)
            const int oy = by - S(2);
            hfade(S(90), oy, S(70), std::max(1, S(1)), rgb(140, 115, 80), 0, 1);
            hfade(S(240), oy, S(70), std::max(1, S(1)), rgb(140, 115, 80), 1, 0);
            text(S(200), oy - S(11), "~", 18, true, rgb(140, 115, 80), 1);
            by += S(20);
        }
        const int bx = S(84), bw = S(226), bh = S(48);
        const bool open = i == sec[tab];
        vgrad(bx, by, bw, bh, open ? rgb(154, 118, 70) : rgb(128, 97, 58), open ? rgb(130, 99, 58) : rgb(108, 81, 48));
        frame(bx, by, bw, bh, rgb(42, 28, 14));
        frame(bx + S(5), by + S(5), bw - S(10), bh - S(10), rgb(168, 139, 90), 1, 0.9f);
        text(bx + bw / 2, by + S(11), t.secs[i].name, 21, false, C_IVORY, 1, true);
        if (zone == 0 && open) glow(bx, by, bw, bh);
        r_secs[i] = {bx, by, bw, bh};
        by += bh + S(16);
    }
}

void paint_parchment_bg(int x, int y, int w, int h) {
    box(x, y, w, h, rgb(184, 150, 92));
    const uint32_t dark = rgb(120, 88, 42);
    const int bw = w / 3, bh = h / 3;
    hfade(x, y, bw, h, dark, 0.75f, 0), hfade(x + w - bw, y, bw, h, dark, 0, 0.75f);
    vfade(x, y, w, bh, dark, 0.6f, 0), vfade(x, y + h - bh, w, bh, dark, 0, 0.7f);
    for (int k = 0; k < h; k += 7) box(x, y + k, w, 1, 0xffffff, 0.025f);   // (fibras do papel)
    frame(x, y, w, h, rgb(75, 50, 20));
}

void paint_title(int cx, int y, const char* s) {
    text(cx, y, s, 30, true, rgb(58, 39, 9), 1);
    const int tw = text_w(s, 30, true);
    for (int side = -1; side <= 1; side += 2) {   // (o ornamento de cada lado: traço e voluta)
        const int ox = cx + side * (tw / 2 + S(14));
        const int lx = side < 0 ? ox - S(40) : ox;
        box(lx, y + S(19), S(26), std::max(2, S(2)), rgb(58, 39, 9));
        const float vx = side < 0 ? ox - S(40) - S(2) : ox + S(30);
        for (float t = 0; t < 8.0f; t += 0.03f) {
            const float r = K * (1.5f + t * 0.7f);
            disc(vx + side * r * cosf(t), y + S(19) + r * sinf(t), K * 1.0f, rgb(58, 39, 9));
        }
    }
}

void paint_row(int x, int y, int w, const Item& it, bool focus) {
    const int h = S(46);
    if (focus) hfade(x, y, w, h, rgb(127, 97, 47), 1, 0.95f);
    else hfade(x, y, w, h, rgb(110, 84, 40), 0.85f, 0.0f);
    text(x + S(18), y + S(11), it.name, 19, false, C_IVORY, 0, true);
    int nx = x + S(18) + text_w(it.name, 19, false) + S(10);
    if (it.restart) {   // (selo "ao reiniciar")
        const int bw = text_w("ao reiniciar", 12, true) + S(10);
        box(nx, y + S(14), bw, S(18), rgb(230, 196, 109));
        text(nx + bw / 2, y + S(15), "ao reiniciar", 12, true, rgb(43, 28, 5), 1);
    }
    const uint32_t ink = focus ? C_IVORY : C_INK;
    const int right = x + w - S(14);
    if (it.kind == K_ACTION) {
        const bool arm = armed == &it;
        text(right, y + S(11), arm ? "Aperte A de novo" : "A", 19, true, arm ? C_GOLD : ink, 2);
        return;
    }
    const char* val = it.kind == K_INFO ? it.info : it.ch.empty() ? "" : it.ch[choice_index(it)].label;
    if (it.value == &opts.dp_preset && opts.dp_preset == 4) val = "Personalizado";
    const int vw = S(210), vx = right - vw;
    text(vx + vw / 2, y + S(11), val, 19, true, ink, 1);
    if (!fixed(it)) {   // (setas)
        const float a = focus ? 1.0f : 0.35f;
        const int ay = y + h / 2;
        for (int i = 0; i < S(10); i++) {
            box(vx + i, ay - i * 7 / 10, 1, 2 * (i * 7 / 10) + 1, ink, a);
            box(right - i, ay - i * 7 / 10, 1, 2 * (i * 7 / 10) + 1, ink, a);
        }
    }
}

void paint_hint(int x, int y, int w, const Item* it) {
    box(x, y, w, std::max(1, S(1)), C_INK2, 0.35f);
    if (!it) return;
    wrap(x, y + S(14), w - S(260), it->help, 17, false, rgb(58, 39, 9));
    if (it->gain && it->value) {
        const char* g = it->gain(choice_index(*it));
        if (g) {
            const int gw = S(230), gx = x + w - gw;
            box(gx, y + S(14), gw, S(58), rgb(79, 58, 28));
            text(gx + gw - S(10), y + S(20), "GANHO MEDIDO NO DECK", 11, true, rgb(233, 214, 166), 2);
            wrap(gx + S(10), y + S(38), gw - S(20), g, 14, true, C_IVORY, 1.2f);
        }
    }
}

void paint_preset_table(int x, int y, int w) {
    static const char* labels[5] = {"Resolução interna", "Distância", "Grama", "Sombras", "Texturas"};
    static const char* vals[5][4] = {{"100%", "75%", "67%", "50%"}, {"Original", "Média", "Curta", "Perto"},
                                     {"Original", "Baixa", "Baixa", "Baixa"}, {"Original", "Média", "Baixa", "Baixa"},
                                     {"Altas", "Médias", "Médias", "Médias"}};
    const int c0 = S(200), cw = (w - c0) / 4, rh = S(30);
    const int act = opts.dp_preset;
    if (act >= 0 && act < 4) box(x + c0 + act * cw, y, cw, rh * 6, 0xffffff, 0.16f);
    for (int c = 0; c < 4; c++) text(x + c0 + c * cw + cw / 2, y + S(6), kPresets[c], 15, true, rgb(58, 39, 9), 1);
    for (int r = 0; r < 5; r++) {
        const int ry = y + rh * (r + 1);
        box(x, ry, w, std::max(1, S(1)), C_INK2, 0.2f);
        text(x, ry + S(6), labels[r], 16, true, rgb(58, 39, 9));
        for (int c = 0; c < 4; c++) text(x + c0 + c * cw + cw / 2, ry + S(6), vals[r][c], 16, c == act, rgb(58, 39, 9), 1);
    }
}

void paint_map(int x, int y, int w) {
    // o Deck, simplificado, no centro
    const int dw = S(380), dh = S(140), dx = x + (w - dw) / 2, dy = y + S(30);
    rrect(dx + S(30), dy - S(14), S(56), S(22), S(8), rgb(42, 32, 22));
    rrect(dx + dw - S(86), dy - S(14), S(56), S(22), S(8), rgb(42, 32, 22));
    rrect(dx, dy, dw, dh, S(52), rgb(30, 23, 18));
    rrect(dx + S(108), dy + S(12), S(164), S(104), S(6), rgb(13, 10, 8));
    box(dx + S(116), dy + S(20), S(148), S(88), rgb(42, 32, 22));
    disc(dx + K * 52, dy + K * 38, K * 15, rgb(43, 33, 22)), disc(dx + K * 52, dy + K * 38, K * 11, rgb(70, 55, 38));
    box(dx + S(42), dy + S(66), S(10), S(30), rgb(70, 55, 38)), box(dx + S(32), dy + S(76), S(30), S(10), rgb(70, 55, 38));
    disc(dx + dw - K * 52, dy + K * 98, K * 15, rgb(43, 33, 22)), disc(dx + dw - K * 52, dy + K * 98, K * 11, rgb(70, 55, 38));
    const float bx = dx + dw - K * 52, by = dy + K * 46;
    const char* f[4] = {"Y", "X", "B", "A"};
    const float off[4][2] = {{0, -16}, {-16, 0}, {16, 0}, {0, 16}};
    for (int i = 0; i < 4; i++) {
        disc(bx + K * off[i][0], by + K * off[i][1], K * 8.5f, rgb(43, 33, 22));
        text((int)(bx + K * off[i][0]), (int)(by + K * off[i][1]) - S(7), f[i], 11, true, rgb(233, 220, 192), 1);
    }
    // rótulos dos dois lados, como os do "Basic Controls" do jogo
    auto lab = [&](bool right, int ly, const char* g, bool rect, const char* t) {
        const int lw = S(176), lx = right ? x + w - lw : x;
        if (right) hfade(lx, ly, lw, S(32), rgb(110, 84, 40), 0.0f, 0.85f);
        else hfade(lx, ly, lw, S(32), rgb(110, 84, 40), 0.85f, 0.0f);
        if (right) {
            const int gw = glyph(lx + S(10), ly + S(16), g, rect);
            text(lx + S(18) + gw, ly + S(5), t, 17, false, C_IVORY, 0, true);
        } else {
            const int tw = text_w(t, 17, false);
            text(lx + S(10), ly + S(5), t, 17, false, C_IVORY, 0, true);
            glyph(lx + S(18) + tw, ly + S(16), g, rect);
        }
    };
    lab(false, y + S(20), "L2", true, "Mirar");
    lab(false, y + S(64), "L", false, "Mover");
    lab(false, y + S(108), "R2", true, "Usar o item");
    lab(false, y + S(152), "L1", true, "Trocar de aba");
    lab(true, y + S(20), "=", false, "Abrir o menu");
    lab(true, y + S(64), "B", false, "Ações e correr");
    lab(true, y + S(108), "A", false, "Guardar");
    lab(true, y + S(152), "Y", false, "Pular");
    lab(true, y + S(196), "R", false, "Câmera");
}

void paint_about(int x, int y, int w) {
    const int col = w / 2 - S(12);
    text(x, y + S(10), "Deckport", 40, true, rgb(58, 39, 9));
    text(x, y + S(58), "STEAMDECK VERSION", 14, true, C_INK2);
    wrap(x, y + S(96), col, "The Legend of Zelda: Ocarina of Time, versão de Switch 2, rodando nativo no Steam Deck.", 17, false, rgb(58, 39, 9));
    wrap(x, y + S(170), col, "Motor Deckport 2.1.0, feito a partir do Hookshot.", 17, false, rgb(58, 39, 9));
    const int rx = x + w / 2 + S(12);
    int ry = y + S(10);
    auto block = [&](const char* h, const char* body) {
        text(rx, ry, h, 14, true, C_INK2);
        ry += S(22);
        ry += wrap(rx, ry, col, body, 17, false, rgb(58, 39, 9)) + S(14);
    };
    block("PORT PARA STEAM DECK", "Kewin Lima");
    block("MOTOR BASE", "Hookshot (NotRexed e colaboradores), licença GPL-3.0. O código do motor e das nossas mudanças acompanha o port.");
    block("JOGO", "Nintendo. Você precisa da sua própria cópia do jogo.");
}

void paint_footer() {
    const int y = (int)H - S(58), cy = y + S(29);
    hfade((int)(W * 0.35f), y, (int)W - (int)(W * 0.35f), (int)H - y, 0, 0, 0.6f);
    int x = (int)W - S(34);
    auto hint = [&](const char* label, const char* g, bool rect, uint32_t c, Rect* r) {
        const int gw = rect ? text_w(g, 12, true) + S(10) : S(24);
        x -= gw;
        glyph(x, cy, g, rect);
        const int lw = text_w(label, 20, false);
        x -= S(9) + lw;
        text(x, cy - S(13), label, 20, false, c, 0, true);
        if (r) *r = {x, y, lw + S(9) + gw, S(58)};
        x -= S(28);
    };
    r_y = r_b = r_a = {0, 0, 0, 0};
    hint(zone == 1 ? "Voltar" : "Fechar", "B", false, C_IVORY, &r_b);
    const Section& s = tabs[tab].secs[sec[tab]];
    if (zone == 0 && !s.items.empty()) hint("Selecionar", "A", false, C_IVORY, &r_a);
    if (zone == 1) hint("Mudar", "<  >", true, C_IVORY, nullptr);
    if (!pending_names().empty()) hint("Aplicar e reiniciar", "Y", false, rgb(246, 215, 125), &r_y);
}

void paint(ui::Ctx& c) {
    DL = c.d, FN = c.f, W = (uint32_t)c.w, H = (uint32_t)c.h, K = std::min(c.w / 1280.0f, c.h / 800.0f);
    const uint32_t w = W, h = H;
    start();
    box(0, 0, (int)w, (int)h, C_NIGHT);
    for (int i = 30; i >= 1; i--) disc(w * 0.7f, h * 0.55f, h * 0.025f * i, rgb(52, 32, 16), 0.035f);
    paint_bar();
    paint_column();
    const Tab& t = tabs[tab];
    const Section& s = t.secs[sec[tab]];
    const int px = S(398), py = S(150), pw = S(842), ph = (int)h - S(150) - S(112);
    paint_parchment_bg(px, py, pw, ph);
    paint_title(px + pw / 2, py + S(22), s.title);
    const int cx = px + S(40), cy = py + S(84), cw = pw - S(80);
    n_rows = 0;
    if (s.type == S_MAP) paint_map(cx, cy, cw);
    else if (s.type == S_ABOUT) paint_about(cx, cy, cw);
    else {
        int ry = cy;
        for (size_t i = 0; i < s.items.size(); i++) {
            paint_row(cx, ry, cw, s.items[i], zone == 1 && (int)i == row[tab]);
            r_rows[i] = {cx, ry, cw, S(46)};
            ry += S(52);
        }
        n_rows = (int)s.items.size();
        if (s.type == S_PRESET) paint_preset_table(cx, ry + S(6), cw);
        const Item* hi = s.items.empty() ? nullptr : &s.items[zone == 1 ? row[tab] : 0];
        paint_hint(cx, py + ph - S(118), cw, hi);
    }
    if (s.type == S_MAP)
        paint_hint(cx, py + ph - S(118), cw, nullptr),
        wrap(cx, py + ph - S(104), cw, "Mesmas posições do controle do Switch: o botão da direita faz as ações, o de baixo guarda e o de cima pula. Este menu abre com View e Menu juntos.", 17, false, rgb(58, 39, 9));
    // faixa do reinício pendente
    const auto pend = pending_names();
    if (!pend.empty()) {
        std::string l = pend.size() == 1 ? "1 opção vale ao reiniciar o jogo: " : std::to_string(pend.size()) + " opções valem ao reiniciar o jogo: ";
        for (size_t i = 0; i < pend.size(); i++) l += (i ? ", " : "") + pend[i];
        text(px + pw / 2, py + ph + S(10), l.c_str(), 16, false, rgb(246, 215, 125), 1);
    }
    paint_footer();
    if (msg_restarting) {
        const int mw = S(520), mh = S(110), mx = ((int)w - mw) / 2, my = ((int)h - mh) / 2;
        box(mx, my, mw, mh, rgb(27, 18, 11), 0.96f);
        frame(mx, my, mw, mh, rgb(179, 148, 97));
        text(mx + mw / 2, my + S(26), "Salvando e reiniciando o jogo", 21, true, C_IVORY, 1);
        text(mx + mw / 2, my + S(62), "Você volta para o ponto em que salvou por último.", 15, false, rgb(185, 178, 162), 1);
    }
}

// ---------------------------------------------------------------- a entrada
void apply_restart() {
    msg_restarting = true;
    save();
    pipeline_cache_save(true);
    if (FILE* f = fopen((game_dir() + "deckport_reiniciar").c_str(), "w")) fputs("1\n", f), fclose(f);
    logf("menu (Deckport): aplicar e reiniciar");
    if (const HWND window = app_window()) PostMessageA(window, WM_CLOSE, 0, 0);
}

// press: as teclas do menu_tick (1 cima, 2 baixo, 3 esquerda, 4 direita, 5 B/Esc, 7 A/Enter); y: o Y do controle
bool tick(bool* press, bool tab_left, bool tab_right, bool y, bool mouse, int mx, int my, uint32_t clicks, bool mine) {
    start();
    bool changed = false;
    // toque e mouse: o que está sob o dedo (as áreas da última pintura)
    if (mouse && (clicks & HOS_MOUSE_LEFT)) {
        for (int i = 0; i < (int)tabs.size(); i++)
            if (in(r_tabs[i], mx, my) && i != tab) tab = i, zone = 0, changed = true;
        for (int i = 0; i < n_secs; i++)
            if (in(r_secs[i], mx, my)) sec[tab] = i, row[tab] = 0, zone = 0, changed = true;
        for (int i = 0; i < n_rows; i++)
            if (in(r_rows[i], mx, my)) {
                const bool again = zone == 1 && row[tab] == i;
                zone = 1, row[tab] = i, changed = true;
                if (again) {
                    const Item& it = tabs[tab].secs[sec[tab]].items[i];
                    if (it.kind == K_ACTION) press[7] = true;
                    else press[mx < r_rows[i].x + r_rows[i].w * 3 / 4 ? 3 : 4] = true;
                }
            }
        if (in(r_y, mx, my)) y = true;
        if (in(r_b, mx, my)) press[5] = true;
        if (in(r_a, mx, my)) press[7] = true;
    }
    if (clicks & HOS_MOUSE_RIGHT) press[5] = true;
    if (tab_left || tab_right) {
        tab = (tab + (tab_right ? 1 : (int)tabs.size() - 1)) % (int)tabs.size();
        zone = 0, armed = nullptr, changed = true;
    }
    const Section& s = tabs[tab].secs[sec[tab]];
    if (y && !pending_names().empty() && mine) { apply_restart(); return true; }
    if (zone == 0) {
        if (press[1] || press[2]) {
            const int n = (int)tabs[tab].secs.size();
            sec[tab] = (sec[tab] + (press[1] ? n - 1 : 1)) % n, row[tab] = 0, changed = true;
        } else if ((press[7] || press[4]) && !s.items.empty()) {
            zone = 1, row[tab] = 0, changed = true;
        } else if (press[5]) {
            open_now = false, armed = nullptr, changed = true;
        }
    } else if (s.items.empty()) {
        zone = 0, changed = true;
    } else {
        const int n = (int)s.items.size();
        const Item& it = s.items[std::min(row[tab], n - 1)];
        if (press[1] || press[2]) row[tab] = (row[tab] + (press[1] ? n - 1 : 1)) % n, armed = nullptr, changed = true;
        else if (press[5]) zone = 0, armed = nullptr, changed = true;
        else if (it.kind == K_ACTION && press[7] && mine) {
            if (armed != &it) armed = &it, changed = true;
            else if (it.action == A_RESTART) {
                armed = nullptr, msg_restarting = true, changed = true;
                save();
                pipeline_cache_save(true);
                logf("menu (Deckport): reiniciar");
                if (const HWND window = app_window()) PostMessageA(window, WM_APP + 9, 0, 0);
            } else if (it.action == A_QUIT) {
                armed = nullptr, save();
                pipeline_cache_save(true);
                if (const HWND window = app_window()) PostMessageA(window, WM_CLOSE, 0, 0);
            }
        } else if (press[3] || press[4] || press[7]) {
            set(it, press[3] ? -1 : 1), changed = true;
        }
    }
    return changed;
}

} // namespace dp

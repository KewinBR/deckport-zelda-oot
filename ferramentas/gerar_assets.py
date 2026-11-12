#!/usr/bin/env python3
"""Gera as artes do port: fundos do instalador, cartões, artes da Steam e o logo da tela de abertura, a partir do
logo do port (arte/logo.png) e de fundos desenhados aqui. As fontes são de licença aberta (Cinzel Decorative e Barlow).

    python ferramentas/gerar_assets.py        (precisa do Pillow; roda no PC, não no Deck)
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "instalador" / "fontes"
SAIDA = RAIZ / "instalador" / "assets"
STEAM = SAIDA / "steam"
ARTE = RAIZ / "arte"
W, H = 1280, 800
OURO = (226, 184, 96)
OURO_CLARO = (250, 226, 160)
OURO_ESCURO = (150, 110, 44)


def fonte(nome, px):
    return ImageFont.truetype(str(FONTES / nome), px)


def fundo(w, h, semente=7, escurece=0.0, brilho=(0.72, 0.42)):
    """Verde-escuro para preto, com um clarão dourado e pontos de luz. Nada do jogo."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    cx, cy = w * brilho[0], h * brilho[1]
    raio = max(w, h) * 0.75
    for y in range(h):
        for x in range(w):
            d = min(1.0, math.hypot(x - cx, y - cy) / raio)
            k = (1 - d) ** 2.2
            v = y / h
            r = 6 + 40 * k + 4 * (1 - v)
            g = 14 + 52 * k + 10 * (1 - v)
            b = 12 + 26 * k + 6 * (1 - v)
            px[x, y] = (int(r), int(g), int(b))
    rnd = random.Random(semente)
    luz = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(luz)
    for _ in range(int(w * h / 9000)):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        r = rnd.uniform(0.6, 2.4) * (w / 1280)
        a = int(rnd.uniform(30, 150) * (1 - min(1, math.hypot(x - cx, y - cy) / raio)))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(*OURO_CLARO, a))
    luz = luz.filter(ImageFilter.GaussianBlur(0.8 * w / 1280))
    img = Image.alpha_composite(img.convert("RGBA"), luz)
    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(sombra)
    for i in range(int(w * 0.6)):   # escuro à esquerda, onde fica o texto
        d.line((i, 0, i, h), fill=(4, 6, 6, int(170 * (1 - i / (w * 0.6)) ** 1.4)))
    img = Image.alpha_composite(img, sombra)
    if escurece:
        img = Image.alpha_composite(img, Image.new("RGBA", (w, h), (4, 6, 6, int(255 * escurece))))
    return img.convert("RGB")


def texto_ouro(d, xy, s, f, anchor="la", cor=OURO, traco=0):
    if traco:
        d.text(xy, s, font=f, fill=cor, anchor=anchor, stroke_width=traco, stroke_fill=(10, 8, 4))
    else:
        d.text(xy, s, font=f, fill=cor, anchor=anchor)


def logo_vertical(largura=640, sombra=True):
    """THE LEGEND OF / ZELDA / OCARINA OF TIME / filete / STEAMDECK VERSION, centrado, em texto."""
    alt = int(largura * 0.72)
    img = Image.new("RGBA", (largura, alt), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = largura / 640
    cx = largura // 2
    texto_ouro(d, (cx, int(36 * k)), "THE LEGEND OF", fonte("CinzelDecorative-Regular.ttf", int(30 * k)), "mt", OURO_CLARO)
    texto_ouro(d, (cx, int(74 * k)), "ZELDA", fonte("CinzelDecorative-Bold.ttf", int(168 * k)), "mt", OURO, int(2 * k))
    texto_ouro(d, (cx, int(268 * k)), "OCARINA OF TIME", fonte("CinzelDecorative-Bold.ttf", int(50 * k)), "mt", OURO_CLARO)
    y = int(346 * k)
    d.line((cx - int(250 * k), y, cx + int(250 * k), y), fill=(*OURO_ESCURO, 255), width=max(1, int(2 * k)))
    r = int(6 * k)
    d.polygon([(cx, y - r), (cx + r, y), (cx, y + r), (cx - r, y)], fill=OURO)
    texto_ouro(d, (cx, int(366 * k)), "STEAMDECK VERSION", fonte("Barlow-Bold.ttf", int(34 * k)), "mt", (240, 236, 224))
    if sombra:
        s = Image.new("RGBA", img.size, (0, 0, 0, 0))
        s.paste((0, 0, 0, 160), mask=img.split()[3])
        s = s.filter(ImageFilter.GaussianBlur(6 * k))
        img = Image.alpha_composite(s, img)
    return img


def logo_horizontal(largura=360):
    k = largura / 360
    img = Image.new("RGBA", (int(largura * 1.12), int(76 * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    texto_ouro(d, (0, 0), "ZELDA", fonte("CinzelDecorative-Bold.ttf", int(46 * k)), "la", OURO)
    texto_ouro(d, (int(178 * k), int(4 * k)), "OCARINA OF TIME", fonte("CinzelDecorative-Regular.ttf", int(19 * k)), "la", OURO_CLARO)
    texto_ouro(d, (int(178 * k), int(30 * k)), "STEAMDECK VERSION", fonte("Barlow-Bold.ttf", int(17 * k)), "la", (236, 232, 220))
    return img


def logo_abertura():
    """O logo da tela de abertura do jogo, 640x478. O renderizador revela a faixa de baixo com um flare: ela tem de
    ficar em x >= 210 e y de 407 a 441 (kSv* em vk_deckport_startup.h)."""
    img = Image.new("RGBA", (640, 478), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    texto_ouro(d, (320, 60), "THE LEGEND OF", fonte("CinzelDecorative-Regular.ttf", 34), "mt", OURO_CLARO)
    texto_ouro(d, (320, 104), "ZELDA", fonte("CinzelDecorative-Bold.ttf", 176), "mt", OURO, 2)
    texto_ouro(d, (320, 306), "OCARINA OF TIME", fonte("CinzelDecorative-Bold.ttf", 54), "mt", OURO_CLARO)
    d.line((70, 386, 570, 386), fill=(*OURO_ESCURO, 255), width=2)
    f = fonte("Barlow-Bold.ttf", 31)
    largura = d.textlength("STEAMDECK VERSION", font=f)
    texto_ouro(d, (636 - largura, 424), "STEAMDECK VERSION", f, "lm", (240, 236, 224))
    assert 636 - largura >= 212, "a faixa STEAMDECK VERSION saiu da área revelada"
    return img


def card(w, h, sel):
    img = Image.new("RGBA", (w, h), (10, 16, 14, 215 if sel else 170))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w - 1, h - 1), outline=(*OURO, 255) if sel else (70, 80, 74, 255), width=3 if sel else 1)
    if sel:
        d.rectangle((0, 0, 6, h - 1), fill=(*OURO, 255))
    return img


def com_logo(base, lg, largura, x, y):
    l2 = lg.resize((largura, round(lg.height * largura / lg.width)), Image.LANCZOS)
    img = base.convert("RGBA")
    if x < 0:
        x = (img.width - l2.width) // 2
    if y < 0:
        y = (img.height - l2.height) // 2
    img.alpha_composite(l2, (x, y))
    return img.convert("RGB")


def logo_do_port():
    """O logo do port (arte/logo.png, 640x478), feito pelo Kewin com IA e liberado por ele para a versão pública
    (2026-11-12). A faixa "STEAMDECK VERSION" fica em x >= 210 e y de 407 a 441: é o que a tela de abertura revela."""
    return Image.open(ARTE / "logo.png").convert("RGBA")


def com_sombra(lg, raio):
    s = Image.new("RGBA", lg.size, (0, 0, 0, 0))
    s.paste((0, 0, 0, 170), mask=lg.split()[3])
    return Image.alpha_composite(s.filter(ImageFilter.GaussianBlur(raio)), lg)


def main():
    for p in (SAIDA, STEAM, ARTE):
        p.mkdir(parents=True, exist_ok=True)
    fundo(W, H).save(SAIDA / "fundo-inicio.png", optimize=True)
    fundo(W, H, escurece=0.15).save(SAIDA / "fundo-passos.png", optimize=True)
    fundo(W, H, escurece=0.25).save(SAIDA / "fundo-instalando.png", optimize=True)
    fundo(W, H, semente=11, brilho=(0.7, 0.5)).save(SAIDA / "fundo-pronto.png", optimize=True)
    lg = logo_do_port()
    com_sombra(lg, 5).resize((440, round(lg.height * 440 / lg.width)), Image.LANCZOS).save(SAIDA / "logo-vertical.png", optimize=True)
    lg.resize((round(lg.width * 132 / lg.height), 132), Image.LANCZOS).save(SAIDA / "logo-horizontal.png", optimize=True)
    for w, h in ((700, 92), (700, 100), (340, 92), (520, 64)):
        for sel in (False, True):
            card(w, h, sel).save(SAIDA / f"card-{w}x{h}{'-sel' if sel else ''}.png", optimize=True)
    # Steam: capa 600x900, horizontal 920x430, fundo 1920x620, logo e ícone
    com_logo(fundo(600, 900, brilho=(0.5, 0.4)), com_sombra(lg, 6), 540, -1, 240).save(STEAM / "capa.png", optimize=True)
    com_logo(fundo(920, 430, brilho=(0.5, 0.5)), com_sombra(lg, 6), 470, -1, -1).save(STEAM / "horizontal.png", optimize=True)
    fundo(1920, 620, brilho=(0.7, 0.45)).save(STEAM / "fundo.png", optimize=True)
    lg.save(STEAM / "logo.png", optimize=True)
    ic = fundo(256, 256, brilho=(0.5, 0.5)).convert("RGBA")
    pq = lg.resize((236, round(lg.height * 236 / lg.width)), Image.LANCZOS)
    ic.alpha_composite(pq, (10, (256 - pq.height) // 2))
    ic.save(STEAM / "icone.png", optimize=True)
    lg.save(ARTE / "logo-abertura.png", optimize=True)
    lg.save(ARTE / "logo-vertical.png", optimize=True)
    print("artes geradas em", SAIDA, "e", ARTE)


if __name__ == "__main__":
    main()

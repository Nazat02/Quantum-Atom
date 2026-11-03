#!/usr/bin/env python3
"""Regenerate the brand/share assets used by the SEO layer.

Outputs (relative to the repo root):
  images/og-image.jpg            1200x630 social share card (kept < 100 KB)
  images/apple-touch-icon.png    180x180
  images/icon-192.png, icon-512.png, icon-512-maskable.png   (site.webmanifest)

Requires: Pillow.   Usage:  python3 tools/seo/make_assets.py
"""
import math
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "images"
BRAND = (255, 91, 20, 255)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def atom_icon(size: int, maskable: bool = False) -> Image.Image:
    """Draw the site's atom badge at `size` px (4x supersampled)."""
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = int(S * 0.10) if maskable else 0
    if maskable:  # full-bleed square so OS masks can crop safely
        d.rectangle([0, 0, S, S], fill=BRAND)
    else:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.2), fill=BRAND)
    sc = (S - 2 * pad) / 90.0
    cx = cy = S / 2

    def ellipse(angle, alpha):
        layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        rx, ry = 34 * sc, 12 * sc
        ImageDraw.Draw(layer).ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            outline=(255, 255, 255, alpha), width=max(2, int(2.2 * sc)))
        return layer.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))

    for ang, a in ((0, 217), (60, 191), (-60, 178)):
        im = Image.alpha_composite(im, ellipse(ang, a))
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    r = 15 * sc
    ImageDraw.Draw(halo).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 90))
    im = Image.alpha_composite(im, halo.filter(ImageFilter.GaussianBlur(sc * 2)))
    nuc = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    nd = ImageDraw.Draw(nuc)
    r = 10 * sc
    nd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 204, 136, 255))
    r2 = 6 * sc
    nd.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 150, 60, 255))
    r3 = 3 * sc
    nd.ellipse([cx - 4 * sc - r3, cy - 4 * sc - r3, cx - 4 * sc + r3, cy - 4 * sc + r3],
               fill=(255, 255, 255, 200))
    im = Image.alpha_composite(im, nuc)
    er, ex = 4.5 * sc, cx + 34 * sc
    ImageDraw.Draw(im).ellipse([ex - er, cy - er, ex + er, cy + er], fill=(255, 255, 255, 255))
    return im.resize((size, size), Image.LANCZOS)


def phone_card(name: str, w: int, h: int, radius: int = 26) -> Image.Image:
    im = Image.open(IMG / name).convert("RGB")
    iw, ih = im.size
    if iw / ih > w / h:
        nw = int(ih * w / h)
        im = im.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
    else:
        nh = int(iw * h / w)
        top = int((ih - nh) * 0.30)
        im = im.crop((0, top, iw, top + nh))
    im = im.resize((w, h), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    out = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, w + 3, h + 3], radius=radius + 2, fill=(255, 120, 50, 120))
    out.paste(im, (2, 2), mask)
    return out


def og_image() -> Image.Image:
    W, H = 1200, 630
    base = Image.new("RGB", (W, H), (6, 4, 3))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gp = glow.load()
    for y in range(H):
        for x in range(W):
            v = max(0, 1 - math.hypot(x - 910, y - 300) / 520) ** 2 * 0.55 \
                + max(0, 1 - math.hypot(x - 80, y - 620) / 420) ** 2 * 0.28
            gp[x, y] = (int(255 * v), int(88 * v), int(14 * v))
    bg = ImageChops.add(base, glow).convert("RGBA")

    pw, ph = 190, 420
    for name, ang, (x, y) in (("preview2.png", -6, (716, 150)),
                              ("preview3.png", 0, (826, 108)),
                              ("preview5.png", 6, (930, 150))):
        card = phone_card(name, pw, ph)
        shadow = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [40, 48, 40 + card.width, 48 + card.height], radius=28, fill=(0, 0, 0, 170))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        shadow.paste(card, (40, 40), card)
        bg.alpha_composite(shadow.rotate(-ang, resample=Image.BICUBIC, expand=True), (x - 40, y - 40))

    f = lambda s, b=True: ImageFont.truetype(FONT_BOLD if b else FONT_REG, s)
    d = ImageDraw.Draw(bg)
    bg.alpha_composite(atom_icon(84), (64, 58))
    d.text((164, 76), "QUANTUM ATOM", font=f(30), fill=(255, 255, 255, 235))
    d.text((64, 190), "See the atom", font=f(66), fill=(255, 255, 255, 255))
    d.text((64, 268), "as it really is.", font=f(66), fill=(255, 122, 48, 255))
    for i, line in enumerate(("Real 3D electron orbitals for all 118",
                              "elements, molecules and nuclei down to",
                              "quarks. Free, in your browser.")):
        d.text((64, 372 + 38 * i), line, font=f(27, False), fill=(235, 225, 218, 235))
    x = 64
    for label in ("118 elements", "Molecules", "Nucleus Explorer"):
        ft = f(21)
        tw = d.textlength(label, font=ft)
        d.rounded_rectangle([x, 528, x + tw + 34, 570], radius=21,
                            fill=(255, 91, 20, 50), outline=(255, 122, 48, 200), width=2)
        d.text((x + 17, 537), label, font=ft, fill=(255, 200, 170, 255))
        x += tw + 48
    return bg.convert("RGB")


def main() -> None:
    atom_icon(180).save(IMG / "apple-touch-icon.png", optimize=True)
    atom_icon(192).save(IMG / "icon-192.png", optimize=True)
    atom_icon(512).save(IMG / "icon-512.png", optimize=True)
    atom_icon(512, maskable=True).save(IMG / "icon-512-maskable.png", optimize=True)
    og_image().save(IMG / "og-image.jpg", quality=84, optimize=True, progressive=True)
    for f in ("og-image.jpg", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-512-maskable.png"):
        print(f"{f:26s}{os.path.getsize(IMG / f):>8,d} bytes")


if __name__ == "__main__":
    main()

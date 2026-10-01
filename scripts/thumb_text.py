#!/usr/bin/env python3
"""
Minimal caption for DroneMill thumbnails: a short place name in wide-spaced capitals, with an
optional small second line, placed in the calmest band of the image (top or bottom) so it
never sits on the subject.

Usage:
  python3 scripts/thumb_text.py <in.jpg> <out.jpg> "THE LIGHTHOUSE" ["3 AM"] [font.ttf]
"""

import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DEFAULT_FONT = "/System/Library/Fonts/Supplemental/Copperplate.ttc"


def _tracked_width(draw, text, font, tracking):
    widths = [draw.textlength(ch, font=font) for ch in text]
    return sum(widths) + tracking * (len(text) - 1)


def _draw_tracked(draw, xy, text, font, tracking, fill):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def _calm_y(img, box_w, box_h):
    """Top y of the calmest spot for a centered text block: scans heights from the top to the
    bottom of the frame and scores each by edge energy plus brightness variation behind the
    block (so it avoids the moon, lamps and busy texture). Slightly prefers the upper half."""
    g = img.convert("L")
    edges = np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    luma = np.asarray(g, dtype=np.float32)
    w, h = img.size
    x0, x1 = int((w - box_w) / 2), int((w + box_w) / 2)
    best, best_y = None, int(h * 0.08)
    for y in range(int(h * 0.06), int(h * 0.90 - box_h), max(4, h // 60)):
        e = edges[y:y + box_h, x0:x1]
        l = luma[y:y + box_h, x0:x1]
        score = e.mean() + 0.6 * l.std()
        if y > h * 0.5:
            score *= 1.25
        if best is None or score < best:
            best, best_y = score, y
    return best_y, best


def _content_box(img):
    """Horizontal extent of the picture, ignoring black pillarbox bars on old square thumbnails."""
    cols = np.asarray(img.convert("L"), dtype=np.float32).mean(axis=0)
    lit = np.nonzero(cols > 12)[0]
    if len(lit) == 0:
        return 0, img.size[0]
    return int(lit[0]), int(lit[-1]) + 1


def caption(img, main, sub=None, font_path=DEFAULT_FONT, position=None):
    """Draws the caption centered on the picture area (pillarbox bars excluded)."""
    full = img.convert("RGB")
    cx0, cx1 = _content_box(full)
    if cx1 - cx0 < full.size[0] * 0.95:
        inner = _caption(full.crop((cx0, 0, cx1, full.size[1])), main, sub, font_path, position)
        full.paste(inner, (cx0, 0))
        return full
    return _caption(full, main, sub, font_path, position)


def _caption(img, main, sub=None, font_path=DEFAULT_FONT, position=None):
    img = img.convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    main = main.upper()
    size = int(h * 0.068)
    font = ImageFont.truetype(font_path, size)
    tracking = size * 0.30
    # shrink long names so they never span more than 70% of the width
    while _tracked_width(draw, main, font, tracking) > w * 0.78 and size > h * 0.035:
        size = int(size * 0.92)
        font = ImageFont.truetype(font_path, size)
        tracking = size * 0.30
    sub_font = ImageFont.truetype(font_path, int(size * 0.5))
    sub_tracking = size * 0.22

    main_w = _tracked_width(draw, main, font, tracking)
    block_h = size + (int(size * 0.95) if sub else 0)
    pad = int(size * 0.6)
    if position == "top":
        y = int(h * 0.09)
    elif position == "bottom":
        y = int(h - h * 0.10 - block_h)
    else:
        y, calm = _calm_y(img, int(main_w) + 2 * pad, block_h + 2 * pad)
        y += pad
        if calm > 28:
            # busy image: a barely visible dark haze behind the text keeps it readable
            haze = Image.new("L", img.size, 0)
            ImageDraw.Draw(haze).ellipse((int((w - main_w) / 2 - pad * 2), int(y - pad * 1.2),
                                          int((w + main_w) / 2 + pad * 2), int(y + block_h + pad * 1.2)), fill=95)
            haze = haze.filter(ImageFilter.GaussianBlur(pad * 1.6))
            img = Image.composite(Image.new("RGB", img.size, (8, 8, 10)), img, haze)
            draw = ImageDraw.Draw(img)

    # light text on dark areas, dark text on very bright areas
    region = np.asarray(img.convert("L").crop((int((w - main_w) / 2), y, int((w + main_w) / 2), y + block_h)))
    light = region.mean() < 150
    fill = (240, 234, 222) if light else (28, 26, 24)
    shadow = (0, 0, 0) if light else (255, 255, 255)

    # very soft shadow layer so the text reads on busy images without looking outlined
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    _draw_tracked(gd, ((w - main_w) / 2, y), main, font, tracking, shadow + (150,))
    if sub:
        sub_text = sub.upper()
        sub_w = _tracked_width(gd, sub_text, sub_font, sub_tracking)
        _draw_tracked(gd, ((w - sub_w) / 2, y + size * 1.3), sub_text, sub_font, sub_tracking, shadow + (150,))
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.18))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    draw = ImageDraw.Draw(img)
    _draw_tracked(draw, ((w - main_w) / 2, y), main, font, tracking, fill)
    if sub:
        sub_text = sub.upper()
        sub_w = _tracked_width(draw, sub_text, sub_font, sub_tracking)
        _draw_tracked(draw, ((w - sub_w) / 2, y + size * 1.3), sub_text, sub_font, sub_tracking, fill)
    return img


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src, dst, main = sys.argv[1:4]
    sub = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
    font = sys.argv[5] if len(sys.argv) > 5 else DEFAULT_FONT
    caption(Image.open(src), main, sub, font).save(dst, quality=92)

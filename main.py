#!/usr/bin/env python3
"""LUMORA — a travel poster for a place that isn't there.

A program that draws one 1024x1024 travel poster with pure Python
standard library only: no network, no fonts, no image libraries.
The PNG is encoded by hand (zlib + struct).

The place: LUMORA, a golden-hour cliff coast where the river does not
fall into the sea — it pours UPWARD, out of a still lake, into a lagoon
that floats in the sky. A small stair-town clings to the cliff and
watches it happen every evening.

Run:  MAKEFUN_OUTPUT_DIR=<dir> python3 main.py
Writes: <dir>/entry.png  (1024x1024, <= 1,048,576 bytes)
"""

import math
import os
import struct
import zlib

W = H = 1024

# ---------------------------------------------------------------- palette
SKY_TOP = (38, 51, 96)        # dusk indigo
SKY_MID = (176, 92, 96)       # rose
SKY_LOW = (246, 178, 82)      # amber horizon
SUN_CORE = (255, 233, 168)
SUN_GLOW = (250, 196, 110)
LAGOON = (53, 181, 172)       # floating lagoon teal
LAGOON_DARK = (29, 122, 114)
LAGOON_LITE = (168, 230, 207)
FALL = (234, 246, 246)        # rising waterfall
FALL_SHADE = (178, 214, 210)
CLIFF = (31, 36, 48)          # cliff silhouette
CLIFF_LITE = (52, 58, 76)
SEA_TOP = (232, 150, 90)      # sea catching the sunset
SEA_BOT = (20, 66, 78)        # deep teal
SEA_DARK = (16, 52, 64)
HOUSE = (43, 43, 58)
ROOF = (224, 120, 86)
WINDOW = (255, 209, 102)
CREAM = (255, 243, 214)       # the place name
NAME_DARK = (28, 36, 64)      # name outline
FRAME = (20, 32, 46)
BIRD = (40, 44, 66)
MIST = (250, 226, 190)

# Deterministic dither table, values -2..2, breaks up gradient banding.
DITHER = [((i * 73 + 41) % 5) - 2 for i in range(256)]


# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def clamp(v):
    return 0 if v < 0 else (255 if v > 255 else v)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def hspan(x0, x1, y, c):
    """Fill a horizontal span of pixels on row y."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    i = (y * W + x0) * 3
    n = x1 - x0 + 1
    buf[i:i + n * 3] = bytes(c) * n


def vgrad(y0, y1, c0, c1, x0=0, x1=W):
    """Vertical gradient band with a whisper of dither."""
    y0 = max(0, y0)
    y1 = min(H, y1)
    span = max(1, y1 - y0 - 1)
    for y in range(y0, y1):
        t = (y - y0) / span
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        row = bytearray((x1 - x0) * 3)
        off = (y * 7) & 255
        for x in range(x0, x1):
            n = DITHER[(x + off) & 255]
            j = (x - x0) * 3
            row[j] = clamp(r + n)
            row[j + 1] = clamp(g + n)
            row[j + 2] = clamp(b + n)
        i = (y * W + x0) * 3
        buf[i:i + len(row)] = row


def fill_poly(points, c):
    """Scanline fill of a simple polygon (list of (x, y))."""
    if not points:
        return
    ys = [p[1] for p in points]
    y_min = max(0, int(min(ys)))
    y_max = min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y_min, y_max + 1):
        xs = []
        for k in range(n):
            x0, y0 = points[k]
            x1, y1 = points[(k + 1) % n]
            if y0 == y1:
                continue
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hspan(int(xs[k]), int(xs[k + 1]), y, c)


def disc(cx, cy, r, c):
    """Filled circle."""
    r = int(r)
    for y in range(max(0, cy - r), min(H - 1, cy + r) + 1):
        dy = y - cy
        dx = int((r * r - dy * dy) ** 0.5)
        hspan(cx - dx, cx + dx, y, c)


def ellipse(cx, cy, rx, ry, c):
    for y in range(max(0, cy - ry), min(H - 1, cy + ry) + 1):
        dy = (y - cy) / ry
        dx = int(rx * (1 - dy * dy) ** 0.5)
        hspan(cx - dx, cx + dx, y, c)


def thick_line(x0, y0, x1, y1, w, c):
    """A line of width w with round caps, drawn as a quad + end discs."""
    dx, dy = x1 - x0, y1 - y0
    L = (dx * dx + dy * dy) ** 0.5
    if L == 0:
        disc(x0, y0, w // 2, c)
        return
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    fill_poly([
        (x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
        (x1 - nx, y1 - ny), (x0 - nx, y0 - ny),
    ], c)
    disc(x0, y0, w // 2, c)
    disc(x1, y1, w // 2, c)


def polyline(points, w, c):
    for a, b in zip(points, points[1:]):
        thick_line(a[0], a[1], b[0], b[1], w, c)


# ---------------------------------------------------------------- the sky
# Three stacked gradients: indigo dusk -> rose -> amber horizon.
vgrad(0, 380, SKY_TOP, SKY_MID)
vgrad(380, 660, SKY_MID, SKY_LOW)

# Faint early stars high up.
for sx, sy, sr in [(120, 60, 2), (240, 110, 2), (360, 45, 1), (480, 90, 2),
                   (620, 55, 1), (760, 100, 2), (880, 50, 2), (940, 130, 1),
                   (60, 150, 1), (300, 160, 1), (830, 170, 1)]:
    disc(sx, sy, sr, (255, 240, 210))

# Sun: glow rings, then the disc, low over the horizon.
for r, col in [(112, (250, 192, 112)), (90, (250, 206, 126)),
               (74, (252, 221, 142))]:
    disc(716, 520, r, col)
disc(716, 520, 60, SUN_CORE)

# A few flat dusk clouds, rose-lit underneath.
for cx, cy, rx, ry in [(180, 300, 120, 16), (250, 318, 90, 12),
                       (880, 248, 100, 13), (818, 264, 72, 10)]:
    ellipse(cx, cy, rx, ry, (214, 128, 110))
    ellipse(cx, cy - 4, rx - 18, ry - 4, (232, 158, 122))

# ---------------------------------------------------------------- the lagoon
# The floating lagoon: an ellipse of water hovering in the sky, dark rim,
# teal body, a bright wind-line across it.
ellipse(716, 345, 190, 60, LAGOON_DARK)
ellipse(716, 341, 182, 54, LAGOON)
ellipse(716, 333, 146, 32, (64, 196, 184))
# Two pale wind-lines on the lagoon.
for wy, wr in [(327, 116), (345, 84)]:
    ellipse(716, wy, wr, 5, LAGOON_LITE)

# ---------------------------------------------------------------- the rising fall
# The river pours UPWARD: a column of water from the lake below to the
# lagoon above, slightly bowed, with white streaks and mist at both ends.
fill_poly([(676, 407), (700, 407), (706, 500), (700, 618),
           (724, 618), (730, 500), (724, 407)], FALL_SHADE)
fill_poly([(684, 407), (700, 407), (704, 500), (700, 618),
           (716, 618), (720, 500), (716, 407)], FALL)
# White streaks inside the column, climbing upward.
for sx in (690, 700, 710):
    for sy in range(425, 610, 34):
        hspan(sx - 2, sx + 2, sy, (255, 255, 255))
# Mist where the water leaves the lake, and where it arrives.
for mx, my, mr in [(700, 622, 26), (676, 628, 16), (726, 628, 16),
                   (700, 403, 22), (682, 407, 12), (720, 407, 12)]:
    disc(mx, my, mr, MIST)

# ---------------------------------------------------------------- the sea
# Horizon at y=660. Sunset amber at the top, deep teal at the bottom.
vgrad(660, 1024, SEA_TOP, SEA_BOT)
# Sun's reflection: a continuous shimmering amber column on the water,
# widening and wavering as it runs toward the viewer.
for y in range(664, 1024):
    t = (y - 664) / 360.0
    wob = int(20 + 16 * t + 3 * math.sin(y / 60.0))
    hspan(716 - wob, 716 + wob, y, (246, 182, 96))
    inner = int(wob * 0.5)
    hspan(716 - inner, 716 + inner, y, (250, 206, 132))
# A few distant boats for scale, dark hulls with pale sails.
for bx, by, s in [(180, 760, 1.0), (880, 820, 0.8), (330, 900, 0.7)]:
    fill_poly([(bx - 26 * s, by), (bx + 26 * s, by),
               (bx + 16 * s, by + 10 * s), (bx - 16 * s, by + 10 * s)],
              (36, 40, 60))
    fill_poly([(bx, by - 34 * s), (bx, by), (bx + 20 * s, by)], (250, 238, 210))
    fill_poly([(bx - 2, by - 30 * s), (bx - 2, by), (bx - 18 * s, by)],
              (232, 214, 180))

# ---------------------------------------------------------------- the cliff
# Dark headland on the left, rising out of the sea toward the lagoon.
fill_poly([(0, 1024), (0, 700), (90, 640), (190, 600), (300, 560),
           (360, 540), (330, 620), (300, 720), (260, 860), (220, 1024)],
          CLIFF)
# Warm rim light along the cliff's top edge.
polyline([(0, 700), (90, 640), (190, 600), (300, 560), (360, 540)],
         6, (246, 178, 96))
# The stair-town: small houses with lit windows climbing the cliff edge.
houses = [
    (52, 668, 44, 32), (118, 640, 40, 30), (182, 612, 44, 32),
    (238, 588, 40, 30), (288, 566, 42, 30),
]
for hx, hy, hw, hh in houses:
    fill_poly([(hx, hy), (hx + hw, hy), (hx + hw, hy + hh),
               (hx, hy + hh)], HOUSE)
    fill_poly([(hx - 4, hy), (hx + hw // 2, hy - 16),
               (hx + hw + 4, hy)], ROOF)
    hspan(hx + hw // 2 - 8, hx + hw // 2 - 4, hy + 12, WINDOW)
    hspan(hx + hw // 2 - 8, hx + hw // 2 - 4, hy + 13, WINDOW)
    hspan(hx + hw // 2 + 4, hx + hw // 2 + 8, hy + 12, WINDOW)
    hspan(hx + hw // 2 + 4, hx + hw // 2 + 8, hy + 13, WINDOW)

# Foreground rocks, bottom corners.
fill_poly([(0, 1024), (0, 960), (120, 940), (210, 980), (240, 1024)],
          SEA_DARK)
fill_poly([(1024, 1024), (1024, 970), (920, 950), (830, 985), (800, 1024)],
          SEA_DARK)

# ---------------------------------------------------------------- birds
for bx, by, s in [(560, 420, 14), (600, 400, 11), (530, 452, 9),
                  (840, 430, 12), (880, 405, 9)]:
    polyline([(bx - s, by), (bx, by - s // 2), (bx + s, by)], 4, BIRD)

# ---------------------------------------------------------------- the name
# LUMORA, hand-lettered in strokes: dark outline first, cream on top.
# Glyph strokes in a 100 x 140 box (x 0..100, y 0..140, top to bottom).
GLYPHS = {
    "L": [[(8, 8), (8, 132), (92, 132)]],
    "U": [[(8, 8), (8, 108), (50, 132), (92, 108), (92, 8)]],
    "M": [[(8, 132), (8, 8), (50, 72), (92, 8), (92, 132)]],
    "O": [[(50, 8), (78, 14), (92, 40), (92, 100), (78, 126),
           (50, 132), (22, 126), (8, 100), (8, 40), (22, 14), (50, 8)]],
    "R": [[(8, 132), (8, 8), (62, 8), (88, 28), (88, 52), (62, 72),
           (8, 72)],
          [(56, 72), (92, 132)]],
    "A": [[(8, 132), (50, 8), (92, 132)], [(28, 86), (72, 86)]],
}

NAME = "LUMORA"
SCALE = 0.92
GW, GH = int(100 * SCALE), int(140 * SCALE)   # glyph box on canvas
GAP = 22
total_w = 6 * GW + 5 * GAP
x0 = (W - total_w) // 2
y0 = 96


def draw_name(width, color):
    for i, ch in enumerate(NAME):
        ox = x0 + i * (GW + GAP)
        for strokes in GLYPHS[ch]:
            pts = [(ox + int(px_ * SCALE), y0 + int(py_ * SCALE))
                   for px_, py_ in strokes]
            polyline(pts, width, color)


draw_name(30, NAME_DARK)   # outline
draw_name(20, CREAM)       # face
# A thin rule under the name, carrying the poster's mood.
hspan(x0 + 40, x0 + total_w - 40, y0 + GH + 26, CREAM)
hspan(x0 + 40, x0 + total_w - 40, y0 + GH + 30, NAME_DARK)

# ---------------------------------------------------------------- frame
# Vintage poster frame: dark border, thin cream inner rule.
for t in range(0, 26):
    hspan(t, W - 1 - t, t, FRAME)
    hspan(t, W - 1 - t, H - 1 - t, FRAME)
    for y in range(t, H - t):
        px(t, y, FRAME)
        px(W - 1 - t, y, FRAME)
hspan(34, W - 35, 34, CREAM)
hspan(34, W - 35, H - 35, CREAM)
for y in range(34, H - 34):
    px(34, y, CREAM)
    px(W - 35, y, CREAM)


# ---------------------------------------------------------------- PNG encode
def write_png(path):
    raw = bytearray()
    prev = bytes(W * 3)
    for y in range(H):
        row = bytes(buf[y * W * 3:(y + 1) * W * 3])
        # Filter type 2 (Up): store row minus previous row, byte-wise.
        filt = bytes((a - b) & 0xFF for a, b in zip(row, prev))
        raw.append(2)
        raw.extend(filt)
        prev = row
    data = zlib.compress(bytes(raw), 9)

    def chunk(typ, payload):
        c = struct.pack(">I", len(payload)) + typ + payload
        return c + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", data)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()

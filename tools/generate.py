#!/usr/bin/env python3
"""Generates the profile's SVG assets into ../assets.

Text is outlined to glyph paths because an SVG loaded through <img> cannot
load web fonts. Needs fonttools, plus the JetBrainsMono Nerd Font and Noto Sans
CJK files at the paths in FONTS below:

    python3 -m venv .venv && .venv/bin/pip install fonttools
    .venv/bin/python tools/generate.py
"""

import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.basePen import BasePen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTCollection, TTFont

OUT = Path(__file__).resolve().parent.parent / "assets"

FONTS = {
    "r": TTFont("/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"),
    "b": TTFont("/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"),
    "c": TTCollection("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc").fonts[0],
}

THEMES = {
    "dark": {
        "bg0": "#0d1117", "bg1": "#111a22", "panel": "#131a22", "panel2": "#19212b",
        "line": "#2a3440", "text": "#e6edf3", "text2": "#b1bac4", "text3": "#8b949e",
        "green": "#4fd1a5", "purple": "#a78bfa", "amber": "#e3b341",
        "glow0": "#22a884", "glow1": "#512bd4", "grid": "#1b232d",
    },
    "light": {
        "bg0": "#f4faf7", "bg1": "#f1effc", "panel": "#ffffff", "panel2": "#f6f8fa",
        "line": "#d8dee4", "text": "#101218", "text2": "#4b5563", "text3": "#6b7280",
        "green": "#13795c", "purple": "#512bd4", "amber": "#9a6700",
        "glow0": "#22a884", "glow1": "#512bd4", "grid": "#e4ebe8",
    },
}

MONO = 0.6  # JetBrains Mono advance, in em
MOTION_OFF = "@media (prefers-reduced-motion: reduce) {"


class Text:
    """Lays out outlined text, emitting each glyph once as a shared <path>."""

    def __init__(self):
        self.defs = {}

    def _glyph(self, font, ch):
        tt = FONTS[font]
        name = tt.getBestCmap()[ord(ch)]
        gid = f"{font}{ord(ch):x}"
        if gid not in self.defs:
            glyphs = tt.getGlyphSet()
            pen = SVGPathPen(glyphs, ntos=lambda v: str(round(v)))
            glyphs[name].draw(pen)
            self.defs[gid] = pen.getCommands()
        upem = tt["head"].unitsPerEm
        return gid, tt["hmtx"][name][0] / upem

    def width(self, s, size, font="r"):
        return sum(self._glyph(self._face(font, c), c)[1] for c in s) * size

    @staticmethod
    def _face(font, ch):
        return "c" if ord(ch) > 0x2fff else font

    def run(self, s, x, y, size, fill, font="r", anchor="start", extra=""):
        if anchor == "middle":
            x -= self.width(s, size, font) / 2
        elif anchor == "end":
            x -= self.width(s, size, font)
        scale = size / 1000
        pen_x, uses = 0.0, []
        for ch in s:
            gid, adv = self._glyph(self._face(font, ch), ch)
            if ch != " ":
                uses.append(f'<use href="#{gid}" x="{round(pen_x)}"/>')
            pen_x += adv * 1000
        return (
            f'<g fill="{fill}" transform="translate({x:.1f} {y:.1f}) scale({scale:.4f} {-scale:.4f})"'
            f' {extra}>{"".join(uses)}</g>'
        )

    def defs_svg(self):
        return "".join(f'<path id="{k}" d="{v}"/>' for k, v in self.defs.items())


def svg(w, h, title, defs, style, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"'
        f' role="img" aria-label="{escape(title, {chr(34): "&quot;"})}"><title>{escape(title)}</title>'
        f"<defs>{defs}</defs><style>{style}</style>{body}</svg>"
    )


def write(name, content):
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    print(f"{name:24} {len(content.encode()) / 1024:7.1f} KB")


def mix(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def backdrop(w, h, t, uid="bg"):
    defs = (
        f'<linearGradient id="{uid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{t["bg0"]}"/><stop offset="1" stop-color="{t["bg1"]}"/></linearGradient>'
        f'<radialGradient id="{uid}g"><stop offset="0" stop-color="{t["glow0"]}" stop-opacity=".22"/>'
        f'<stop offset="1" stop-color="{t["glow0"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="{uid}p"><stop offset="0" stop-color="{t["glow1"]}" stop-opacity=".24"/>'
        f'<stop offset="1" stop-color="{t["glow1"]}" stop-opacity="0"/></radialGradient>'
        f'<pattern id="{uid}d" width="28" height="28" patternUnits="userSpaceOnUse">'
        f'<circle cx="1.5" cy="1.5" r="1.1" fill="{t["grid"]}"/></pattern>'
        f'<clipPath id="{uid}c"><rect width="{w}" height="{h}" rx="16"/></clipPath>'
    )
    body = (
        f'<rect width="{w}" height="{h}" fill="url(#{uid})"/>'
        f'<rect width="{w}" height="{h}" fill="url(#{uid}d)"/>'
        f'<ellipse cx="{w * .2:.0f}" cy="{h * .35:.0f}" rx="{w * .4:.0f}" ry="{h * .8:.0f}" fill="url(#{uid}g)"/>'
        f'<ellipse cx="{w * .82:.0f}" cy="{h * .7:.0f}" rx="{w * .42:.0f}" ry="{h * .85:.0f}" fill="url(#{uid}p)"/>'
    )
    return defs, body


# --- hero: a murmuration that spells words ---------------------------------


class Outline(BasePen):
    """Flattens a glyph into closed polygons for point-in-shape tests."""

    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.polys, self.cur = [], []

    def _moveTo(self, p):
        self.cur = [p]
        self.polys.append(self.cur)

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for i in range(1, 9):
            u = i / 8
            v = 1 - u
            self.cur.append(tuple(
                v * v * v * p0[k] + 3 * v * v * u * a[k] + 3 * v * u * u * b[k] + u * u * u * c[k]
                for k in (0, 1)
            ))

    def _qCurveToOne(self, a, c):
        p0 = self.cur[-1]
        for i in range(1, 9):
            u = i / 8
            v = 1 - u
            self.cur.append(tuple(v * v * p0[k] + 2 * v * u * a[k] + u * u * c[k] for k in (0, 1)))


def winding(polys, x, y):
    wn = 0
    for poly in polys:
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            if (y0 <= y) != (y1 <= y):
                if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                    wn += 1 if y1 > y0 else -1
    return wn


def word_points(s, size, cx, baseline, count, rng):
    tt, glyphs, cmap = FONTS["b"], FONTS["b"].getGlyphSet(), FONTS["b"].getBestCmap()
    x0, scale, pts = cx - len(s) * MONO * size / 2, size / 1000, []
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        pen = Outline(glyphs)
        glyphs[cmap[ord(ch)]].draw(pen)
        polys = [[(x0 + (i * 600 + px) * scale, baseline - py * scale) for px, py in p] for p in pen.polys]
        for gy in range(int(baseline - size), int(baseline + size * .3), 3):
            for gx in range(int(x0 + i * 600 * scale), int(x0 + (i + 1) * 600 * scale), 3):
                if winding(polys, gx + .5, gy + .5):
                    pts.append((gx + rng.random(), gy + rng.random()))
    pts = sorted(rng.sample(pts, count), key=lambda p: p[0])
    return pts


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def hero(theme, t):
    rng = random.Random(1071)
    w, h = 1280, 400
    loop, step = 28.0, 0.5
    n = 460
    size, base = 142, 216
    a_pts = word_points("Mark Walls", size, w / 2, base, n, rng)
    b_pts = word_points(".NET + AI", size, w / 2, base, n, rng)

    ball = []
    for _ in range(n):
        while True:
            p = [rng.gauss(0, .8) for _ in range(3)]
            if sum(v * v for v in p) < 4.5:
                break
        ball.append(p)

    def flock(i, s):
        bx, by, bz = ball[i]
        lag = s - .22 * abs(bx)
        cx = 640 + 400 * math.sin(lag * .42 + 1.4) + 90 * math.sin(lag * .97)
        cy = 138 + 34 * math.sin(lag * .71 + .5)
        yaw, pitch = s * .48, .55 + .38 * math.sin(s * .37)
        x = bx * math.cos(yaw) + bz * math.sin(yaw)
        z = -bx * math.sin(yaw) + bz * math.cos(yaw)
        y = by * math.cos(pitch) - z * math.sin(pitch)
        # Stretch and squeeze in antiphase so density rolls through the flock.
        pulse = math.sin(s * .83)
        sx, sy = 112 + 58 * pulse, 40 - 19 * pulse
        px = x * sx
        bend = 30 * math.sin(s * .61 + 2) * (px / 150) ** 2
        return cx + px, cy + y * sy + bend + 12 * math.sin(s * 1.9 + bx * 2.2)

    # (start, end, departing-from word or None, arriving-at word or None)
    moves = [(5.2, 7.9, a_pts, None), (11.3, 14.0, None, b_pts), (19.0, 21.7, b_pts, None), (24.5, 27.2, None, a_pts)]

    def blend(i, s):
        spread = 1.1
        for start, end, leaving, arriving in moves:
            word = leaving or arriving
            xn = word[i][0] / w
            if s < end:
                u = smooth((s - start - spread * xn) / (end - start - spread))
                fx, fy = flock(i, s)
                if leaving:
                    if s < start:
                        return word[i]
                    return word[i][0] + (fx - word[i][0]) * u, word[i][1] + (fy - word[i][1]) * u
                if s < start:
                    return fx, fy
                return fx + (word[i][0] - fx) * u, fy + (word[i][1] - fy) * u
            if arriving and end <= s < moves[(moves.index((start, end, leaving, arriving)) + 1) % 4][0]:
                return arriving[i]
        return a_pts[i]

    frames = int(loop / step)
    groups = {}
    for i in range(n):
        vals = []
        for f in range(frames + 1):
            x, y = blend(i, f * step % loop if f < frames else 0.0)
            vals.append(f"{x - a_pts[i][0]:.0f} {y - a_pts[i][1]:.0f}")
        bucket = min(5, int(a_pts[i][0] / w * 6))
        r = 2.1 + .8 * rng.random()
        groups.setdefault(bucket, []).append(
            f'<circle cx="{a_pts[i][0]:.0f}" cy="{a_pts[i][1]:.0f}" r="{r:.1f}">'
            f'<animateTransform attributeName="transform" type="translate" dur="{loop:.0f}s"'
            f' repeatCount="indefinite" values="{";".join(vals)}"/></circle>'
        )
    flock_svg = "".join(
        f'<g fill="{mix(t["green"], t["purple"], k / 5)}">{"".join(v)}</g>' for k, v in sorted(groups.items())
    )

    x = Text()
    bg_defs, bg = backdrop(w, h, t)
    defs = bg_defs

    def word(s, cls):
        left = w / 2 - len(s) * MONO * size / 2
        letters = "".join(
            x.run(ch, left + i * MONO * size, base, size, mix(t["green"], t["purple"], i / (len(s) - 1)), "b")
            for i, ch in enumerate(s) if ch != " "
        )
        return f'<g class="{cls}">{letters}</g>'

    pct = lambda s: f"{s / loop * 100:.2f}%"
    style = f"""
    .wa{{animation:wa {loop:.0f}s linear infinite}}
    .wb{{opacity:0;animation:wb {loop:.0f}s linear infinite}}
    .fl{{opacity:0;animation:fl {loop:.0f}s linear infinite}}
    @keyframes wa{{0%,{pct(5.2)}{{opacity:1}}{pct(5.7)},{pct(26.7)}{{opacity:0}}{pct(27.3)},100%{{opacity:1}}}}
    @keyframes wb{{0%,{pct(13.6)}{{opacity:0}}{pct(14.2)},{pct(19.0)}{{opacity:1}}{pct(19.5)},100%{{opacity:0}}}}
    @keyframes fl{{0%,{pct(4.9)}{{opacity:0}}{pct(5.2)},{pct(13.9)}{{opacity:1}}{pct(14.4)},{pct(18.7)}{{opacity:0}}{pct(19.0)},{pct(27.0)}{{opacity:1}}{pct(27.4)},100%{{opacity:0}}}}
    {MOTION_OFF}.fl,.wb{{display:none}}.wa{{animation:none}}}}
    """
    body = bg
    body += f'<g class="fl">{flock_svg}</g>'
    body += word("Mark Walls", "wa")
    body += word(".NET + AI", "wb")
    body += x.run("A model should be a PackageReference.", w / 2, 296, 25, t["text"], "b", "middle")
    body += x.run("In-process on CPU or CUDA · no Python sidecar · no cloud API", w / 2, 334, 18, t["text3"], "r", "middle")
    defs += x.defs_svg()
    title = "Mark Walls: a model should be a PackageReference. A murmuration of starlings forms the name, then .NET + AI."
    write(f"hero-{theme}.svg", svg(w, h, title, defs, style, f'<g clip-path="url(#bgc)">{body}</g>'))


# --- terminal: the Starling quickstart, typed out --------------------------


def terminal():
    t = THEMES["dark"]
    w, h, lh, fs = 1280, 446, 34, 20
    x0, y0, cw = 44, 104, fs * MONO
    loop = 18.0
    x = Text()
    prompt, body, covers, style = t["green"], [], [], []
    pct = lambda s: f"{s / loop * 100:.2f}%"

    def typed(idx, s, y, start, cps=46):
        dur = len(s) / cps
        lx = x0 + 2 * cw
        ww = len(s) * cw + 4
        name = f"c{idx}"
        steps = max(1, len(s))
        style.append(
            f".{name}{{animation:{name} {loop:.0f}s infinite}}"
            f"@keyframes {name}{{0%{{transform:translateX(0)}}"
            f"{pct(start)}{{transform:translateX(0);animation-timing-function:steps({steps},end)}}"
            f"{pct(start + dur)},{pct(loop - .25)}{{transform:translateX({ww:.0f}px)}}"
            f"100%{{transform:translateX(0)}}}}"
        )
        body.append(x.run("$", x0, y, fs, prompt, "b"))
        body.append(x.run(s, lx, y, fs, t["text"], "r"))
        covers.append(f'<rect class="cov {name}" x="{lx - 1:.0f}" y="{y - fs - 2}" width="{ww:.0f}" height="{lh}" fill="#0a0e13"/>')
        return start + dur

    def show(idx, inner, start):
        name = f"s{idx}"
        style.append(
            f".{name}{{opacity:0;animation:{name} {loop:.0f}s infinite}}"
            f"@keyframes {name}{{0%,{pct(start)}{{opacity:0}}{pct(start + .25)},{pct(loop - .25)}{{opacity:1}}100%{{opacity:0}}}}"
        )
        body.append(f'<g class="rv {name}">{inner}</g>')

    now = typed(0, "dotnet add package Starlings.Models.E5.Extensions.AI", y0, .5)
    now = typed(1, "dotnet add package Microsoft.ML.OnnxRuntime --version 1.30.0", y0 + lh, now + .55)
    now = typed(2, "dotnet run", y0 + 2 * lh, now + .55)
    now += .6

    y = y0 + 3 * lh + 12
    show(0, x.run("query: Which river runs through Cologne?", x0, y, fs, t["purple"], "b"), now)
    now += .45
    rows = [
        (.680, "passage: The Eiffel Tower is in Paris.", False),
        (.807, "passage: Der Rhein fließt durch Köln.", True),
        (.688, "passage: 富士山は日本一高い山です。", False),
    ]
    bar_x, bar_w = x0 + 7 * cw, 250
    for i, (score, label, best) in enumerate(rows):
        y = y0 + (4 + i) * lh + 26
        ink, muted = (t["green"], t["text"]) if best else (t["text3"], t["text2"])
        name = f"b{i}"
        span = bar_w * score
        start = now + i * .22
        style.append(
            f".{name}{{transform-box:fill-box;transform-origin:left;animation:{name} {loop:.0f}s infinite}}"
            f"@keyframes {name}{{0%,{pct(start)}{{transform:scaleX(0)}}{pct(start + .7)},{pct(loop - .25)}{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}"
        )
        row = x.run(f"{score:.3f}", x0, y, fs, ink, "b")
        row += f'<rect x="{bar_x:.0f}" y="{y - 14}" width="{bar_w}" height="14" rx="3" fill="#19212b"/>'
        row += f'<rect class="{name}" x="{bar_x:.0f}" y="{y - 14}" width="{span:.0f}" height="14" rx="3" fill="{ink}"/>'
        row += x.run(label, bar_x + bar_w + 24, y, fs, muted, "b" if best else "r")
        show(1 + i, row, start)
    now += 1.1
    y = y0 + 8 * lh + 8
    show(4, x.run("Three languages, one vector space. In-process, no Python, no network after the first run.", x0, y, 18, t["text3"]), now)

    win = (
        f'<rect width="{w}" height="{h}" rx="16" fill="#0a0e13"/>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="none" stroke="#252d38"/>'
        f'<path d="M0 54H{w}" stroke="#1c232c"/>'
        '<circle cx="30" cy="27" r="7" fill="#ff5f57"/><circle cx="54" cy="27" r="7" fill="#febc2e"/><circle cx="78" cy="27" r="7" fill="#28c840"/>'
    )
    win += x.run("~/search · multilingual semantic search in .NET", w / 2, 33, 15, t["text3"], "r", "middle")
    css = (
        "".join(style)
        + f"{MOTION_OFF}.cov{{display:none}}.rv{{opacity:1;animation:none}}.rv rect{{animation:none}}}}"
    )
    clip = f'<clipPath id="win"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16"/></clipPath>'
    title = "Terminal: adding a Starling package and running multilingual semantic search. The German passage scores highest, 0.807."
    write("terminal.svg", svg(w, h, title, clip + x.defs_svg(), css, win + "".join(body) + f'<g clip-path="url(#win)">{"".join(covers)}</g>'))


# --- buttons: open an assistant with a prompt already filled in -------------


def button(slug, label):
    h, x = 64, Text()
    w = round(x.width(label, 24, "b") + 72)
    defs = (
        '<linearGradient id="bt" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#13795c"/><stop offset="1" stop-color="#512bd4"/></linearGradient>'
    )
    body = f'<rect width="{w}" height="{h}" rx="32" fill="url(#bt)"/>'
    body += x.run(label, w / 2, 41, 24, "#ffffff", "b", "middle")
    write(f"ask-{slug}.svg", svg(w, h, label, defs + x.defs_svg(), "", body))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for theme_name, palette in THEMES.items():
        hero(theme_name, palette)
    terminal()
    button("claude", "Ask Claude")
    button("chatgpt", "Ask ChatGPT")
    button("perplexity", "Ask Perplexity")

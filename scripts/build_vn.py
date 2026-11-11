"""Add Vietnamese glyphs to Fira Code.

usage: build_vn.py <FiraCode-X.ttf> <FiraSans-Y.ttf> <out.ttf>

Strategy
- Reuse Fira Code's own accents (acute, grave, tilde, circumflex, breve, dotaccent).
- Borrow only what Fira Code lacks from Fira Sans (same Fira family):
  hook above, horn.
- Build new mark glyphs (advance 1200, drawn over a centred cell like Fira
  Code's own spacing accents), then build each Vietnamese letter as a TrueType
  composite: base + marks.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib.tables._g_l_y_f import GlyphComponent, Glyph, OVERLAP_COMPOUND

code_path, sans_path, out_path = sys.argv[1:4]
code = TTFont(code_path)
sans = TTFont(sans_path)
cglyf = code["glyf"]
cgs = code.getGlyphSet()
sgs = sans.getGlyphSet()
ccmap = code.getBestCmap()
scmap = sans.getBestCmap()
ADV = 1200


def bounds(gs, name):
    bp = BoundsPen(gs)
    gs[name].draw(bp)
    return bp.bounds  # xMin, yMin, xMax, yMax


def new_glyph(name, src_gs, src_name, sx, sy, dx, dy):
    """Draw src glyph transformed (scale then translate) into a new contour glyph."""
    pen = TTGlyphPen(None)
    src_gs[src_name].draw(TransformPen(pen, (sx, 0, 0, sy, dx, dy)))
    g = pen.glyph()
    add_glyph(name, g)


def add_glyph(name, g):
    order = code.getGlyphOrder()
    if name not in order:
        order.append(name)
        code.setGlyphOrder(order)
    cglyf[name] = g
    g.recalcBounds(cglyf)
    code["hmtx"][name] = (ADV, getattr(g, "xMin", 0))


def place(src_gs, src, name, *, w=None, h=None, cx=None, x0=None, x1=None, y0=None, y1=None, scale=None):
    """Create mark glyph `name` from `src`, scaled to width w/height h (or uniform
    scale), then positioned by centre-x / left / right and bottom / top."""
    b = bounds(src_gs, src)
    bw, bh = b[2] - b[0], b[3] - b[1]
    if w:
        sx = w / bw
    elif h and not scale:
        sx = h / bh
    else:
        sx = scale if scale else 1
    sy = (h / bh) if h else (scale if scale else sx)
    nw, nh = bw * sx, bh * sy
    if cx is not None:
        left = cx - nw / 2
    elif x0 is not None:
        left = x0
    else:
        left = x1 - nw
    bottom = y0 if y0 is not None else y1 - nh
    new_glyph(name, src_gs, src, sx, sy, left - b[0] * sx, bottom - b[1] * sy)
    return (left, bottom, left + nw, bottom + nh)


# ---------------------------------------------------------------- metrics
xh = bounds(cgs, "x")[3]
cap = bounds(cgs, "H")[3]
acute_b = bounds(cgs, "acute")
CX = (acute_b[0] + acute_b[2]) / 2  # centre of Fira Code's lowercase accents
acute_c = bounds(cgs, "acute.case")
CXC = (acute_c[0] + acute_c[2]) / 2

# scale Fira Sans -> Fira Code: match the acute height so borrowed marks have
# the same visual size as Fira Code's own marks
k_low = (acute_b[3] - acute_b[1]) / (lambda b: b[3] - b[1])(bounds(sgs, "acutecomb"))
k_cap = (acute_c[3] - acute_c[1]) / (lambda b: b[3] - b[1])(bounds(sgs, "acutecomb.case"))
k_horn = 1950 / sans["head"].unitsPerEm

# ---------------------------------------------------------------- marks
# hook above (dấu hỏi) — same bottom as acute, centred like the other accents
hb = bounds(sgs, "hookabovecomb")
place(sgs, "hookabovecomb", "vn.hook", scale=k_low, cx=CX, y0=acute_b[1])
place(sgs, "hookabovecomb.case", "vn.hook.case", scale=k_cap, cx=CXC, y0=acute_c[1])

# dot below (dấu nặng) — Fira Code's own dot, moved below the baseline
dot = bounds(cgs, "dotaccent")
DOT_TOP = -110
place(cgs, "dotaccent", "vn.dotbelow", scale=1.0, cx=600, y1=DOT_TOP)

# horn — Fira Sans' combining horn
place(sgs, "uni031B", "vn.horn", scale=k_horn, x0=0, y0=0)
place(sgs, "uni031B", "vn.horn.case", scale=k_horn * 1.08, x0=0, y0=0)

# ---- stacked marks (Vietnamese style: tone right/left of circumflex, on top of breve)
# Must stay legible at terminal sizes (12-14 px): keep the circumflex near full
# size and put acute/grave/hook BESIDE it (so they need little extra height)
# at ~80% of Fira Code's own accent size. Tilde goes on top.
circ = bounds(cgs, "circumflex")
circC = bounds(cgs, "circumflex.case")
CW = (circ[2] - circ[0]) * 0.84          # circumflex width when stacked
SHIFT = 85                                # move circumflex away from the side mark


def circ_set(suffix, src, y0, h, cx, top, tone_h, hook_h, tilde_h):
    left = place(cgs, src, f"vn.circ.acute{suffix}", w=CW, h=h, cx=cx - SHIFT, y0=y0)
    place(cgs, src, f"vn.circ.hook{suffix}", w=CW, h=h, cx=cx - SHIFT, y0=y0)
    right = place(cgs, src, f"vn.circ.grave{suffix}", w=CW, h=h, cx=cx + SHIFT, y0=y0)
    mid = place(cgs, src, f"vn.circ.tilde{suffix}", w=CW * 0.92, h=h * 0.85, cx=cx, y0=y0)
    place(cgs, "acute", f"vn.circacute{suffix}", h=tone_h, x0=left[2] - 135, y1=top)
    place(cgs, "grave", f"vn.circgrave{suffix}", h=tone_h, x1=right[0] + 135, y1=top)
    place(sgs, "hookabovecomb", f"vn.circhook{suffix}", h=hook_h, x0=left[2] - 95, y1=top)
    place(cgs, "tilde", f"vn.circtilde{suffix}", w=(mid[2] - mid[0]) * 0.95, h=tilde_h,
          cx=cx, y0=mid[3] + 55)


circ_set("", "circumflex", circ[1], 285, CX, 1760, 260, 290, 165)
circ_set(".case", "circumflex.case", 1445, 215, CXC, 1800, 215, 235, 130)

brv = bounds(cgs, "breve")


def breve_set(suffix, src, y0, h, cx, top, tone_h, hook_h, tilde_h):
    bb = place(cgs, src, f"vn.breve{suffix}", w=(brv[2] - brv[0]) * 0.86, h=h, cx=cx, y0=y0)
    place(cgs, "acute", f"vn.breveacute{suffix}", h=tone_h, cx=cx + 25, y1=top)
    place(cgs, "grave", f"vn.brevegrave{suffix}", h=tone_h, cx=cx - 25, y1=top)
    place(sgs, "hookabovecomb", f"vn.brevehook{suffix}", h=hook_h, cx=cx, y1=top)
    place(cgs, "tilde", f"vn.brevetilde{suffix}", w=(bb[2] - bb[0]) * 0.95, h=tilde_h, cx=cx,
          y0=bb[3] + 55)


breve_set("", "breve", brv[1], 230, CX, 1775, 235, 260, 160)
breve_set(".case", "breve.case", 1440, 170, CXC, 1805, 180, 200, 125)

# ---------------------------------------------------------------- letters
def accent_dx(base_char, upper):
    """x offset Fira Code uses for accents on this base (from its á / Á)."""
    acute_map = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "y": "ý"}
    ch = acute_map[base_char.lower()]
    if upper:
        ch = ch.upper()
    g = cglyf[ccmap[ord(ch)]]
    return g.components[1].x


def base_glyph(base_char):
    if base_char == "i":
        return "dotlessi"
    return ccmap[ord(base_char)]


def dot_dx(base_char):
    """dot below x: follow Fira Sans' relative position (matters for y/Y)."""
    sname = scmap[ord({"a": "ạ", "e": "ẹ", "i": "ị", "o": "ọ", "u": "ụ", "y": "ỵ"}[base_char.lower()]
                      if base_char.islower() else
                      {"a": "Ạ", "e": "Ẹ", "i": "Ị", "o": "Ọ", "u": "Ụ", "y": "Ỵ"}[base_char.lower()])]
    sg = sans["glyf"][sname]
    sb = bounds(sgs, sg.components[0].glyphName)
    dc = [c for c in sg.components if c.glyphName == "dotbelowcomb"][0]
    db = bounds(sgs, "dotbelowcomb")
    sdot = dc.x + (db[0] + db[2]) / 2
    rel = (sdot - sb[0]) / (sb[2] - sb[0])
    cb = bounds(cgs, ccmap[ord(base_char)])
    return cb[0] + rel * (cb[2] - cb[0]) - 600


def horn_base(base_char):
    """create ơ/ư/Ơ/Ư (horn attached at upper right of o/u/O/U)."""
    name = {"o": "uni01A1", "u": "uni01B0", "O": "uni01A0", "U": "uni01AF"}[base_char]
    sname = scmap[ord({"o": "ơ", "u": "ư", "O": "Ơ", "U": "Ư"}[base_char])]
    plain = bounds(sgs, scmap[ord(base_char)])
    withh = bounds(sgs, sname)
    s = k_horn
    cb = bounds(cgs, ccmap[ord(base_char)])
    horn = "vn.horn.case" if base_char.isupper() else "vn.horn"
    hb_ = bounds(cgs, horn)
    right = min(cb[2] + (withh[2] - plain[2]) * s, 1190)
    top = cb[3] + (withh[3] - plain[3]) * s
    return name, [(ccmap[ord(base_char)], 0, 0), (horn, round(right - hb_[2]), round(top - hb_[3]))]


letters = {}
TONES = {"acute": "́", "grave": "̀", "hook": "̉", "tilde": "̃", "dot": "̣"}
import unicodedata

for lower in "aeiouy":
    for upper in (False, True):
        bc = lower.upper() if upper else lower
        suf = ".case" if upper else ""
        dx = accent_dx(bc, upper)
        bases = [(bc, None)]
        if lower in "aeo":
            bases.append((bc, "circ"))
        if lower == "a":
            bases.append((bc, "breve"))
        if lower in "ou":
            bases.append((bc, "horn"))
        for b, mod in bases:
            for tone, comb in TONES.items():
                seq = b + {"circ": "̂", "breve": "̆", "horn": "̛", None: ""}[mod] + comb
                ch = unicodedata.normalize("NFC", seq)
                if len(ch) != 1:
                    continue
                if ord(ch) in ccmap:
                    continue  # already in Fira Code
                comps = []
                if mod == "horn":
                    hname, hcomps = horn_base(b)
                    comps = hcomps
                    hcb = bounds(cgs, ccmap[ord(b)])
                elif mod == "circ" and tone != "dot":
                    comps = [(base_glyph(b), 0, 0), (f"vn.circ.{tone}{suf}", dx, 0)]
                elif mod == "breve" and tone != "dot":
                    comps = [(base_glyph(b), 0, 0), ("vn.breve" + suf, dx, 0)]
                elif mod in ("circ", "breve"):  # dot below: reuse â / ă glyph
                    comps = [(ccmap[ord(unicodedata.normalize("NFC", b + ("̂" if mod == "circ" else "̆")))], 0, 0)]
                else:
                    comps = [(base_glyph(b) if tone != "dot" else ccmap[ord(b)], 0, 0)]
                if tone == "dot":
                    comps.append(("vn.dotbelow", round(dot_dx(b)), 0))
                elif mod == "circ":
                    comps.append((f"vn.circ{tone}{suf}", dx, 0))
                elif mod == "breve":
                    comps.append((f"vn.breve{tone}{suf}", dx, 0))
                else:
                    mark = {"acute": "acute", "grave": "grave", "tilde": "tilde", "hook": "vn.hook"}[tone] + suf
                    comps.append((mark, dx, 0))
                letters[ch] = comps

# horn letters without tone
for b in "ouOU":
    hname, hcomps = horn_base(b)
    letters[chr({"uni01A1": 0x1A1, "uni01B0": 0x1B0, "uni01A0": 0x1A0, "uni01AF": 0x1AF}[hname])] = hcomps

# horn + tone: put tone on horn letter (tone centred like on o/u)
for ch, comps in list(letters.items()):
    if comps and comps[0][0] in ("o", "u", "O", "U") and len(comps) == 3 and comps[1][0].startswith("vn.horn"):
        pass  # already includes horn + tone

created = []
for ch, comps in sorted(letters.items()):
    if ord(ch) in ccmap:
        continue
    name = "uni%04X" % ord(ch)
    g = Glyph()
    g.numberOfContours = -1
    g.components = []
    for i, (gn, x, y) in enumerate(comps):
        c = GlyphComponent()
        c.glyphName = gn
        c.x, c.y = int(round(x)), int(round(y))
        # same flags as Fira Code's own composites (e.g. aacute):
        # base = ROUND_XY_TO_GRID|USE_MY_METRICS (0x204), marks = ROUND_XY_TO_GRID (0x4).
        # Do NOT set OVERLAP_COMPOUND: Windows' rasterizer then switches to a
        # different (heavier, blurrier) rendering mode for the whole glyph.
        c.flags = 0x204 if i == 0 else 0x4
        g.components.append(c)
    add_glyph(name, g)
    for table in code["cmap"].tables:
        if table.isUnicode():
            table.cmap[ord(ch)] = name
    created.append(ch)

# combining marks for decomposed input (zero-width, drawn over previous cell)
for cp, src in ((0x0309, "vn.hook"), (0x0323, "vn.dotbelow"), (0x031B, None)):
    if cp in ccmap:
        continue
    name = "uni%04X" % cp
    if src is None:  # horn: put it at the right shoulder of a lowercase o
        _, hc = horn_base("o")
        src_name, dx, dy = hc[1]
    else:
        src_name, dx, dy = src, 0, 0
    pen = TTGlyphPen(None)
    cgs2 = code.getGlyphSet()
    cgs2[src_name].draw(TransformPen(pen, (1, 0, 0, 1, dx - ADV, dy)))
    g = pen.glyph()
    add_glyph(name, g)
    code["hmtx"][name] = (0, g.xMin)
    for table in code["cmap"].tables:
        if table.isUnicode():
            table.cmap[cp] = name

# GDEF: new letters are bases, combining marks are marks
gdef = code["GDEF"].table
if gdef.GlyphClassDef:
    cd = gdef.GlyphClassDef.classDefs
    for ch in created:
        cd["uni%04X" % ord(ch)] = 1
    for cp in (0x0309, 0x0323, 0x031B):
        cd["uni%04X" % cp] = 3

# ---------------------------------------------------------------- names
def rename(s):
    return s.replace("Fira Code", "Fira Code VN").replace("FiraCode", "FiraCodeVN")


for rec in code["name"].names:
    if rec.nameID in (1, 3, 4, 6, 16, 17, 21, 22):
        rec.string = rename(rec.toUnicode())
    if rec.nameID == 5:
        rec.string = rec.toUnicode() + "; Vietnamese glyphs added (hook/horn from Fira Sans, OFL)"

code["head"].fontRevision = code["head"].fontRevision
if "DSIG" in code:
    del code["DSIG"]
code.save(out_path)
print(f"{out_path}: +{len(created)} letters", "".join(created))

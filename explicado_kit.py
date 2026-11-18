"""Kit de dibujo de los reels «explicados» de AC: animación vectorial con Skia con los colores de ArquitecturaConfidencial
(línea de neón AMARILLA sobre tinta, papel para el texto y coral para «el problema»). Los nombres ORO/ORO_L/ORO_D se
conservan del motor original: aquí son el amarillo de la marca, su tono claro y su tono apagado. Aquí están los utensilios (trazos con brillo, tipografía,
figuras) y las ESCENAS: decorados animados que explicado.py monta según el guion.

Cada escena es una función draw(c, st): c = lienzo de Skia (1080×1920), st = estado (tiempo, parámetros del golpe actual
y del anterior, y cuánto hace que cambió cada parámetro), para que todo entre animado y nada salte.
"""
import math, os, random

import skia

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
ORO, ORO_L, ORO_D = (255, 204, 0), (255, 228, 120), (150, 122, 24)          # amarillo AC, claro y apagado
CREMA, NEGRO, CARBON, CARBON_L = (246, 243, 236), (9, 10, 13), (20, 23, 29), (36, 41, 51)   # papel y tinta de AC
CORAL, CORAL_D = (255, 96, 82), (128, 44, 38)
COLOR = {"oro": ORO, "coral": CORAL, "crema": CREMA, "oro_l": ORO_L}
_TF = {}


def tf(bold=True):
    k = "bold" if bold else "regular"
    if k not in _TF:
        _TF[k] = skia.Typeface.MakeFromFile(os.path.join(HERE, "fonts", f"texgyreadventor-{k}.otf"))
    return _TF[k]


def col(rgb, a=1.0):
    return skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(255 * max(0.0, min(1.0, a))))


def mixc(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(t):
    t = clamp(t); return 1 - (1 - t) ** 3


def eio(t):
    t = clamp(t); return 3 * t * t - 2 * t * t * t


def eob(t, s=1.9):
    """Entrada con un pequeño rebote."""
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def lerp(a, b, t):
    return a + (b - a) * t


def stroke(rgb, w=6, a=1.0):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w, Color=col(rgb, a))
    p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def fill(rgb, a=1.0):
    return skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=col(rgb, a))


def line(c, x0, y0, x1, y1, rgb=ORO, w=6, a=1.0):
    c.drawLine(x0, y0, x1, y1, stroke(rgb, w, a))


def rrect(c, x, y, w, h, r=18, f=CARBON, s=ORO, sw=5, a=1.0, fa=None):
    rc = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    if f is not None:
        c.drawRRect(rc, fill(f, a if fa is None else fa))
    if s is not None and sw:
        c.drawRRect(rc, stroke(s, sw, a))


def circle(c, x, y, r, f=CARBON, s=ORO, sw=5, a=1.0):
    if f is not None:
        c.drawCircle(x, y, r, fill(f, a))
    if s is not None and sw:
        c.drawCircle(x, y, r, stroke(s, sw, a))


def capsule(c, x0, y0, x1, y1, w, f=CARBON_L, s=ORO, sw=5, a=1.0):
    """Miembro redondeado: relleno con contorno (el contorno es un trazo más ancho por debajo)."""
    if s is not None and sw:
        c.drawLine(x0, y0, x1, y1, stroke(s, w + 2 * sw, a))
    c.drawLine(x0, y0, x1, y1, stroke(f, w, a))


def path_of(pts, close=False):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def poly(c, pts, f=CARBON, s=ORO, sw=5, a=1.0, close=True):
    p = path_of(pts, close)
    if f is not None:
        c.drawPath(p, fill(f, a))
    if s is not None and sw:
        c.drawPath(p, stroke(s, sw, a))


def trazo(c, pts, t, rgb=ORO, w=6, a=1.0, close=False):
    """Línea que se dibuja sola: t = 0..1 de su longitud."""
    if t <= 0:
        return
    p = path_of(pts, close)
    if t < 1:
        L = skia.PathMeasure(p, False).getLength()
        pa = stroke(rgb, w, a)
        pa.setPathEffect(skia.DashPathEffect.Make([L * t, L], 0))
        c.drawPath(p, pa)
    else:
        c.drawPath(p, stroke(rgb, w, a))


def text(c, s, x, y, size=48, rgb=CREMA, a=1.0, bold=True, align="c", outline=0, ocol=NEGRO, track=0.0):
    """Texto en una línea; y = línea base. align: c/l/r. Devuelve el ancho."""
    f = skia.Font(tf(bold), size)
    f.setSubpixel(True)
    if track:
        ws = [f.measureText(ch) for ch in s]
        w = sum(ws) + track * size * (len(s) - 1)
        x0 = x - w / 2 if align == "c" else x - w if align == "r" else x
        for ch, cw in zip(s, ws):
            if outline:
                p = stroke(ocol, outline, a); c.drawString(ch, x0, y, f, p)
            c.drawString(ch, x0, y, f, fill(rgb, a)); x0 += cw + track * size
        return w
    w = f.measureText(s)
    x0 = x - w / 2 if align == "c" else x - w if align == "r" else x
    if outline:
        c.drawString(s, x0, y, f, stroke(ocol, outline, a))
    c.drawString(s, x0, y, f, fill(rgb, a))
    return w


def tw(s, size, bold=True):
    return skia.Font(tf(bold), size).measureText(s)


def wrap(s, size, maxw, bold=True):
    out, cur = [], ""
    for w_ in s.split():
        t = (cur + " " + w_).strip()
        if cur and tw(t, size, bold) > maxw:
            out.append(cur); cur = w_
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


def fit(s, size, maxw, max_lines=2, bold=True, min_size=40):
    while size > min_size:
        ls = wrap(s, size, maxw, bold)
        if len(ls) <= max_lines:
            return size, ls
        size -= 4
    return size, wrap(s, size, maxw, bold)


# ------------------------------------------------------------------ estado de una escena
class St:
    """Lo que una escena necesita saber en un fotograma."""

    def __init__(self, t, beats, k, u, seed=0):
        self.t, self.beats, self.k, self.u, self.seed = t, beats, k, u, seed
        self.p = beats[k]["P"]                              # parámetros acumulados hasta este golpe
        self.prev = beats[k - 1]["P"] if k > 0 else self.p
        self.dur = beats[k]["t1"] - beats[k]["t0"]

    def get(self, key, default=None):
        return self.p.get(key, default)

    def mix(self, key, default=0.0, d=0.7):
        """Valor numérico que pasa suave del golpe anterior a este."""
        a = self.prev.get(key, default); b = self.p.get(key, default)
        try:
            return lerp(float(a), float(b), eio(self.u / d))
        except (TypeError, ValueError):
            return b

    def since(self, key):
        """Segundos desde que este parámetro tomó su valor actual (para animar su entrada)."""
        v = self.p.get(key); k = self.k
        while k > 0 and self.beats[k - 1]["P"].get(key) == v:
            k -= 1
        return self.t - self.beats[k]["t0"]

    def was(self, key, default=None):
        return self.prev.get(key, default) if self.k > 0 else default


# ------------------------------------------------------------------ fondo
_FONDO = {}


def _fondo_fijo(tono):
    """Degradado y viñeta (no cambian): se pintan una vez y se reutilizan en cada fotograma."""
    if tono not in _FONDO:
        sf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        c = sf.getCanvas(); c.clear(col(NEGRO))
        top = (17, 20, 28) if tono == "noche" else (22, 26, 34)
        sh = skia.GradientShader.MakeLinear([(0, 0), (0, H)], [col(top), col(NEGRO), col((11, 13, 17))], [0, 0.55, 1])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
        vg = skia.GradientShader.MakeRadial((W / 2, H * 0.52), H * 0.72, [col(NEGRO, 0), col(NEGRO, 0.72)], [0.55, 1])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=vg))
        _FONDO[tono] = sf.makeImageSnapshot()
    return _FONDO[tono]


def fondo(c, t, tono="noche", seed=0):
    """Negro cálido con cuadrícula fina, viñeta y motas doradas que flotan."""
    c.drawImage(_fondo_fijo(tono), 0, 0)
    g = stroke(ORO, 1, 0.045)
    off = (t * 6) % 60
    for x in range(0, W + 60, 60):
        c.drawLine(x, 0, x, H, g)
    for y in range(-60, H + 60, 60):
        c.drawLine(0, y + off, W, y + off, g)
    r = random.Random(seed)
    for i in range(26):
        x = r.uniform(0, W); y0 = r.uniform(0, H); sp = r.uniform(8, 26); ph = r.uniform(0, 6.28)
        y = (y0 - t * sp) % H
        a = 0.10 + 0.10 * math.sin(t * 1.3 + ph)
        c.drawCircle(x + 12 * math.sin(t * 0.5 + ph), y, r.uniform(1.5, 3.5), fill(ORO_L, a))


def halo(c, x, y, r, rgb=ORO, a=0.22):
    sh = skia.GradientShader.MakeRadial((x, y), r, [col(rgb, a), col(rgb, 0)])
    c.drawCircle(x, y, r, skia.Paint(Shader=sh, AntiAlias=True))


# ------------------------------------------------------------------ iconos (centrados en 0,0, caben en ±s)
def ic_doc(c, s, rgb=ORO, a=1.0, f=CARBON, lines=3):
    w, h = s * 0.74, s
    poly(c, [(-w, -h), (w * 0.45, -h), (w, -h * 0.55), (w, h), (-w, h)], f, rgb, max(3, s * 0.09), a)
    c.drawPath(path_of([(w * 0.45, -h), (w * 0.45, -h * 0.55), (w, -h * 0.55)]), stroke(rgb, max(2.5, s * 0.07), a))
    for i in range(lines):
        y = -h * 0.18 + i * h * 0.36
        line(c, -w * 0.55, y, w * (0.55 if i < lines - 1 else 0.1), y, rgb, max(2.5, s * 0.07), a * 0.8)


def ic_casa(c, s, rgb=ORO, a=1.0, f=CARBON):
    poly(c, [(-s * 0.8, s), (-s * 0.8, -s * 0.1), (0, -s), (s * 0.8, -s * 0.1), (s * 0.8, s)], f, rgb, max(3, s * 0.1), a)
    rrect(c, -s * 0.2, s * 0.25, s * 0.4, s * 0.75, 3, None, rgb, max(2.5, s * 0.08), a)


def ic_persona(c, s, rgb=ORO, a=1.0, f=CARBON_L):
    sw = max(3, s * 0.1)
    p = skia.Path()
    p.moveTo(-s * 0.78, s); p.lineTo(-s * 0.78, s * 0.35)
    p.cubicTo(-s * 0.78, -s * 0.2, s * 0.78, -s * 0.2, s * 0.78, s * 0.35); p.lineTo(s * 0.78, s); p.close()
    c.drawPath(p, fill(f, a)); c.drawPath(p, stroke(rgb, sw, a))
    circle(c, 0, -s * 0.52, s * 0.4, f, rgb, sw, a)


def ic_moneda(c, s, rgb=ORO, a=1.0, f=CARBON):
    circle(c, 0, 0, s, f, rgb, max(3, s * 0.12), a)
    text(c, "€", 0, s * 0.42, s * 1.15, rgb, a)


def ic_check(c, s, rgb=ORO, a=1.0, t=1.0):
    trazo(c, [(-s * 0.6, 0), (-s * 0.15, s * 0.5), (s * 0.7, -s * 0.5)], t, rgb, max(5, s * 0.22), a)


def ic_cruz(c, s, rgb=CORAL, a=1.0, t=1.0):
    trazo(c, [(-s * 0.55, -s * 0.55), (s * 0.55, s * 0.55)], clamp(t * 2), rgb, max(5, s * 0.22), a)
    trazo(c, [(s * 0.55, -s * 0.55), (-s * 0.55, s * 0.55)], clamp(t * 2 - 1), rgb, max(5, s * 0.22), a)


def ic_lapiz(c, s, rgb=ORO, a=1.0):
    c.save(); c.rotate(40)
    rrect(c, -s * 0.18, -s * 0.9, s * 0.36, s * 1.35, 4, CARBON, rgb, max(3, s * 0.09), a)
    poly(c, [(-s * 0.18, s * 0.45), (s * 0.18, s * 0.45), (0, s * 0.95)], CARBON, rgb, max(3, s * 0.09), a)
    c.restore()


def ic_planos(c, s, rgb=ORO, a=1.0):
    for i, d in enumerate((0.24, 0.0, -0.24)):
        c.save(); c.translate(d * s, d * s * 0.8)
        rrect(c, -s * 0.72, -s * 0.72, s * 1.44, s * 1.44, 6, CARBON, rgb, max(3, s * 0.08), a * (0.5 + 0.25 * i))
        c.restore()
    c.save(); c.translate(-0.24 * s, -0.19 * s)
    line(c, -s * 0.4, -s * 0.3, s * 0.4, -s * 0.3, rgb, max(2.5, s * 0.07), a)
    line(c, -s * 0.4, 0, s * 0.1, 0, rgb, max(2.5, s * 0.07), a)
    line(c, -s * 0.4, -s * 0.3, -s * 0.4, s * 0.35, rgb, max(2.5, s * 0.07), a)
    c.restore()


def ic_firma(c, s, rgb=ORO, a=1.0, t=1.0):
    pts = [(-s * 0.85, s * 0.1), (-s * 0.6, -s * 0.5), (-s * 0.4, s * 0.3), (-s * 0.15, -s * 0.6), (s * 0.05, s * 0.25),
           (s * 0.3, -s * 0.2), (s * 0.5, s * 0.15), (s * 0.85, -s * 0.05)]
    p = skia.Path(); p.moveTo(*pts[0])
    for i in range(1, len(pts) - 1, 2):
        p.quadTo(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
    pa = stroke(rgb, max(4, s * 0.1), a)
    if t < 1:
        L = skia.PathMeasure(p, False).getLength(); pa.setPathEffect(skia.DashPathEffect.Make([L * t, L], 0))
    c.drawPath(p, pa)
    line(c, -s * 0.9, s * 0.62, s * 0.9, s * 0.62, rgb, max(2.5, s * 0.06), a * 0.6)


def ic_reloj(c, s, hora=9.0, rgb=ORO, a=1.0, f=CARBON):
    circle(c, 0, 0, s, f, rgb, max(4, s * 0.09), a)
    for i in range(12):
        an = math.radians(i * 30)
        line(c, math.sin(an) * s * 0.8, -math.cos(an) * s * 0.8, math.sin(an) * s * 0.9, -math.cos(an) * s * 0.9, rgb,
             max(2, s * 0.045), a * 0.7)
    ah = math.radians((hora % 12) * 30); am = math.radians((hora * 60 % 60) * 6)
    line(c, 0, 0, math.sin(ah) * s * 0.5, -math.cos(ah) * s * 0.5, CREMA, max(4, s * 0.1), a)
    line(c, 0, 0, math.sin(am) * s * 0.74, -math.cos(am) * s * 0.74, CREMA, max(3, s * 0.065), a)
    c.drawCircle(0, 0, max(3, s * 0.07), fill(rgb, a))


def ic_calendario(c, s, rgb=ORO, a=1.0, f=CARBON):
    rrect(c, -s * 0.85, -s * 0.7, s * 1.7, s * 1.55, s * 0.14, f, rgb, max(3, s * 0.09), a)
    line(c, -s * 0.85, -s * 0.3, s * 0.85, -s * 0.3, rgb, max(3, s * 0.08), a)
    for x in (-0.42, 0.42):
        line(c, x * s, -s * 0.92, x * s, -s * 0.55, rgb, max(3, s * 0.1), a)


ICONOS = {"doc": ic_doc, "casa": ic_casa, "persona": ic_persona, "moneda": ic_moneda, "lapiz": ic_lapiz,
          "planos": ic_planos, "firma": ic_firma, "calendario": ic_calendario}


def icono(c, nombre, x, y, s, rgb=ORO, a=1.0, sc=1.0, **kw):
    c.save(); c.translate(x, y)
    if sc != 1.0:
        c.scale(sc, sc)
    if nombre == "reloj":
        ic_reloj(c, s, kw.get("hora", 9.0), rgb, a)
    elif nombre == "check":
        ic_check(c, s, rgb, a, kw.get("t", 1.0))
    elif nombre == "cruz":
        ic_cruz(c, s, rgb, a, kw.get("t", 1.0))
    else:
        ICONOS.get(nombre, ic_doc)(c, s, rgb, a)
    c.restore()


# ------------------------------------------------------------------ plano de vivienda (original, paramétrico)
# Coordenadas en una caja 0..100 × 0..130. Muros exteriores, tabiques, puertas (arco) y capas de instalaciones.
PL_MUROS = [[(0, 0), (100, 0), (100, 130), (0, 130), (0, 0)]]
PL_TABIQUES = [[(0, 52), (38, 52)], [(52, 52), (100, 52)], [(58, 0), (58, 40)], [(58, 52), (58, 96)], [(58, 108), (58, 130)],
               [(0, 92), (24, 92)], [(36, 92), (58, 92)], [(78, 52), (78, 86)], [(78, 86), (100, 86)]]
PL_PUERTAS = [((38, 52), 14, 0), ((58, 40), 12, 90), ((24, 92), 12, 0), ((58, 96), 12, 90)]
PL_VENTANAS = [[(14, 0), (42, 0)], [(70, 0), (92, 0)], [(100, 14), (100, 40)], [(0, 104), (0, 122)], [(70, 130), (92, 130)]]
PL_MOBIL = [("rect", 8, 12, 30, 16), ("rect", 66, 8, 26, 12), ("circ", 82, 30, 7), ("rect", 6, 62, 22, 22), ("rect", 62, 60, 12, 22),
            ("rect", 84, 58, 12, 10), ("circ", 89, 74, 4), ("rect", 8, 100, 12, 24), ("rect", 66, 112, 26, 12)]
PL_FONTA = [[(89, 74), (89, 96), (62, 96)], [(89, 63), (97, 63), (97, 96), (89, 96)], [(62, 71), (62, 96), (62, 124), (78, 124)]]
PL_ELEC = [[(50, 127), (50, 100), (20, 100)], [(50, 100), (50, 46), (20, 46), (20, 20)], [(50, 46), (80, 46), (80, 20)],
           [(80, 46), (90, 46), (90, 56)]]
PL_ELEC_PT = [(20, 100), (20, 20), (80, 20), (90, 56), (20, 46), (50, 72), (30, 72)]
PL_ESTR = [(0, 0), (58, 0), (100, 0), (0, 52), (58, 52), (100, 52), (0, 92), (58, 92), (100, 86), (0, 130), (58, 130), (100, 130)]
PL_COTAS = [((0, -9), (58, -9)), ((58, -9), (100, -9)), ((-9, 0), (-9, 52)), ((-9, 52), (-9, 130))]


def plano(c, x, y, s, t_muros=1.0, capas=(), t_capa=None, a=1.0, rgb=ORO, fino=False):
    """Dibuja el plano con (x, y) = esquina superior izquierda y s = píxeles por unidad. t_muros: 0..1 (se dibuja solo).
    capas: nombres visibles; t_capa: {nombre: 0..1} para la entrada de cada capa."""
    t_capa = t_capa or {}
    P = lambda q: (x + q[0] * s, y + q[1] * s)
    wm = max(3, s * (0.9 if fino else 1.5))
    if "relleno" in capas or True:
        c.drawRect(skia.Rect.MakeXYWH(x, y, 100 * s, 130 * s), fill(CARBON, a * 0.55 * clamp(t_muros * 2)))
    for m in PL_MUROS:
        trazo(c, [P(q) for q in m], clamp(t_muros * 1.6), rgb, wm, a)
    for i, m in enumerate(PL_TABIQUES):
        trazo(c, [P(q) for q in m], clamp(t_muros * 3 - 0.9 - i * 0.12), rgb, wm * 0.62, a)
    tv = clamp(t_muros * 3 - 1.6)
    for m in PL_VENTANAS:
        if tv > 0:
            a_, b_ = P(m[0]), P(m[1])
            c.drawLine(a_[0], a_[1], b_[0], b_[1], stroke(NEGRO, wm * 0.5, a * tv))
            c.drawLine(a_[0], a_[1], b_[0], b_[1], stroke(CREMA, max(1.5, wm * 0.2), a * tv))
    for (q, r, rot) in PL_PUERTAS:
        if tv > 0:
            px, py = P(q)
            rc = skia.Rect.MakeXYWH(px - r * s, py - r * s, 2 * r * s, 2 * r * s)
            c.drawArc(rc, rot, 90 * tv, False, stroke(rgb, max(1.5, wm * 0.22), a * 0.7))
            an = math.radians(rot + 90 * tv)
            c.drawLine(px, py, px + math.cos(an) * r * s, py + math.sin(an) * r * s, stroke(rgb, max(2, wm * 0.3), a * 0.9))
    tm = clamp(t_muros * 3 - 1.9)
    if tm > 0 and not fino:
        for m in PL_MOBIL:
            if m[0] == "rect":
                rrect(c, x + m[1] * s, y + m[2] * s, m[3] * s, m[4] * s, s * 1.2, None, ORO_D, max(1.5, wm * 0.2), a * tm)
            else:
                c.drawCircle(x + m[1] * s, y + m[2] * s, m[3] * s, stroke(ORO_D, max(1.5, wm * 0.2), a * tm))
    if "cotas" in capas:
        t = t_capa.get("cotas", 1.0)
        for (q0, q1) in PL_COTAS:
            a0, a1 = P(q0), P(q1)
            trazo(c, [a0, a1], t, CREMA, max(1.5, wm * 0.18), a * 0.8)
            for q in (a0, a1):
                c.drawLine(q[0] - s * 1.6, q[1] + s * 1.6, q[0] + s * 1.6, q[1] - s * 1.6, stroke(CREMA, max(1.5, wm * 0.18), a * 0.8 * t))
    if "estructura" in capas:
        t = t_capa.get("estructura", 1.0)
        for i, q in enumerate(PL_ESTR):
            k = eob(clamp(t * 2.2 - i * 0.09))
            if k > 0:
                px, py = P(q)
                c.drawRect(skia.Rect.MakeXYWH(px - s * 2.6 * k, py - s * 2.6 * k, s * 5.2 * k, s * 5.2 * k), fill(CREMA, a))
    if "fontaneria" in capas:
        t = t_capa.get("fontaneria", 1.0)
        for i, m in enumerate(PL_FONTA):
            trazo(c, [P(q) for q in m], clamp(t * 1.8 - i * 0.3), CORAL, max(3, wm * 0.5), a)
    if "electricidad" in capas:
        t = t_capa.get("electricidad", 1.0)
        for i, m in enumerate(PL_ELEC):
            trazo(c, [P(q) for q in m], clamp(t * 1.8 - i * 0.25), ORO_L, max(3, wm * 0.42), a)
        for i, q in enumerate(PL_ELEC_PT):
            k = eob(clamp(t * 2.4 - 0.8 - i * 0.1))
            if k > 0:
                px, py = P(q); c.drawCircle(px, py, s * 2.0 * k, fill(NEGRO, a)); c.drawCircle(px, py, s * 2.0 * k, stroke(ORO_L, max(2, wm * 0.3), a))


# ------------------------------------------------------------------ figura (de espaldas, sentada)
def figura(c, x, y, s=1.0, pose="trabaja", t=0.0, rgb=ORO, a=1.0, mezcla=None):
    """Persona de espaldas, sentada (cabeza, hombros, brazos y respaldo de la silla), con el centro de los hombros en
    (x, y). pose: trabaja, agobio, telefono, celebra, mira. mezcla = (pose_anterior, 0..1) para pasar suave de una a otra."""
    def ang(p):
        # (brazo izq: hombro->codo, codo->mano), (brazo dcho), inclinación de la cabeza, caída de hombros
        if p == "agobio":
            return ((-122, -58), (-58, -122), 9, 14)
        if p == "telefono":
            return ((168, -64), (-48, -128), -9, 0)
        if p == "celebra":
            return ((-124, -100), (-56, -80), -5, -12)
        if p == "mira":
            return ((120, 84), (60, 96), 0, 2)
        w = math.sin(t * 11) * 3.5
        return ((166 + w, -66 - w), (14 - w, -114 + w), 3 + math.sin(t * 1.2) * 2, 4)
    A = ang(pose)
    if mezcla and mezcla[1] < 1:
        B = ang(mezcla[0]); k = eio(mezcla[1])
        A = (tuple(lerp(B[0][i], A[0][i], k) for i in range(2)), tuple(lerp(B[1][i], A[1][i], k) for i in range(2)),
             lerp(B[2], A[2], k), lerp(B[3], A[3], k))
    c.save(); c.translate(x, y + A[3] * s); c.scale(s, s)
    resp = math.sin(t * 1.6) * 2.5
    # espalda
    p = skia.Path()
    p.moveTo(-126, 420); p.lineTo(-126, 44)
    p.cubicTo(-126, -16 - resp, 126, -16 - resp, 126, 44); p.lineTo(126, 420)
    c.drawPath(p, fill(CARBON_L, a)); c.drawPath(p, stroke(rgb, 6, a))
    # respaldo de la silla, por delante de la espalda
    rrect(c, -164, 150, 328, 420, 44, CARBON, ORO_D, 6, a)
    line(c, -100, 210, 100, 210, ORO_D, 4, a * 0.7)
    # brazos
    for lado, (a1, a2) in ((-1, A[0]), (1, A[1])):
        sx, sy = lado * 110, 36
        ex, ey = sx + math.cos(math.radians(a1)) * 112, sy + math.sin(math.radians(a1)) * 112
        hx, hy = ex + math.cos(math.radians(a2)) * 112, ey + math.sin(math.radians(a2)) * 112
        capsule(c, sx, sy, ex, ey, 46, CARBON_L, rgb, 6, a)
        capsule(c, ex, ey, hx, hy, 40, CARBON_L, rgb, 6, a)
        circle(c, hx, hy, 25, CARBON_L, rgb, 6, a)
    # cuello y cabeza
    c.save(); c.rotate(A[2], 0, -10)
    capsule(c, 0, -6, 0, -40, 40, CARBON_L, rgb, 6, a)
    circle(c, 0, -104, 70, CARBON_L, rgb, 6, a)
    c.restore()
    c.restore()

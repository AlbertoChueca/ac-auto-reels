"""Piezas comunes de render (vídeo + audio) para los reels de AC · ArquitecturaConfidencial.

Todo se dibuja a 1080x1920. Marca AC (para estudiantes de arquitectura): tinta casi negra, papel de croquis y amarillo
rotulador de acento (el subrayador de las láminas). Tipografía: TeX Gyre Adventor (licencia GUST en fonts/).
Sonido 100 % tonal (sin ruido blanco) + filtro final `dehiss` como red de seguridad.
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 25, 24000
OUT_W, OUT_H = 720, 1280
SAFE_TOP, SAFE_BOTTOM = 250, 1500      # la interfaz de Instagram/TikTok tapa arriba, abajo y la columna derecha
F_BOLD = os.path.join(HERE, "fonts", "texgyreadventor-bold.otf")
F_REG = os.path.join(HERE, "fonts", "texgyreadventor-regular.otf")
F_ITAL = os.path.join(HERE, "fonts", "texgyreadventor-italic.otf")
F900, F800 = F_BOLD, F_REG              # titulares / textos (nombres heredados del motor de TCAE)

# ---- marca UDA (colores medidos en los documentos de UDA)
CARBON = (43, 43, 43); CARBON_D = (30, 30, 30); PIEDRA = (243, 240, 236); PIEDRA_D = (216, 210, 202)
BRONCE = (122, 106, 88); ARENA = (201, 185, 166); GRIS = (107, 107, 107); WHITE = (255, 255, 255)
NEGRO = (12, 12, 12); NEGRO_C = (24, 23, 21); ORO = (200, 164, 93); ORO_D = (150, 120, 64); CREMA = (242, 236, 224)
# ---- marca AC: tinta, papel de croquis y amarillo rotulador (lo usan visual.py y las portadas)
TINTA = (14, 16, 20); PAPEL = (246, 243, 236); AMARILLO = (255, 204, 0); AMARILLO_D = (196, 156, 0)
TERRACOTA = (156, 74, 58)              # solo para marcar la opción trampa (sobrio, no rojo chillón)
INK, PAPER, MUTED, OK = CARBON, WHITE, GRIS, BRONCE
BORDER = (226, 220, 212)

_FONTS = {}


def font(path, size):
    k = (path, int(size))
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(path, int(size))
    return _FONTS[k]


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eob(t, s=1.7):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1
def eo(t): t = clamp(t); return 1 - (1 - t) ** 3
def eio(t): t = clamp(t); return 3 * t * t - 2 * t * t * t


def spaced(text, path, size, color, tracking=0.18):
    """Texto con espaciado entre letras (logotipo, etiquetas en versalitas)."""
    f = font(path, size); gap = size * tracking
    w = sum(f.getlength(c) for c in text) + gap * (len(text) - 1)
    bb = f.getbbox("ÁgÑ")
    top = max(0, -bb[1]) + 2                     # hueco para las tildes de las mayúsculas (Á, É...)
    im = Image.new("RGBA", (int(w) + 4, bb[3] + top + 6), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 0
    for c in text:
        d.text((x, top), c, font=f, fill=color); x += f.getlength(c) + gap
    return im


def logo(size=120, color=PAPEL, sub=AMARILLO, align="center"):
    """Logotipo de AC: «ARQUITECTURA» espaciado con «CONFIDENCIAL» en amarillo rotulador debajo."""
    top = spaced("ARQUITECTURA", F_BOLD, size * 0.5, color, 0.16)
    bot = spaced("CONFIDENCIAL", F_REG, max(12, size * 0.32), sub, 0.42)
    w = max(top.width, bot.width)
    im = Image.new("RGBA", (w, top.height + bot.height), (0, 0, 0, 0))
    xa = {"center": lambda i: (w - i.width) // 2, "right": lambda i: w - i.width, "left": lambda i: 0}[align]
    im.alpha_composite(top, (xa(top), 0)); im.alpha_composite(bot, (xa(bot), top.height))
    return im


def rule(w, color=BRONCE, h=6):
    im = Image.new("RGBA", (int(w), int(h)), tuple(color[:3]) + (255,))
    return im


# ------------------------------------------------------------------ texto
def wrap(words, fnt, maxw, space=None):
    """[(word, x, line)] + n_lines: reparto en líneas sin cortar palabras."""
    space = space or fnt.getlength(" ")
    out, x, line = [], 0.0, 0
    for w in words:
        wl = fnt.getlength(w)
        if x and x + wl > maxw:
            line += 1; x = 0.0
        out.append((w, x, line)); x += wl + space
    return out, line + 1


def fit_font(text, path, size, maxw, max_lines, min_size=34):
    """Tamaño de letra más grande con el que `text` (o su lista de palabras) cabe en max_lines líneas."""
    words = text if isinstance(text, list) else text.split()
    while size > min_size:
        _, n = wrap(words, font(path, size), maxw)
        if n <= max_lines:
            break
        size -= 2
    return size


def text_block(text, path, size, maxw, color=INK, lit=None, dim=None, align="left", line_gap=1.22):
    """Bloque de texto. lit = nº de palabras ya dichas (karaoke): esas van en `color`, el resto en `dim`."""
    words = text.split(); f = font(path, size)
    pos, n = wrap(words, f, maxw)
    lh = int(size * line_gap)
    widths = {}
    for w, x, ln in pos:
        widths[ln] = x + f.getlength(w)
    top = accent_pad(f)                                     # sitio para la tilde de Á, É, Ó (si no, se corta)
    im = Image.new("RGBA", (int(maxw) + 8, lh * n + int(size * 0.35) + top), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k, (w, x, ln) in enumerate(pos):
        off = 0 if align == "left" else (maxw - widths[ln]) / 2
        c = color if (lit is None or k < lit) else (dim or MUTED)
        d.text((x + off, ln * lh + top), w, font=f, fill=c)
    return im


def accent_pad(f):
    """Píxeles que sobresalen por arriba las mayúsculas con tilde (la fuente las dibuja por encima de la línea)."""
    return max(0, -f.getbbox("ÁÉÍÓÚÑ")[1]) + 2


def word_img(word, size, color=WHITE, stroke=0, path=None, stroke_col=CARBON, shadow=False):
    """Palabra grande (ganchos y titulares). Estilo editorial: sin contorno salvo sobre imagen."""
    fo = font(path or F900, size)
    w = int(fo.getlength(word)) + 2 * stroke + 20
    top = accent_pad(fo)
    im = Image.new("RGBA", (w, int(size * 1.4) + 2 * stroke + top), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shadow:
        d.text((stroke + 10 + 3, stroke + 5 + top), word, font=fo, fill=(0, 0, 0, 110))
    d.text((stroke + 10, stroke + top), word, font=fo, fill=color, stroke_width=stroke, stroke_fill=stroke_col)
    return im


def headline(text, size=104, maxw=940, max_lines=3, color=WHITE, hot=ARENA, hot_words=(), stroke=0, stroke_col=CARBON,
             shadow=False, upper=False, align="center"):
    """Titular de varias líneas (sin contorno salvo sobre imagen); palabras de hot_words en color `hot`."""
    text = text.upper() if upper else text
    words = []
    for w in text.split():                                  # «2.712 €», «20 %», «150 m²»: la unidad nunca va sola
        if words and w.strip(".,:;!?") in ("€", "%", "m²", "h"):
            words[-1] += " " + w
        else:
            words.append(w)
    size = fit_font(words, F900, size, maxw - 40, max_lines, 54)
    sp = font(F900, size).getlength(" ")
    ims = [word_img(w, size, hot if w.split(" ")[0].strip(".,!?¿¡:").lower() in hot_words else color, stroke, None,
                    stroke_col, shadow) for w in words]
    adv = lambda im: im.width - 20 - 2 * stroke + sp
    lines, cur, cw = [], [], 0
    for im in ims:
        if cur and cw + im.width - 20 > maxw:
            lines.append(cur); cur, cw = [], 0
        cur.append(im); cw += adv(im)
    lines.append(cur)
    lh = int(size * 1.08) + 2 * stroke
    out = Image.new("RGBA", (maxw + 40, lh * len(lines) + int(size * 0.45)), (0, 0, 0, 0))
    for li, line in enumerate(lines):
        tw = sum(adv(i) for i in line) - sp
        x = (out.width - tw) / 2 - 10 if align == "center" else 0
        for im in line:
            out.alpha_composite(im, (int(x), li * lh)); x += adv(im)
    return out


def pill(txt, size, bg, fg=WHITE, padx=34, pady=14, path=None, outline=None, radius=None):
    f = font(path or F900, size)
    tw = f.getlength(txt); bb = f.getbbox("ÁgÑ")
    h = bb[3] - bb[1] + 2 * pady
    im = Image.new("RGBA", (int(tw + 2 * padx), int(h)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], im.height // 2 if radius is None else radius, fill=bg,
                        outline=outline, width=3 if outline else 0)
    d.text((padx, pady - bb[1]), txt, font=f, fill=fg)
    return im


def shadowed(im, blur=22, off=(0, 18), alpha=90):
    pad = blur * 3
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (4, 20, 18, 0)); sh.putalpha(im.getchannel("A").point(lambda a: a * alpha // 255))
    out.alpha_composite(sh, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def paste_center(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if im is None or scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda a: int(a * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


_BANDS = {}


def band_img(h, w=W - 80, a=120):
    k = (h, w, a)
    if k not in _BANDS:
        band = Image.new("RGBA", (w + 60, h), (0, 0, 0, 0))
        ImageDraw.Draw(band).rounded_rectangle([30, 18, w + 30, h - 18], 38, fill=(6, 30, 27, a))
        _BANDS[k] = band.filter(ImageFilter.GaussianBlur(10))
    return _BANDS[k]


def check_icon(size, color=WHITE, bg=BRONCE):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=bg)
    s = size
    d.line([(s * .27, s * .52), (s * .44, s * .68), (s * .74, s * .34)], fill=color, width=max(4, s // 9), joint="curve")
    return im


def cross_icon(size, color=WHITE, bg=TERRACOTA):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=bg); s = size; w = max(4, s // 9)
    d.line([(s * .32, s * .32), (s * .68, s * .68)], fill=color, width=w)
    d.line([(s * .68, s * .32), (s * .32, s * .68)], fill=color, width=w)
    return im


# ------------------------------------------------------------------ audio (todo tonal)
def tone(freq, dur, decay=18, vol=0.35):
    t = np.arange(int(SR * dur)) / SR
    return (np.sin(2 * np.pi * freq * t) * np.exp(-decay * t) * vol).astype(np.float32)


def tick(high=False): return tone(1500 if high else 1150, 0.05, 70, 0.22 if high else 0.15)


def whoosh(dur=0.45):
    n = int(SR * dur); t = np.arange(n) / SR; ph = t / dur
    f = 260 + 520 * ph ** 1.4
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.35 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    return (s * np.sin(np.pi * ph) ** 2 * 0.06).astype(np.float32)


def chime_ok():
    """Acierto: arpegio mayor brillante."""
    out = np.zeros(int(SR * 1.3), np.float32)
    for k, f in enumerate((659.3, 830.6, 987.8, 1318.5)):
        s = tone(f, 1.0, 4.5, 0.16); s[:int(SR * 0.6)] += tone(f * 2, 0.6, 9, 0.04)
        i = int(SR * 0.07 * k); out[i:i + len(s)] += s[: len(out) - i]
    return out


def soft_hit():
    t = np.arange(int(SR * 0.8)) / SR
    f = 55 + 60 * np.exp(-t * 18)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * np.clip(t / 0.004, 0, 1) * 0.5).astype(np.float32)


def stamp():
    """Golpe seco para el sello MITO / REALIDAD."""
    s = soft_hit() * 1.2; s[:int(SR * 0.25)] += tone(220, 0.25, 14, 0.25)
    return s


def riser(d):
    t = np.arange(int(SR * d)) / SR
    f = 220 + 900 * (t / d) ** 2
    return ((np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.1) * (t / d) ** 2).astype(np.float32)


def study_beat(total, bpm=88):
    """Base musical suave tipo 'lo-fi de estudio': bombo redondo, tic tonal y acordes de pad (sin ruido)."""
    n = int(SR * (total + 1)); out = np.zeros(n, np.float32)
    step = 60 / bpm / 2
    t = np.arange(int(SR * 0.3)) / SR
    kick = (np.sin(2 * np.pi * np.cumsum(45 + 70 * np.exp(-t * 28)) / SR) * np.exp(-t * 10) * 0.55).astype(np.float32)
    hat = tone(3200, 0.04, 120, 0.035)
    chords = [(220.0, 261.6, 329.6), (196.0, 246.9, 293.7), (174.6, 220.0, 261.6), (196.0, 246.9, 329.6)]
    i, tt = 0, 0.0
    while tt < total:
        k = int(tt * SR)
        if i % 4 == 0:
            out[k:k + len(kick)] += kick[: n - k]
        elif i % 2 == 1:
            out[k:k + len(hat)] += hat[: n - k]
        if i % 16 == 0:                                        # un acorde cada compás
            dur = step * 16; tc = np.arange(int(SR * dur)) / SR
            env = np.clip(tc / 0.6, 0, 1) * np.clip((dur - tc) / 0.8, 0, 1)
            pad = sum(np.sin(2 * np.pi * f * tc) + 0.3 * np.sin(2 * np.pi * f * 2.001 * tc) for f in chords[(i // 16) % 4])
            pad = (pad * env * 0.025).astype(np.float32)
            out[k:k + len(pad)] += pad[: n - k]
        tt += step; i += 1
    return out


def dehiss(a, sr=SR):
    """Red de seguridad sobre toda la banda sonora: cualquier tramo >= 80 ms que suene a ruido blanco se silencia."""
    a = np.asarray(a, np.float32); fr = int(sr * 0.02); n = len(a) // fr
    if n < 5:
        return a
    F = a[: n * fr].reshape(n, fr)
    X = np.abs(np.fft.rfft(F * np.hanning(fr), axis=1)) + 1e-9
    flat = np.exp(np.mean(np.log(X[:, 3:]), axis=1)) / np.mean(X[:, 3:], axis=1)
    rms = np.sqrt(np.mean(F ** 2, axis=1)); top = np.percentile(rms, 95) + 1e-9
    bad = (flat > 0.78) & (rms > 0.004 * top)
    g = np.ones(n, np.float32); i = 0
    while i < n:
        if bad[i]:
            j = i
            while j < n and bad[j]: j += 1
            if j - i >= 4: g[i:j] = 0.05
            i = j
        else:
            i += 1
    if g.min() == 1:
        return a
    gs = np.concatenate([np.repeat(g, fr), np.ones(len(a) - n * fr, np.float32)])
    gs = np.convolve(gs, np.ones(int(sr * 0.012)) / int(sr * 0.012), "same")
    print(f"audio: eliminados {int(np.sum(g < 1)) * 20} ms de siseo", flush=True)
    return (a * gs).astype(np.float32)


def enc_args(out, scale=True):
    return ((["-vf", f"scale={OUT_W}:{OUT_H}:flags=bicubic"] if scale else []) +
            ["-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-crf", "23", "-maxrate", "2500k",
             "-bufsize", "5000k", "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", "-use_editlist", "0", out])


# ------------------------------------------------------------------ iconos de línea (dibujados en código, sin texto)
def icon(name, size=64, color=CARBON, bg=None, stroke=None):
    """Icono sencillo de línea: clock, euro, team, plan, chart, calendar, check, cross, shield, doc, up, gear."""
    S = 4 * size; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w = stroke or max(10, S // 14); c = tuple(color[:3]) + (255,)
    if bg:
        d.ellipse([0, 0, S - 1, S - 1], fill=tuple(bg[:3]) + (255,))
    m = S * 0.22; L, T_, R, B = m, m, S - m, S - m; cx, cy = S / 2, S / 2
    if name == "clock":
        d.ellipse([L, T_, R, B], outline=c, width=w)
        d.line([(cx, cy), (cx, T_ + w * 2.2)], fill=c, width=w); d.line([(cx, cy), (R - w * 2.6, cy)], fill=c, width=w)
    elif name == "euro":
        d.arc([L + w, T_, R + w * 1.5, B], 50, 310, fill=c, width=w)
        d.line([(L - w * 0.3, cy - w * 1.6), (cx + w, cy - w * 1.6)], fill=c, width=int(w * 0.8))
        d.line([(L - w * 0.3, cy + w * 1.0), (cx + w, cy + w * 1.0)], fill=c, width=int(w * 0.8))
    elif name == "team":
        for dx, k in ((-0.2, 0.85), (0.2, 0.85), (0, 1.0)):
            r = S * 0.09 * k; x = cx + dx * S; y = cy - S * 0.1
            d.ellipse([x - r, y - r - S * 0.04, x + r, y + r - S * 0.04], outline=c, width=int(w * 0.8))
            d.arc([x - r * 1.9, y + r * 0.9, x + r * 1.9, y + r * 4.6], 200, 340, fill=c, width=int(w * 0.8))
    elif name in ("plan", "doc"):
        d.rectangle([L + S * 0.06, T_, R - S * 0.06, B], outline=c, width=w)
        if name == "plan":
            d.line([(L + S * 0.06, cy), (cx, cy)], fill=c, width=int(w * 0.7)); d.line([(cx, T_), (cx, B - S * 0.12)], fill=c, width=int(w * 0.7))
        else:
            for k in range(3):
                y = T_ + S * (0.14 + 0.12 * k); d.line([(L + S * 0.16, y), (R - S * 0.16, y)], fill=c, width=int(w * 0.6))
    elif name in ("chart", "up"):
        d.line([(L, B), (R, B)], fill=c, width=w)
        for k, h in enumerate((0.25, 0.45, 0.7)):
            x = L + S * 0.08 + k * S * 0.17; d.rectangle([x, B - S * h * 0.75, x + S * 0.1, B], fill=c)
        if name == "up":
            d.line([(L, B - S * 0.25), (R - S * 0.05, T_ + S * 0.02)], fill=c, width=int(w * 0.8))
    elif name == "calendar":
        d.rectangle([L, T_ + S * 0.06, R, B], outline=c, width=w); d.line([(L, T_ + S * 0.2), (R, T_ + S * 0.2)], fill=c, width=w)
        for x in (L + S * 0.14, R - S * 0.14):
            d.line([(x, T_ - S * 0.02), (x, T_ + S * 0.1)], fill=c, width=w)
        d.rectangle([cx - S * 0.05, cy + S * 0.02, cx + S * 0.05, cy + S * 0.12], fill=c)
    elif name == "check":
        d.line([(L + S * 0.02, cy + S * 0.02), (cx - S * 0.06, B - S * 0.1), (R, T_ + S * 0.08)], fill=c, width=int(w * 1.3), joint="curve")
    elif name == "cross":
        d.line([(L + S * 0.06, T_ + S * 0.06), (R - S * 0.06, B - S * 0.06)], fill=c, width=int(w * 1.3))
        d.line([(R - S * 0.06, T_ + S * 0.06), (L + S * 0.06, B - S * 0.06)], fill=c, width=int(w * 1.3))
    elif name == "shield":
        d.polygon([(cx, T_), (R, T_ + S * 0.1), (R - S * 0.04, cy + S * 0.08), (cx, B), (L + S * 0.04, cy + S * 0.08), (L, T_ + S * 0.1)],
                  outline=c, width=w)
    else:                                                  # gear / genérico
        d.ellipse([L + S * 0.08, T_ + S * 0.08, R - S * 0.08, B - S * 0.08], outline=c, width=w)
        d.ellipse([cx - S * 0.08, cy - S * 0.08, cx + S * 0.08, cy + S * 0.08], fill=c)
    return im.resize((size, size), Image.LANCZOS)


_ICON_RX = [("clock", r"tiempo|hora|horas|minut|rápid|semana|día|dias|días"), ("euro", r"€|coste|cost|precio|pag|factur|dinero|margen|sueldo|nómin|nomin|rentab|cobr"),
            ("team", r"equipo|plantilla|emplead|persona|contrat|socio|arquitecto|colaborador"),
            ("calendar", r"plazo|entrega|calendario|fecha|mes|meses|año"), ("plan", r"plano|proyecto|planimetr|revit|cad|modelo|bim|detalle"),
            ("doc", r"memoria|documento|pliego|estudio|presupuesto|medicion|certificad"), ("up", r"crec|más encargos|escal|aument|subir|ganar"),
            ("shield", r"firma|responsab|riesgo|seguridad|garant|revis|calidad")]


def icon_for(text):
    import re as _re
    t = text.lower()
    for name, rx in _ICON_RX:
        if _re.search(rx, t):
            return name
    return "check"


# ------------------------------------------------------------------ sonido premium (v2): música y transiciones
# Todo sintetizado aquí (sin licencias): piano eléctrico con armónicos, bajo, arpegio con eco, reverb por convolución y
# percusión suave. Varias progresiones y tempos: cada reel suena distinto pero siempre elegante (negro y oro en audio).
def _env(n, a=0.005, d=1.2, sr=SR):
    t = np.arange(n) / sr
    return np.clip(t / max(a, 1e-4), 0, 1) * np.exp(-t / d)


def epiano(freq, dur, vel=1.0):
    """Nota de piano eléctrico (Rhodes): parciales con caída distinta + ligero trémolo + campanita de ataque."""
    n = int(SR * dur); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * freq * t) * _env(n, 0.004, 1.6)
         + 0.35 * np.sin(2 * np.pi * freq * 2.0 * t) * _env(n, 0.003, 0.7)
         + 0.12 * np.sin(2 * np.pi * freq * 3.0 * t) * _env(n, 0.002, 0.35)
         + 0.08 * np.sin(2 * np.pi * freq * 7.02 * t) * _env(n, 0.001, 0.06))          # «tine» del ataque
    s *= 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    rel = min(n, int(SR * 0.08)); s[-rel:] *= np.linspace(1, 0, rel)
    return (s * 0.11 * vel).astype(np.float32)


def _reverb(x, secs=2.2, wet=0.28, seed=7):
    """Reverb de sala por convolución con una respuesta suave (ruido filtrado y en caída: el resultado es tonal)."""
    rng = np.random.default_rng(seed)
    n = int(SR * secs); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 3.2 / secs)
    ir = np.convolve(ir, np.ones(24) / 24, "same")                    # quita los agudos (más cálido, sin siseo)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    L = len(x) + n; N = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]
    return (x * (1 - wet) + y.astype(np.float32) * wet * 0.9).astype(np.float32)


PROGS = [  # (acordes en Hz, raíz del bajo) — maj7 / m9: sofisticado, tranquilo y con brillo
    [((261.6, 329.6, 392.0, 493.9), 65.4), ((220.0, 261.6, 329.6, 392.0), 55.0),
     ((174.6, 220.0, 261.6, 329.6), 87.3), ((196.0, 246.9, 293.7, 392.0), 98.0)],      # Cmaj7 Am7 Fmaj7 G6
    [((293.7, 349.2, 440.0, 523.3), 73.4), ((196.0, 246.9, 349.2, 440.0), 98.0),
     ((261.6, 329.6, 392.0, 493.9), 65.4), ((220.0, 261.6, 329.6, 392.0), 55.0)],      # Dm7 G9 Cmaj7 Am7
    [((233.1, 293.7, 349.2, 440.0), 58.3), ((196.0, 233.1, 293.7, 349.2), 98.0),
     ((207.7, 261.6, 311.1, 392.0), 51.9), ((174.6, 220.0, 261.6, 349.2), 87.3)],      # Bbmaj7 Gm7 Abmaj7 F
]


def premium_beat(total, bpm=84, seed=0, energy=1.0, jitter=True):
    """Base musical premium: acordes de piano eléctrico, bajo redondo, arpegio con eco y pulso suave."""
    rng = random.Random(seed)
    prog = PROGS[rng.randrange(len(PROGS))]
    bpm = bpm + (rng.choice((-4, 0, 4)) if jitter else 0)     # jitter=False: tempo exacto (cortes al ritmo)
    beat = 60 / bpm; bar = beat * 4
    n = int(SR * (total + 2)); keys = np.zeros(n, np.float32); low = np.zeros(n, np.float32); perc = np.zeros(n, np.float32)

    def add(buf, a, t0):
        i = int(t0 * SR)
        if i >= n: return
        j = min(n, i + len(a)); buf[i:j] += a[: j - i]

    t, b = 0.0, 0
    patt = rng.choice(([0, 2, 1, 3, 2, 1, 3, 2], [0, 1, 2, 3, 2, 1, 0, 2], [0, 2, 3, 1, 2, 3, 1, 2]))
    while t < total + bar:
        ch, root = prog[b % len(prog)]
        for k, f in enumerate(ch):                              # acorde, ligeramente rasgueado
            add(keys, epiano(f, bar * 1.05, 0.55), t + 0.012 * k)
        if b % 2 == 1:                                           # empuje en el 3er tiempo de compases alternos
            for f in ch[1:]:
                add(keys, epiano(f, beat * 1.4, 0.32), t + 2.5 * beat)
        for s_, idx in enumerate(patt):                          # arpegio en corcheas, una octava arriba
            add(keys, epiano(ch[idx] * 2, beat * 0.9, 0.22 * energy), t + s_ * beat / 2)
        nb = int(SR * bar); tb = np.arange(nb) / SR              # bajo: raíz con caída larga y armónico suave
        bass = (np.sin(2 * np.pi * root * tb) + 0.25 * np.sin(2 * np.pi * root * 2 * tb)) * _env(nb, 0.02, 1.4) * 0.22
        add(low, bass.astype(np.float32), t)
        for q in range(4):                                       # pulso: bombo suave en 1 y 3, «click» en 2 y 4
            tq = t + q * beat
            if q % 2 == 0:
                nk = int(SR * 0.35); tk = np.arange(nk) / SR
                kick = np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-tk * 30)) / SR) * np.exp(-tk * 9) * 0.32 * energy
                add(perc, kick.astype(np.float32), tq)
            else:
                add(perc, tone(2400, 0.04, 160, 0.025 * energy) + tone(1200, 0.04, 90, 0.02 * energy), tq)
        t += bar; b += 1
    d = int(SR * beat * 0.75)                                    # eco del arpegio a corchea con puntillo
    echo = np.zeros_like(keys); echo[d:] = keys[:-d] * 0.28
    mix = _reverb(keys + echo, 2.4, 0.32, rng.randrange(10 ** 6)) + low + perc
    fade = min(len(mix), int(SR * 1.5))
    mix[:int(SR * 0.6)] *= np.linspace(0, 1, int(SR * 0.6))
    out = mix[: int(SR * total)]
    out[-fade:] *= np.linspace(1, 0, fade)
    return (out / (np.max(np.abs(out)) + 1e-9) * 0.5).astype(np.float32)


def _band_noise(n, f0, f1, seed=3):
    """Ruido de banda estrecha que barre de f0 a f1 (por bloques en frecuencia): suena a aire, nunca a siseo."""
    rng = np.random.default_rng(seed)
    out = np.zeros(n, np.float32); blk = 1024
    for i in range(0, n, blk // 2):
        seg = rng.standard_normal(blk); F = np.fft.rfft(seg * np.hanning(blk))
        fr = np.fft.rfftfreq(blk, 1 / SR); fc = f0 + (f1 - f0) * min(1, i / max(1, n))
        F *= np.exp(-((fr - fc) / (fc * 0.35)) ** 2)
        s = np.fft.irfft(F, blk).astype(np.float32)
        j = min(n, i + blk); out[i:j] += s[: j - i]
    return out / (np.max(np.abs(out)) + 1e-9)


def whoosh2(dur=0.5):
    """Transición de diapositiva: soplo de aire que sube + cuerpo tonal suave (elegante, sin estridencias)."""
    n = int(SR * dur); t = np.arange(n) / SR; ph = t / dur
    air = _band_noise(n, 500, 2600) * np.sin(np.pi * ph) ** 2.2 * 0.09
    f = 180 + 320 * ph ** 1.6
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * ph) ** 2 * 0.035
    return (air + body).astype(np.float32)


def impact():
    """Golpe grave y corto al entrar cada escena (da peso, como en los anuncios premium)."""
    n = int(SR * 0.6); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-t * 18)) / SR) * np.exp(-t * 6.5) * 0.30
    s += np.sin(2 * np.pi * 110 * t) * np.exp(-t * 30) * 0.05
    return s.astype(np.float32)


def blip(k=0):
    """Aparición de una opción: nota de marimba suave que sube con cada opción (A, B, C, D)."""
    f = (659.3, 784.0, 880.0, 1046.5, 1174.7)[k % 5]
    n = int(SR * 0.35); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 3.99 * t) * np.exp(-t * 40)) * np.exp(-t * 14) * 0.09
    return s.astype(np.float32)


def tick2(last=False):
    """Cuenta atrás: tic de madera (el último, más agudo)."""
    f = 1900 if last else 1400
    n = int(SR * 0.08); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.7 * t)) * np.exp(-t * 85) * 0.11
    return s.astype(np.float32)


def shimmer():
    """Cierre / momento clave: brillo de campanitas en arpegio con reverb."""
    out = np.zeros(int(SR * 1.6), np.float32)
    for k, f in enumerate((1046.5, 1318.5, 1568.0, 2093.0)):
        s = epiano(f, 1.2, 0.5); i = int(SR * 0.06 * k); out[i:i + len(s)] += s[: len(out) - i]
    return _reverb(out, 1.4, 0.4, 11)

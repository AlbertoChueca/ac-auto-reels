"""Las ESCENAS de los reels «explicados» (ver explicado_kit.py para los utensilios). Cada una es draw(c, st).

    despacho      el estudio de noche: monitor, reloj, pila de encargos y el arquitecto de espaldas (poses)
    llamada       entra una llamada (quién, asunto) y se acepta o se rechaza
    rejilla       N iconos (documentos, casas, personas…) con K resaltados
    barras        2-3 barras que crecen, con su cifra
    cifra         un número grande que cuenta hasta su valor
    curva         carga de trabajo del año frente a la capacidad (fija o elástica)
    meses         12 meses: trabajo de cada mes y lo que pagas (coste fijo o variable)
    plano         una planta que se dibuja sola y sus capas (cotas, estructura, fontanería, electricidad) y la firma
    flujo         tres pasos encadenados (tú diseñas → se desarrolla → tú firmas)
    versus        dos columnas enfrentadas, fila a fila
    presupuesto   el documento de presupuesto: partidas, sello y pagos por fases
    equipo        tu equipo y las manos que se suman
    edificio      un bloque que sube planta a planta, con viviendas resaltadas
    tribunal      la mesa del tribunal (o el tutor) con tu panel detrás y sus gestos
    lamina        los 7 bloques de un TFM como un panel que se va llenando
    movil         «pásaselo a…»: el reel en un móvil y la hoja de enviar
    cierre        la marca
"""
import math, random

import skia

from explicado_kit import *        # noqa: F401,F403  (utensilios de dibujo)

CX = W / 2
MESES = "EFMAMJJASOND"


def _entra(st, d=0.5, delay=0.0):
    return eo((st.t - delay) / d)


# ------------------------------------------------------------------ despacho
def despacho(c, st):
    t = st.t
    hora = st.mix("hora", 21.0, d=max(0.8, st.dur * 0.9))
    noche = st.get("luz", "noche") == "noche"
    # calendario de pared con el día de entrega marcado
    c.save(); c.translate(118, 720)
    rrect(c, -78, -84, 156, 176, 14, CARBON, ORO_D, 5)
    line(c, -78, -42, 78, -42, ORO_D, 4)
    for q in (-36, 36):
        line(c, q, -100, q, -66, ORO, 6)
    dia = int(st.get("dia", 9))
    for i in range(12):
        gx, gy = -52 + (i % 4) * 35, -14 + (i // 4) * 36
        if i == dia and st.get("entrega", True):
            c.drawCircle(gx, gy, 15, stroke(CORAL, 4, 0.75 + 0.25 * math.sin(t * 5)))
            c.drawCircle(gx, gy, 5, fill(CORAL))
        else:
            c.drawCircle(gx, gy, 4.5, fill(ORO_D if i > dia else ORO, 0.9))
            if i < dia:
                line(c, gx - 8, gy + 8, gx + 8, gy - 8, ORO_D, 3)
    c.restore()
    # reloj de pared
    icono(c, "reloj", 962, 720, 70, ORO, 1.0, hora=hora)
    # mesa
    halo(c, CX, 930, 620, ORO, 0.16 if st.get("pantalla", "plano") != "apagada" else 0.04)
    rrect(c, 20, 1218, 1040, 34, 10, CARBON, ORO, 5)
    # pila de encargos (carpetas)
    n = st.mix("pila", 0.0, d=0.9)
    for i in range(int(math.ceil(n))):
        k = clamp(n - i); y = 1218 - 30 - i * 34 - (1 - eob(k)) * 60
        rgb = CORAL if (st.get("pila_color") == "coral" and i >= 3) else ORO
        rrect(c, 34 + (i % 2) * 10, y, 150, 28, 6, CARBON, rgb, 4, clamp(k * 2))
        line(c, 50 + (i % 2) * 10, y + 14, 100 + (i % 2) * 10, y + 14, rgb, 3, 0.6 * clamp(k * 2))
    # monitor
    mx, my, mw, mh = 216, 690, 648, 430
    rrect(c, CX - 28, my + mh, 56, 70, 4, CARBON, ORO_D, 4)
    rrect(c, CX - 120, 1196, 240, 22, 8, CARBON, ORO, 4)
    rrect(c, mx, my, mw, mh, 22, (11, 12, 16), ORO, 6)
    c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(mx + 8, my + 8, mw - 16, mh - 16), 14, 14), True)
    modo = st.get("pantalla", "plano"); ts = st.since("pantalla")
    if modo == "plano":
        tm = clamp((ts % 7.0) / 3.2)
        plano(c, mx + 44, my + 34, 2.72, tm, ("cotas",) if tm > 0.9 else (), {"cotas": clamp((ts % 7.0 - 3.2) / 0.8)}, fino=True)
        for i in range(6):                                           # panel de capas, como en CAD
            a = clamp(ts * 3 - i * 0.3)
            rrect(c, mx + 370, my + 46 + i * 54, 226, 36, 8, CARBON, ORO_D, 3, a)
            line(c, mx + 386, my + 64 + i * 54, mx + 386 + 60 + (i * 37) % 90, my + 64 + i * 54, ORO, 4, a * 0.8)
        cur = (ts * 0.35) % 1                                         # cursor
        c.drawCircle(mx + 80 + 240 * cur, my + 120 + 160 * abs(math.sin(ts * 0.9)), 7, fill(CREMA, 0.9))
    elif modo == "pendientes":
        tot = int(st.get("pendientes", 6)); vis = min(6, tot)
        text(c, "PENDIENTE", mx + 40, my + 62, 30, ORO, 0.9, align="l", track=0.12)
        text(c, str(tot), mx + mw - 44, my + 70, 54, CORAL, clamp(ts * 3), align="r")
        for i in range(vis):
            a = eo(ts * 2.2 - i * 0.22); y = my + 96 + i * 50 + (1 - a) * 20
            rrect(c, mx + 40, y, 30, 30, 6, None, CORAL, 4, a)
            line(c, mx + 90, y + 15, mx + 90 + 300 + (i * 53) % 170, y + 15, CREMA, 6, a * 0.75)
    elif modo == "aviso":
        a = eob(ts * 2.4)
        c.save(); c.translate(CX, my + mh / 2); c.scale(0.8 + 0.2 * a, 0.8 + 0.2 * a)
        rgb = COLOR.get(st.get("aviso_color", "coral"), CORAL)
        rrect(c, -260, -110, 520, 220, 26, CARBON, rgb, 6, clamp(a))
        icono(c, "calendario", -180, 0, 46, rgb, clamp(a))
        ls = wrap(st.get("aviso", "Entrega: mañana"), 40, 320)
        for i, l_ in enumerate(ls[:3]):
            text(c, l_, -110, -22 + (i - (len(ls[:3]) - 1) / 2) * 50 + 30, 40, CREMA, clamp(a), align="l")
        c.restore()
    elif modo == "vacia":
        a = eo(ts * 2)
        text(c, "BANDEJA DE ENTRADA", CX, my + 150, 30, ORO_D, a, track=0.14)
        text(c, "0", CX, my + 290, 150, ORO_D, a)
        text(c, "encargos nuevos", CX, my + 350, 32, ORO_D, a, bold=False)
    elif modo == "ok":
        a = eob(ts * 2.2)
        circle(c, CX, my + mh / 2, 110 * a, CARBON, ORO_L, 7)
        icono(c, "check", CX, my + mh / 2 + 6, 80, ORO_L, 1.0, t=clamp(ts * 2.5 - 0.3))
    elif modo == "correo":
        nn = int(st.get("correos", 4))
        for i in range(nn):
            a = eob(ts * 2.4 - i * 0.35); y = my + 40 + i * 88
            rrect(c, mx + 50 + (1 - a) * 80, y, mw - 100, 70, 14, CARBON, ORO if i else CORAL, 4, clamp(a))
            circle(c, mx + 96 + (1 - a) * 80, y + 35, 18, None, ORO if i else CORAL, 4, clamp(a))
            line(c, mx + 136, y + 26, mx + 136 + 220 + (i * 61) % 160, y + 26, CREMA, 6, 0.8 * clamp(a))
            line(c, mx + 136, y + 48, mx + 136 + 120 + (i * 37) % 120, y + 48, ORO_D, 5, 0.8 * clamp(a))
    c.restore()
    # arquitecto, de espaldas
    pose = st.get("pose", "trabaja"); tp = st.since("pose"); ant = st.was("pose", pose)
    figura(c, CX, 1345, 1.0, pose, t, ORO, 1.0, mezcla=(ant, tp / 0.45) if ant != pose else None)
    if pose == "agobio":                                              # gotas de agobio
        for i in range(3):
            k = (t * 0.9 + i * 0.33) % 1
            c.drawCircle(CX - 150 + i * 150 + (i - 1) * 40 * k, 1175 - 80 * k, 7, fill(CORAL, (1 - k) * 0.9))
    if pose == "telefono":
        for i in range(3):
            k = (t * 1.2 + i * 0.33) % 1
            c.drawArc(skia.Rect.MakeXYWH(CX - 230 - 60 * k, 1130 - 60 * k, 120 * k + 40, 120 * k + 40), 120, 100, False,
                      stroke(ORO_L, 5, (1 - k) * 0.8))


# ------------------------------------------------------------------ llamada
def llamada(c, st):
    t = st.t; a = eob(_entra(st, 0.45))
    resp = st.get("respuesta"); tr = st.since("respuesta") if resp else 0
    sonando = not resp
    vib = math.sin(t * 38) * 2.2 if sonando and (t % 1.4) < 0.7 else 0
    c.save(); c.translate(CX, 1090 + (1 - a) * 500); c.scale(0.94, 0.94); c.rotate(vib)
    if sonando:
        for i in range(3):
            k = (t * 0.8 + i / 3) % 1
            rrect(c, -250 - 90 * k, -420 - 90 * k, 500 + 180 * k, 840 + 180 * k, 70 + 40 * k, None, ORO, 5, (1 - k) * 0.5)
    rgbm = CORAL if resp == "no" else ORO
    rrect(c, -250, -420, 500, 840, 64, (11, 12, 16), rgbm, 7)
    rrect(c, -70, -398, 140, 26, 13, CARBON_L, None, 0)
    halo(c, 0, -170, 260, rgbm, 0.20)
    circle(c, 0, -170, 96, CARBON, rgbm, 6)
    icono(c, st.get("icono", "persona"), 0, -166, 52, rgbm)
    text(c, "LLAMADA ENTRANTE", 0, -310, 26, ORO_D, 1, track=0.14)
    sz, ls = fit(st.get("quien", "Promotor"), 62, 430, 1)
    text(c, ls[0], 0, -10, sz, CREMA)
    sz, ls = fit(st.get("asunto", ""), 36, 430, 2, bold=False, min_size=28)
    for i, l_ in enumerate(ls[:2]):
        text(c, l_, 0, 52 + i * 46, sz, ORO_L, 0.95, bold=False)
    # botones
    for lado, rgb, nombre in ((-1, CORAL, "no"), (1, ORO_L, "si")):
        pres = resp == nombre; k = eob(tr * 3) if pres else 0
        apag = 0.3 if (resp and not pres) else 1.0
        circle(c, lado * 120, 250, 66 + 10 * k, rgb if pres else CARBON, rgb, 6, apag)
        if nombre == "no":
            icono(c, "cruz", lado * 120, 250, 30, NEGRO if pres else rgb, apag)
        else:
            icono(c, "check", lado * 120, 254, 30, NEGRO if pres else rgb, apag)
    c.restore()


# ------------------------------------------------------------------ rejilla
def rejilla(c, st):
    n = int(st.get("n", 18)); cols = int(st.get("cols", 0)) or (6 if n > 24 else 5 if n > 12 else 4 if n > 6 else 3)
    rows = math.ceil(n / cols)
    aw, ah = 940, 800
    cell = min(aw / cols, ah / rows, 250)
    s = cell * 0.33
    ch = min(cell * 1.35, ah / rows)                                 # filas algo más separadas si hay sitio
    x0 = CX - cols * cell / 2 + cell / 2; y0 = 1050 - rows * ch / 2 + ch / 2
    res = st.get("resaltar", 0); tr = st.since("resaltar")
    idx = set(res) if isinstance(res, (list, tuple)) else set(range(int(res)))
    if st.get("resaltar_fin"):                                        # los K últimos en vez de los primeros
        idx = set(range(n - int(res), n))
    rgbh = COLOR.get(st.get("color", "oro"), ORO)
    ico = st.get("icono", "doc"); nums = st.get("numeros", False)
    orden = sorted(idx)
    for i in range(n):
        cx_, cy_ = x0 + (i % cols) * cell, y0 + (i // cols) * ch
        a = eob(st.t * 2.6 - i * (1.1 / max(6, n)))
        if a <= 0:
            continue
        hot = i in idx
        kh = eob(tr * 3 - orden.index(i) * (0.9 / max(4, len(orden)))) if hot else 0
        if hot and kh > 0:
            rgb = mixc(ORO_D, rgbh, clamp(kh)); al = 1.0; sc = a * (1 + 0.12 * math.sin(clamp(kh) * math.pi))
            halo(c, cx_, cy_, cell * 0.62, rgbh, 0.20 * clamp(kh))
        else:
            dim = clamp(tr * 2.5) if idx else 0
            rgb = ORO_D if idx else ORO; al = lerp(1.0, 0.5, dim) if idx else 1.0; sc = a
        icono(c, ico, cx_, cy_, s, rgb, al * clamp(a * 2), sc=max(0.01, sc))
        if nums:
            text(c, str(i + 1), cx_, cy_ + s * 1.75, max(20, s * 0.5), rgb, al * clamp(a * 2), bold=False)
        if hot and st.get("marca") and kh > 0.3:
            icono(c, st.get("marca"), cx_ + s * 0.7, cy_ - s * 0.8, s * 0.42, CREMA if st.get("marca") == "check" else CORAL,
                  1.0, t=clamp(kh * 1.4 - 0.3))


# ------------------------------------------------------------------ barras
def barras(c, st):
    bs = st.get("barras", []); prev = st.prev.get("barras", bs) if st.k > 0 else bs
    n = max(1, len(bs)); bw = min(250, 760 / n); gap = (880 - n * bw) / (n + 1)
    base = 1380; hmax = 560
    line(c, 80, base, 1000, base, ORO_D, 4, _entra(st))
    tb = st.since("barras"); primera = st.since("barras") == st.t
    for i, b in enumerate(bs):
        x = 100 + gap + i * (bw + gap)
        v1 = float(b.get("v", 50)); v0 = float(prev[i].get("v", v1)) if (not primera and i < len(prev)) else 0.0
        k = eo((tb - i * 0.25) / 0.9)
        v = lerp(v0, v1, k); h = max(6, hmax * v / 100)
        rgb = COLOR.get(b.get("c", "oro"), ORO)
        halo(c, x + bw / 2, base - h / 2, bw * 1.1, rgb, 0.12)
        rrect(c, x, base - h, bw, h, 14, mixc(CARBON, rgb, 0.16), rgb, 6)
        sz, ls = fit(b.get("e", ""), 30, bw + gap * 0.8, 2, min_size=22)
        for j, l_ in enumerate(ls[:2]):
            text(c, l_, x + bw / 2, base + 48 + j * 36, sz, CREMA, clamp(k * 2), track=0.04)
        if b.get("t"):
            sz, ls = fit(b["t"], 54, bw + gap * 0.9, 1, min_size=30)
            text(c, ls[0], x + bw / 2, base - h - 26, sz, rgb, clamp(k * 2.5 - 1), outline=8)


# ------------------------------------------------------------------ cifra
def cifra(c, st):
    v = float(st.get("valor", 0)); tv = st.since("valor")
    v0 = float(st.was("valor", 0) or 0) if st.since("valor") != st.t else float(st.get("desde", 0))
    k = eo(tv / float(st.get("dur", 1.1)))
    cur = lerp(v0, v, k)
    dec = int(st.get("decimales", 0))
    s_ = f"{cur:,.{dec}f}".replace(",", "·").replace(".", ",").replace("·", ".")
    s_ = st.get("prefijo", "") + s_ + st.get("sufijo", "")
    rgb = COLOR.get(st.get("color", "oro_l"), ORO_L)
    halo(c, CX, 1000, 520, rgb, 0.16)
    pulso = 1 + 0.04 * math.sin(clamp(k) * math.pi)
    for i in range(2):                                                # anillos
        rr = 330 + i * 46
        c.drawArc(skia.Rect.MakeXYWH(CX - rr, 1000 - rr, 2 * rr, 2 * rr), -90 + st.t * (20 - 34 * i), 300 * eo(st.t / 0.9),
                  False, stroke(rgb if i == 0 else ORO_D, 6 - i * 2, 0.9 - i * 0.4))
    sz = 250
    while tw(s_, sz) > 560 and sz > 90:
        sz -= 10
    c.save(); c.translate(CX, 1000); c.scale(pulso, pulso)
    text(c, s_, 0, sz * 0.34, sz, rgb, 1.0, outline=10)
    c.restore()
    if st.get("sub"):
        sz, ls = fit(st.get("sub"), 46, 940, 1, min_size=32)
        if len(ls) > 1:
            sz, ls = fit(st.get("sub"), 40, 900, 2, min_size=30)
        for i, l_ in enumerate(ls[:2]):
            text(c, l_, CX, 1408 + i * (sz + 8) - (len(ls[:2]) - 1) * (sz + 8) / 2, sz, CREMA, eo((st.since("sub") - 0.2) / 0.5), outline=8)
    if st.get("icono"):
        icono(c, st.get("icono"), CX, 700, 40, rgb, eo(st.t * 2))


# ------------------------------------------------------------------ curva (carga de trabajo del año)
_CARGA = [0.30, 0.52, 0.92, 0.98, 0.80, 0.62, 0.30, 0.08, 0.70, 0.95, 0.72, 0.22]


def curva(c, st):
    """p: datos (lista 0..1; por defecto la carga de un estudio en el año), eje (etiquetas), capacidad ("fija" |
    "elastica"), nivel (altura de la línea fija), cap_texto, resalta ("picos" | "valles"), txt_picos, txt_valles."""
    base, alto = 1400, 600
    datos = st.get("datos") or _CARGA
    eje = st.get("eje") or (list(MESES) if len(datos) == 12 else [str(i + 1) for i in range(len(datos))])
    n = len(datos)
    px = lambda i: 110 + i * (860 / max(1, n - 1))
    cap = st.get("capacidad"); tc = st.since("capacidad") if cap else 0
    lvl = float(st.get("nivel", 0.52))
    te = _entra(st, 1.6)
    line(c, 90, base, 990, base, ORO_D, 4)
    for i, m in enumerate(eje[:n]):
        text(c, str(m), px(i), base + 46, 28, ORO_D, 1, bold=False)
    if st.get("eje_texto"):
        text(c, st.get("eje_texto"), 990, base + 92, 24, ORO_D, 1, align="r", track=0.1)
    pts = [(px(i), base - alto * v) for i, v in enumerate(datos)]
    p = skia.Path(); p.moveTo(*pts[0])
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]; x1, y1 = pts[i]; mx = (x0 + x1) / 2
        p.cubicTo(mx, y0, mx, y1, x1, y1)
    ycap = base - alto * lvl
    res = st.get("resalta")
    if cap == "fija":
        k = eo(tc / 0.7)
        for (clip_top, clip_h, rgb, quien) in ((0, ycap, CORAL, "picos"), (ycap, base - ycap, CREMA, "valles")):
            c.save(); c.clipRect(skia.Rect.MakeXYWH(0, clip_top, W, clip_h))
            area = skia.Path(p); area.lineTo(990, ycap); area.lineTo(110, ycap); area.close()
            al = 0.34 if res == quien else 0.16
            if res == quien:
                al += 0.12 * math.sin(st.t * 5)
            c.drawPath(area, fill(rgb, al * k))
            c.restore()
        pa = stroke(CREMA, 5, 0.9 * k); pa.setPathEffect(skia.DashPathEffect.Make([18, 14], 0))
        c.drawLine(90, ycap, 90 + 900 * k, ycap, pa)
        text(c, st.get("cap_texto", "TU EQUIPO"), 986, ycap - 16, 26, CREMA, k, align="r", track=0.08)
    pa = stroke(ORO, 8)
    if te < 1:
        L = skia.PathMeasure(p, False).getLength(); pa.setPathEffect(skia.DashPathEffect.Make([L * te, L], 0))
    c.drawPath(p, pa)
    for i, q in enumerate(pts):
        if te * (n - 1) >= i:
            circle(c, q[0], q[1], 9, NEGRO, ORO, 5)
    if cap == "elastica":
        k = eo(tc / 1.2)
        p2 = skia.Path(); p2.moveTo(pts[0][0], lerp(ycap, pts[0][1] - 26, k))
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1][0], lerp(ycap, pts[i - 1][1] - 26, k); x1, y1 = pts[i][0], lerp(ycap, pts[i][1] - 26, k)
            mx = (x0 + x1) / 2; p2.cubicTo(mx, y0, mx, y1, x1, y1)
        pa = stroke(ORO_L, 6, 0.95); pa.setPathEffect(skia.DashPathEffect.Make([18, 14], st.t * 30))
        c.drawPath(p2, pa)
        text(c, st.get("cap_texto", "TU EQUIPO + EXTERNO"), 986, base - alto - 30, 26, ORO_L, k, align="r", track=0.08)
    imax = max(range(n), key=lambda i: datos[i]); imin = min(range(n), key=lambda i: datos[i])
    if res == "picos" and (cap == "fija" or st.get("txt_picos")):
        tx = st.get("txt_picos", "NO LLEGAS")
        cand = [i for i in range(n) if datos[i] >= 0.9] or [imax]
        for i in (cand[0], cand[-1]) if len(cand) > 1 and cand[-1] - cand[0] > 2 else (cand[-1],):
            xx = min(max(pts[i][0], 110 + tw(tx, 30) / 2), 990 - tw(tx, 30) / 2)
            text(c, tx, xx, pts[i][1] - 34, 30, CORAL, eo(st.since("resalta") * 2 - 0.2), outline=8)
    if res == "valles" and (cap == "fija" or st.get("txt_valles")):
        text(c, st.get("txt_valles", "PAGAS IGUAL"), min(max(pts[imin][0], 220), 880), (ycap + 120) if cap == "fija" else pts[imin][1] - 40, 30, CREMA,
             eo(st.since("resalta") * 2 - 0.2), outline=8)


# ------------------------------------------------------------------ meses (trabajo y coste de cada mes)
def meses(c, st):
    base, alto = 1400, 420
    trab = st.get("trabajo") or _CARGA
    coste = st.get("coste", "fijo"); tcs = st.since("coste")
    line(c, 70, base, 1010, base, ORO_D, 4)
    cw = 880 / 12
    for i in range(12):
        x = 100 + i * cw + cw / 2
        a = eo(st.t * 2 - i * 0.07)
        h = max(8, alto * trab[i]) * a
        vacio = trab[i] < 0.35
        rrect(c, x - cw * 0.33, base - h, cw * 0.66, h, 8, mixc(CARBON, ORO, 0.14), ORO if not vacio else ORO_D, 4, a)
        text(c, MESES[i], x, base + 44, 26, ORO_D, a, bold=False)
        # lo que pagas ese mes
        ky = 790
        if coste == "fijo":
            k = eob(tcs * 3 - i * 0.08)
            if k > 0:
                rgb = CORAL if (vacio and st.get("resalta")) else ORO
                if vacio and st.get("resalta"):
                    halo(c, x, ky, 60, CORAL, 0.25 + 0.1 * math.sin(st.t * 6))
                icono(c, "moneda", x, ky, 29, rgb, 1.0, sc=max(0.01, k))
        else:
            k = eob(tcs * 3 - i * 0.08)
            if k > 0 and not vacio:
                icono(c, "moneda", x, ky, 13 + 17 * trab[i], ORO_L, 1.0, sc=max(0.01, k))
    text(c, st.get("arriba", "LO QUE PAGAS"), 100, 720, 28, CREMA, _entra(st), align="l", track=0.1)
    text(c, st.get("abajo", "EL TRABAJO QUE ENTRA"), 100, base - alto - 40, 28, CREMA, _entra(st), align="l", track=0.1)


# ------------------------------------------------------------------ plano
def plano_grande(c, st):
    s = 5.9; x = CX - 50 * s; y = 676
    caps = list(st.get("capas", [])); antes = list(st.prev.get("capas", [])) if st.k > 0 else []
    tcap = st.since("capas")
    tc = {n_: (clamp(tcap / 1.1) if n_ not in antes or st.since("capas") == st.t and False else 1.0) for n_ in caps}
    for n_ in caps:
        if n_ not in antes:
            tc[n_] = clamp(tcap / 1.1)
    halo(c, CX, 1050, 640, ORO, 0.10)
    plano(c, x, y, s, clamp(st.t / float(st.get("dibujo", 2.4))), caps, tc)
    if st.get("firma"):
        tf_ = st.since("firma"); k = eob(tf_ * 2.6)
        c.save(); c.translate(770, 1352); c.rotate(-6); c.scale(max(0.01, k), max(0.01, k))
        rrect(c, -200, -78, 400, 156, 18, (11, 12, 16), ORO_L, 6)
        text(c, st.get("firma_texto", "TU FIRMA"), -176, -36, 26, ORO_L, 1, align="l", track=0.14)
        c.save(); c.translate(0, 16); ic_firma(c, 84, CREMA, 1.0, clamp(tf_ * 1.6 - 0.4)); c.restore()
        c.restore()
    if st.get("etiqueta"):
        text(c, st.get("etiqueta"), x, 1478, 30, CREMA, 0.8 * eo(st.since("etiqueta") * 2), align="l", bold=False)


# ------------------------------------------------------------------ flujo (tres pasos)
def flujo(c, st):
    pasos = st.get("pasos", []); act = st.get("activo", None); ta = st.since("activo")
    n = len(pasos); ch = 190; gap = 78
    y0 = 1050 - (n * ch + (n - 1) * gap) / 2
    for i, pz in enumerate(pasos):
        a = eob(st.t * 2.4 - i * 0.5)
        if a <= 0:
            continue
        y = y0 + i * (ch + gap)
        on = act is None or act == i or (isinstance(act, list) and i in act)
        k = eo(ta * 3) if on and act is not None else 0
        rgb = COLOR.get(pz.get("c", "oro"), ORO) if on else ORO_D
        c.save(); c.translate(CX, y + ch / 2); c.scale(max(0.01, a) * (1 + 0.04 * k), max(0.01, a) * (1 + 0.04 * k))
        if on and act is not None:
            halo(c, 0, 0, 520, rgb, 0.16)
        rrect(c, -420, -ch / 2, 840, ch, 30, mixc(CARBON, rgb, 0.10 if on else 0.0), rgb, 6, 1.0 if on else 0.6)
        circle(c, -320, 0, 62, (11, 12, 16), rgb, 5, 1.0 if on else 0.6)
        icono(c, pz.get("i", "doc"), -320, 0, 34, rgb, 1.0 if on else 0.6)
        sz, ls = fit(pz.get("t", ""), 50, 560, 2, min_size=34)
        for j, l_ in enumerate(ls[:2]):
            text(c, l_, -230, 18 + (j - (len(ls[:2]) - 1) / 2) * (sz + 8), sz, CREMA if on else ORO_D, 1, align="l")
        if pz.get("s"):
            pass
        c.restore()
        if i < n - 1:
            ky = y + ch + 8; kk = eo(st.t * 2.4 - i * 0.5 - 0.4)
            trazo(c, [(CX, ky), (CX, ky + (gap - 16))], kk, ORO if on else ORO_D, 6)
            if kk > 0.8:
                poly(c, [(CX - 16, ky + gap - 34), (CX + 16, ky + gap - 34), (CX, ky + gap - 12)], ORO, None, 0)


# ------------------------------------------------------------------ versus
def versus(c, st):
    A = st.get("a", {"t": "CONTRATAR", "filas": []}); B = st.get("b", {"t": "DELEGAR", "filas": []})
    n = st.mix("n", 0, d=0.5); nn = int(st.get("n", 0)); tn = st.since("n")
    y0, hh = 650, 800
    for lado, D, rgb in ((0, A, CORAL), (1, B, ORO_L)):
        a = eob(st.t * 2.4 - lado * 0.25); x = 50 + lado * 500
        c.save(); c.translate(x + 240, y0 + hh / 2); c.scale(max(0.01, a), max(0.01, a)); c.translate(-240, -hh / 2)
        rrect(c, 0, 0, 480, hh, 30, mixc(CARBON, rgb, 0.06), rgb, 6)
        sz, ls = fit(D.get("t", ""), 46, 420, 1, min_size=30)
        text(c, ls[0], 240, 76, sz, rgb, 1, track=0.06)
        line(c, 40, 112, 440, 112, rgb, 3, 0.5)
        filas = D.get("filas", [])
        rh = (hh - 150) / max(3, len(filas))
        for i, f_ in enumerate(filas):
            if i >= nn:
                continue
            k = eo(tn * 2.5) if i == nn - 1 else 1.0
            yy = 150 + i * rh + rh / 2
            icono(c, "cruz" if lado == 0 else "check", 62, yy, 22, rgb, k, t=k)
            sz, ls = fit(f_, 36, 350, 3, bold=False, min_size=26)
            for j, l_ in enumerate(ls[:3]):
                text(c, l_, 104 + (1 - k) * 20, yy + 12 + (j - (len(ls[:3]) - 1) / 2) * (sz + 6), sz, CREMA, k, align="l", bold=False)
        c.restore()


# ------------------------------------------------------------------ presupuesto
def presupuesto(c, st):
    a = eob(_entra(st, 0.5))
    c.save(); c.translate(CX, 1000 + (1 - a) * 300); c.rotate(-2 + 2 * a)
    rrect(c, -350, -370, 700, 740, 26, (13, 15, 19), ORO, 6)
    text(c, st.get("titulo", "PRESUPUESTO"), -300, -292, 38, ORO, 1, align="l", track=0.14)
    line(c, -300, -262, 300, -262, ORO_D, 3)
    part = st.get("partidas", ["Planimetría", "Instalaciones", "Estructuras", "Memoria", "Mediciones"])
    marc = st.get("marcadas", None); tm = st.since("marcadas")
    for i, p_ in enumerate(part[:6]):
        k = eo(st.t * 2 - 0.3 - i * 0.16); y = -205 + i * 76
        on = marc is None or i in marc
        rrect(c, -300, y - 22, 44, 44, 8, None, ORO if on else ORO_D, 4, k)
        if on:
            icono(c, "check", -278, y + 2, 16, ORO_L, k, t=clamp((tm if marc is not None else st.t) * 3 - 0.6 - i * 0.2))
        text(c, p_, -236, y + 13, 36, CREMA if on else ORO_D, k, align="l", bold=False)
        line(c, 150, y, 300, y, ORO_D if not on else CREMA, 6, k * 0.6)
    if st.get("cerrado", True):
        k = eo(st.t * 2 - 1.3)
        line(c, -300, 232, 300, 232, ORO, 3, k)
        text(c, "TOTAL", -300, 302, 34, ORO, k, align="l", track=0.14)
        text(c, st.get("total", "CERRADO"), 300, 306, 50, ORO_L, k, align="r")
    c.restore()
    if st.get("sello"):
        ts = st.since("sello"); k = eob(ts * 3)
        c.save(); c.translate(842, 716); c.rotate(14 - 30 * (1 - clamp(k))); c.scale(max(0.01, k) * (2.2 - 1.2 * clamp(ts * 4)), max(0.01, k) * (2.2 - 1.2 * clamp(ts * 4)))
        circle(c, 0, 0, 128, (13, 15, 19), ORO_L, 8); circle(c, 0, 0, 104, None, ORO_L, 3)
        sz, ls = fit(st.get("sello"), 78, 190, 1, min_size=40)
        text(c, ls[0], 0, sz * 0.2, sz, ORO_L)
        text(c, st.get("sello_sub", "CERRADO EN"), 0, -56, 20, ORO_L, 1, track=0.14)
        c.restore()
    if st.get("pago"):
        tp = st.since("pago"); k = eo(tp * 2.2)
        y = 1396; w = 700
        f = float(st.get("pago", 60)) / 100
        rrect(c, CX - w / 2, y, w * f * k, 64, 14, mixc(CARBON, ORO_L, 0.3), ORO_L, 5)
        k2 = eo(tp * 2.2 - 0.6)
        if k2 > 0:
            rrect(c, CX - w / 2 + w * f + 12, y, (w * (1 - f) - 12) * k2, 64, 14, CARBON, ORO, 5)
        text(c, st.get("pago_a", "60 % al iniciar"), CX - w / 2 + 20, y + 44, 30, CREMA, k, align="l")
        text(c, st.get("pago_b", "40 % al entregar"), CX + w / 2 - 20, y + 44, 30, CREMA, k2, align="r")


# ------------------------------------------------------------------ equipo
def equipo(c, st):
    prop = int(st.get("propios", 3)); ext = st.mix("extra", 0, d=1.0); text_ext = st.get("extra_texto")
    halo(c, CX, 1150, 600, ORO, 0.10)
    # los que se suman (detrás, en arco)
    N = int(math.ceil(ext))
    for i in range(N):
        k = eob(clamp(ext - i)); an = math.radians(-160 + i * (140 / max(1, int(st.get("extra", 1)) - 1 or 1)))
        x = CX + math.cos(an) * 400; y = 1120 + math.sin(an) * 330
        halo(c, x, y, 120, ORO_L, 0.18 * clamp(k))
        icono(c, "persona", x, y, 62, ORO_L, clamp(k * 2), sc=max(0.01, k))
        pa = stroke(ORO_L, 3, 0.5 * clamp(k)); pa.setPathEffect(skia.DashPathEffect.Make([10, 10], -st.t * 30))
        c.drawLine(x, y + 60, CX, 1250, pa)
    for i in range(prop):
        a = eob(st.t * 2.4 - i * 0.2); x = CX + (i - (prop - 1) / 2) * 230
        apagado = st.get("saturado") and True
        rgb = CORAL if st.get("saturado") else ORO
        icono(c, "persona", x, 1290, 92, rgb if apagado else ORO, 1.0, sc=max(0.01, a))
        if st.get("saturado"):
            for j in range(3):
                kk = (st.t * 0.8 + j / 3 + i * 0.2) % 1
                icono(c, "doc", x - 60 + j * 60, 1130 - 130 * (1 - kk), 22, CORAL, kk * 0.9)
    if text_ext and ext > 0.5:
        text(c, text_ext, CX, 1462, 32, ORO_L, eo(st.since("extra") * 2 - 0.4), track=0.1, outline=8)


# ------------------------------------------------------------------ edificio (bloque de viviendas)
def edificio(c, st):
    pl = int(st.get("plantas", 8)); cols = int(st.get("cols", 4))
    bw = 620; x0 = CX - bw / 2; base = 1420; ph = min(96, 720 / pl); top = base - pl * ph
    k = eo(st.t / 1.2)
    halo(c, CX, (top + base) / 2, 560, ORO, 0.12)
    line(c, 60, base, 1020, base, ORO_D, 5)
    res = st.get("resaltar"); tr = st.since("resaltar")
    idx = set(res) if isinstance(res, (list, tuple)) else (set(range(int(res))) if res else set())
    rgbh = COLOR.get(st.get("color", "oro_l"), ORO_L)
    vis = int(math.ceil(pl * k))
    for f in range(vis):                                              # planta a planta, desde abajo
        kk = eob(clamp(pl * k - f)); y = base - (f + 1) * ph
        rrect(c, x0, y + (1 - kk) * -30, bw, ph, 4, CARBON, ORO, 5, clamp(kk * 2))
        for j in range(cols):
            i = f * cols + j; wx = x0 + (j + 0.5) * bw / cols
            hot = i in idx; kh = eob(tr * 3 - (sorted(idx).index(i) if hot else 0) * (0.8 / max(4, len(idx)))) if hot else 0
            if hot and kh > 0:
                rrect(c, wx - 44, y + ph * 0.2, 88, ph * 0.56, 6, mixc(CARBON, rgbh, 0.75 * clamp(kh)), rgbh, 4, clamp(kk * 2))
                halo(c, wx, y + ph / 2, 80, rgbh, 0.25 * clamp(kh))
            else:
                al = (0.45 if idx and clamp(tr * 2.5) > 0.5 else 1.0) * clamp(kk * 2)
                rrect(c, wx - 44, y + ph * 0.2, 88, ph * 0.56, 6, (11, 12, 16), ORO_D, 4, al)
                line(c, wx, y + ph * 0.2, wx, y + ph * 0.76, ORO_D, 3, al)
    if st.get("grua", True):                                          # grúa
        gx = x0 + bw + 70; gt = top - 150
        line(c, gx, base, gx, gt, ORO_D, 7); line(c, gx - 330 * k, gt + 30, gx + 90, gt + 30, ORO_D, 6)
        line(c, gx, gt, gx - 200 * k, gt + 30, ORO_D, 3); line(c, gx, gt, gx + 90, gt + 30, ORO_D, 3)
        cx_ = gx - 250 * k + 30 * math.sin(st.t * 0.8)
        line(c, cx_, gt + 30, cx_, gt + 110 + 14 * math.sin(st.t * 1.5), ORO_D, 3)
        rrect(c, cx_ - 22, gt + 110 + 14 * math.sin(st.t * 1.5), 44, 30, 4, CARBON, ORO, 4)
    if st.get("texto"):
        text(c, st.get("texto"), CX, top - 40, 34, CREMA, eo(st.since("texto") * 2), track=0.08, outline=8)


# ------------------------------------------------------------------ tribunal (defensa / corrección)
def tribunal(c, st):
    """p: miembros (1-3), gesto (None | "duda" | "ok" | "no"), foco (índice que habla), panel (bool: tu lámina detrás),
    alumno (bool)."""
    n = int(st.get("miembros", 3)); gesto = st.get("gesto"); tg = st.since("gesto") if gesto else 0
    a0 = _entra(st, 0.6)
    halo(c, CX, 980, 620, ORO, 0.12)
    if st.get("panel", True):                                         # tu panel, colgado detrás
        rrect(c, CX - 250, 640, 500, 330, 10, (11, 12, 16), ORO_D, 5, a0)
        rrect(c, CX - 226, 664, 210, 150, 6, None, ORO_D, 4, a0); rrect(c, CX + 4, 664, 222, 96, 6, None, ORO_D, 4, a0)
        for i in range(4):
            line(c, CX + 8, 790 + i * 22, CX + 8 + 200 - (i * 47) % 90, 790 + i * 22, ORO_D, 4, a0 * 0.8)
        rrect(c, CX - 226, 836, 452, 110, 6, None, ORO_D, 4, a0)
    foco = st.get("foco")
    for i in range(n):
        a = eob(st.t * 2.2 - i * 0.2); x = CX + (i - (n - 1) / 2) * 290
        on = foco is None or foco == i
        rgb = ORO if on else ORO_D
        icono(c, "persona", x, 1085, 104, rgb, 1.0 if on else 0.7, sc=max(0.01, a))
        if gesto and (foco is None or foco == i):
            k = eob(tg * 3 - i * 0.25)
            if k > 0:
                gx, gy = x + 84, 905
                rgbg = CORAL if gesto in ("duda", "no") else ORO_L
                circle(c, gx, gy, 46 * k, (11, 12, 16), rgbg, 5)
                if gesto == "duda":
                    text(c, "?", gx, gy + 22 * k, 64 * k, rgbg)
                elif gesto == "ok":
                    icono(c, "check", gx, gy + 2, 24 * k, rgbg, 1.0)
                else:
                    icono(c, "cruz", gx, gy, 22 * k, rgbg, 1.0)
    rrect(c, 60, 1196, 960, 44, 12, CARBON, ORO, 6, a0)                # la mesa del tribunal
    rrect(c, 110, 1240, 860, 150, 6, (11, 12, 16), ORO_D, 5, a0)
    if st.get("alumno", True):                                        # tú, de espaldas
        figura(c, CX, 1560, 0.72, st.get("pose", "mira"), st.t, ORO_L, a0)


# ------------------------------------------------------------------ lámina / paneles del TFM por bloques
BLOQUES = ["Urbanismo", "Planos", "Construcción", "Instalaciones", "Estructuras", "Imágenes 3D", "Memoria"]


def lamina(c, st):
    """Los 7 bloques de un TFM como un panel que se va llenando. p: hechos (cuántos están cerrados, 0-7), resaltar
    (índices atascados, en coral), nombres (bool), activo (índice en el que estás)."""
    hechos = st.mix("hechos", 0, d=1.0); res = st.get("resaltar") or []; tr = st.since("resaltar")
    act = st.get("activo")
    cajas = [(-400, -380, 380, 240), (0, -380, 400, 240), (-400, -120, 260, 240), (-120, -120, 250, 240), (150, -120, 250, 240),
             (-400, 140, 520, 240), (140, 140, 260, 240)]
    halo(c, CX, 1050, 640, ORO, 0.10)
    a0 = _entra(st, 0.5)
    rrect(c, CX - 430, 1050 - 410, 860, 820, 16, (11, 12, 16), ORO_D, 5, a0)
    for i, (x, y, w_, h_) in enumerate(cajas):
        a = eob(st.t * 2.4 - i * 0.13)
        if a <= 0:
            continue
        hecho = clamp(hechos - i); mal = i in res
        km = eob(tr * 3 - res.index(i) * 0.25) if mal else 0
        rgb = CORAL if (mal and km > 0) else (ORO_L if hecho >= 1 else ORO if act == i else ORO_D)
        bx, by = CX + x + 10, 1050 + y + 10; bw, bh = w_ - 20, h_ - 20
        c.save(); c.translate(bx + bw / 2, by + bh / 2); c.scale(max(0.01, a), max(0.01, a)); c.translate(-bw / 2, -bh / 2)
        if mal and km > 0:
            halo(c, bw / 2, bh / 2, bw * 0.7, CORAL, 0.20 + 0.08 * math.sin(st.t * 5))
        rrect(c, 0, 0, bw, bh, 10, mixc(CARBON, rgb, 0.22 * hecho if not mal else 0.12), rgb, 5 if (hecho >= 1 or mal or act == i) else 4)
        if hecho > 0 and not mal:                                     # contenido dibujado a medida que se cierra
            for j in range(3):
                line(c, 22, bh - 30 - j * 24, 22 + (bw - 44) * clamp(hecho * 1.5 - j * 0.25) * (1 - j * 0.22), bh - 30 - j * 24, rgb, 5, 0.75)
            icono(c, "check", bw - 34, 34, 16, ORO_L, clamp(hecho), t=clamp(hecho * 1.5 - 0.3))
        if mal and km > 0.3:
            icono(c, "cruz", bw - 34, 34, 15, CORAL, 1.0, t=clamp(km * 1.5 - 0.3))
        if st.get("nombres", True):
            sz = max(18, min(34, 34 * (bw - 84) / max(1, tw(BLOQUES[i], 34))))   # deja sitio a la marca de la esquina
            text(c, BLOQUES[i], 20, 30 + sz * 0.6, sz, CREMA if (hecho >= 1 or mal or act == i) else ORO_D, 1, align="l")
        c.restore()


# ------------------------------------------------------------------ móvil: pásaselo a…
def movil(c, st):
    t = st.t; a = eob(_entra(st, 0.5))
    c.save(); c.translate(CX, 1040 + (1 - a) * 700); c.rotate(-3 + 3 * a)
    rrect(c, -270, -470, 540, 940, 70, (11, 12, 16), ORO, 7)
    c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-250, -450, 500, 900), 54, 54), True)
    th = st.get("_thumb")
    if th is not None:
        c.drawImageRect(th, skia.Rect.MakeXYWH(-250, -450, 500, 900), skia.SamplingOptions(skia.FilterMode.kLinear))
        c.drawRect(skia.Rect.MakeXYWH(-250, -450, 500, 900), fill(NEGRO, 0.25))
    # hoja de enviar
    k = eo((t - 0.5) / 0.5)
    yh = 450 - 330 * k
    rrect(c, -250, yh, 500, 400, 36, CREMA, None, 0)
    rrect(c, -40, yh + 16, 80, 8, 4, (200, 194, 182), None, 0)
    text(c, "Enviar a", -214, yh + 78, 34, (20, 22, 28), 1, align="l")
    cont = st.get("contactos") or st.get("_contactos") or ["Tu compi", "Taller", "Clase"]
    tap = 1.5; env = t > tap + 0.25
    for i, nom in enumerate(cont[:3]):
        x = -150 + i * 150; y = yh + 168
        rgb = (ORO, (70, 80, 100), (120, 130, 150))[i]
        sel = i == 0 and t > tap
        circle(c, x, y, 50 + (6 * eob((t - tap) * 4) if sel else 0), rgb, NEGRO if sel else None, 6 if sel else 0)
        text(c, nom[:1].upper(), x, y + 16, 44, CREMA)
        text(c, nom, x, y + 96, 26, NEGRO, 1, bold=False)
    c.restore()
    if env:
        ke = eob((t - tap - 0.25) * 3)
        c.save(); c.translate(0, -80); c.scale(max(0.01, ke), max(0.01, ke))
        rrect(c, -150, -42, 300, 84, 42, ORO_L, None, 0)
        text(c, "Enviado ✓".replace("✓", ""), -20, 14, 38, NEGRO)
        icono(c, "check", 96, 2, 18, NEGRO, 1.0)
        c.restore()
    # dedo
    kf = eio((t - 0.9) / 0.6); out = eio((t - tap - 0.2) / 0.5)
    fx_ = lerp(260, -150, kf) + 260 * out; fy_ = lerp(700, yh + 200, kf) + 320 * out
    if t > 0.8:
        capsule(c, fx_, fy_, fx_ + 46, fy_ + 220, 64, (232, 196, 168), NEGRO, 5)
    c.restore()


# ------------------------------------------------------------------ cierre
def cierre(c, st):
    a = eo(st.t / 0.5)
    halo(c, CX, 900, 620, ORO, 0.16 * a)
    lg = st.get("_logo")
    if lg is not None:
        w = 520; h = w * lg.height() / lg.width()
        pa = skia.Paint(AntiAlias=True, Color=col((255, 255, 255), a))
        c.drawImageRect(lg, skia.Rect.MakeXYWH(CX - w / 2, 800 - h / 2 - (1 - a) * 30, w, h),
                        skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), pa)
    k = eo((st.t - 0.35) / 0.5)
    line(c, CX - 160 * k, 980, CX + 160 * k, 980, ORO, 4, k)
    sz, ls = fit(st.get("claim") or st.get("_claim") or "Asesoría para tu TFM de arquitectura", 46, 860, 2, bold=False)
    for i, l_ in enumerate(ls[:2]):
        text(c, l_, CX, 1070 + i * 60, sz, CREMA, k, bold=False)
    k2 = eo((st.t - 0.6) / 0.5)
    text(c, st.get("handle") or st.get("_handle") or "@arquitectura_confidencial", CX, 1290, 40, ORO_L, k2)
    text(c, st.get("web") or st.get("_web") or "arquitecturaconfidencial.com", CX, 1350, 32, ORO_D, k2, bold=False)


ESCENAS = {"despacho": despacho, "llamada": llamada, "rejilla": rejilla, "barras": barras, "cifra": cifra, "curva": curva,
           "meses": meses, "plano": plano_grande, "flujo": flujo, "versus": versus, "presupuesto": presupuesto,
           "equipo": equipo, "edificio": edificio, "tribunal": tribunal, "lamina": lamina, "movil": movil, "cierre": cierre}
# parámetros que cada escena entiende (lo usa el validador de guiones)
PARAMS = {
    "despacho": {"hora", "luz", "dia", "entrega", "pantalla", "pendientes", "aviso", "aviso_color", "correos", "pila", "pila_color", "pose"},
    "llamada": {"quien", "asunto", "icono", "respuesta"},
    "rejilla": {"n", "cols", "icono", "resaltar", "resaltar_fin", "color", "numeros", "marca"},
    "barras": {"barras"},
    "cifra": {"valor", "desde", "dur", "decimales", "prefijo", "sufijo", "color", "sub", "icono"},
    "curva": {"datos", "eje", "eje_texto", "nivel", "capacidad", "cap_texto", "resalta", "txt_picos", "txt_valles"},
    "meses": {"trabajo", "coste", "resalta", "arriba", "abajo"},
    "plano": {"capas", "dibujo", "firma", "firma_texto", "etiqueta"},
    "flujo": {"pasos", "activo"},
    "versus": {"a", "b", "n"},
    "presupuesto": {"titulo", "partidas", "marcadas", "cerrado", "total", "sello", "sello_sub", "pago", "pago_a", "pago_b"},
    "equipo": {"propios", "extra", "extra_texto", "saturado"},
    "edificio": {"plantas", "cols", "resaltar", "color", "grua", "texto"},
    "tribunal": {"miembros", "gesto", "foco", "panel", "alumno", "pose"},
    "lamina": {"hechos", "resaltar", "nombres", "activo"},
    "movil": {"contactos"},
    "cierre": {"claim", "handle", "web"},
}

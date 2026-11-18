"""Reels «EXPLICADOS» de AC · ArquitecturaConfidencial: explicativos animados (ilustración vectorial con los colores de
AC, subtítulos palabra a palabra, mito tachado y «pásaselo a…») para estudiantes de arquitectura agobiados con su TFM.

Enfoque obligatorio (marca.py): asesoría y acompañamiento. Cada reel ENSEÑA algo que le sirve al alumno (planificar,
qué mira el tribunal, por qué se atasca, cómo aprovechar una corrección) y AC aparece como el equipo que acompaña. Nunca
se dice ni se insinúa que alguien hace el TFM por el alumno: el proyecto, las decisiones y la defensa son suyos.

Estructura de cada guion (fuentes/explicados.json):
    1. escena en segunda persona con giro («Quedan tres semanas. Y sigues cambiando la planta.»)
    2. el mito, tachado («Y no, no es que seas un desastre»)
    3. el porqué, explicado con un dibujo
    4. la salida, en pasos concretos que el alumno puede aplicar hoy
    5. el reencuadre («Un TFM no se acaba: se cierra»)
    6. «Pásaselo a ese compañero que…» (compartir) y la marca
Cada golpe = una frase de voz + una escena (explicado_escenas.py) con sus parámetros + un rótulo opcional.

    python explicado.py --lista | --valida
    VOZ=mock python explicado.py --render <id> out/x.mp4        # prueba local sin voz real
"""
import base64, datetime, json, math, os, random, re, subprocess, sys, time

import numpy as np
import skia

import explicado_kit as K
import explicado_escenas as E
from explicado_kit import W, H, ORO, ORO_L, ORO_D, CREMA, NEGRO, CORAL, COLOR, clamp, eo, eio, eob, lerp

HERE = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(HERE, "fuentes", "explicados.json")
FPS, SR = 30, 24000
SAFE_TOP, SAFE_BOT = 250, 1480
Y_SUB, Y_ROT = 345, 520                    # subtítulos y rótulo
CAM0 = (W / 2, 1050, 1.0)
import marca
HANDLE, WEB = marca.HANDLE, marca.WEB
ESTILO_VOZ = {
    "gancho": "storytelling, intrigued, like starting a story for a colleague, a little suspense",
    "giro": "a beat of tension, lower and slower, then let it land",
    "mito": "firm and a little playful, stress the NO",
    "porque": "clear, explaining to a friend, natural ups and downs",
    "dato": "weighty and precise, slow down on the number",
    "salida": "brighter, confident, quicker pace",
    "reencuadre": "calm, lower, the key line: pause before the second half",
    "compartir": "warm and friendly, a smile in the voice, never a sales pitch",
}


def say(*a):
    print("explicado:", *a, flush=True)


# ------------------------------------------------------------------ banco
def banco():
    return json.load(open(BANCO))["guiones"]


def _usados():
    try:
        return [x["id"] for x in json.load(open(os.path.join(HERE, "used.json")))]
    except Exception:
        return []


def elegir(seed=0, cual=None):
    """El guion menos usado (los nuevos primero, en el orden del banco)."""
    G = banco(); u = _usados()
    if cual:
        return next(g for g in G if g["id"] == cual)
    rng = random.Random(seed)
    return min(G, key=lambda g: (u.count(f"explicado:{g['id']}"), G.index(g) if u.count(f"explicado:{g['id']}") == 0 else rng.random()))


def validar(g):
    """Errores de un guion (lista vacía = válido). Lo usan el banco y el agente que escribe guiones nuevos."""
    err = []
    bs = g.get("golpes") or []
    if not (7 <= len(bs) <= 16):
        err.append(f"{len(bs)} golpes (7-16)")
    palabras = sum(len(b.get("voz", "").split()) for b in bs) + len(g.get("compartir", "").split())
    if not (60 <= palabras <= 135):
        err.append(f"{palabras} palabras de voz (60-135)")
    esc = None
    for i, b in enumerate(bs):
        e = b.get("escena", "=")
        if e == "=":
            if esc is None:
                err.append("el primer golpe necesita escena")
        elif e not in E.ESCENAS or e in ("movil", "cierre"):
            err.append(f"golpe {i + 1}: escena desconocida «{e}»")
        else:
            esc = e
        malos = set(b.get("p") or {}) - E.PARAMS.get(esc or "", set())
        if malos:
            err.append(f"golpe {i + 1}: parámetros que {esc} no entiende: {sorted(malos)}")
        n = len(b.get("voz", "").split())
        if not (2 <= n <= 20):
            err.append(f"golpe {i + 1}: {n} palabras (2-20)")
        if b.get("rotulo") and len(b["rotulo"]) > 26:
            err.append(f"golpe {i + 1}: rótulo de más de 26 caracteres")
    if not g.get("compartir") or not re.match(r"^(Pásaselo|Envíaselo|Mándaselo|Compártelo)", g.get("compartir", "")):
        err.append("falta «compartir» (empieza por Pásaselo / Envíaselo / Mándaselo / Compártelo)")
    if not g.get("hook") or len(g["hook"]) > 46:
        err.append("falta «hook» (titular de portada, máx. 46 caracteres)")
    if not any(b.get("tachado") for b in bs):
        err.append("falta el mito tachado")
    todo = " ".join([g.get("hook", ""), g.get("compartir", ""), g.get("descripcion", ""), g.get("pregunta", "")] + g.get("puntos", [])
                    + [b.get("voz", "") + " " + b.get("rotulo", "") + " " + json.dumps(b.get("p", {}), ensure_ascii=False) for b in bs])
    if not marca.limpio(todo):
        err.append("contiene una promesa prohibida (marca.PROHIBIDO)")
    if re.search(r"te (lo )?hacemos|lo hacemos por ti|hacemos tu|te lo entregamos|sin que (tu tutor|nadie)|delega(r|s)? (tu|el) tfm|"
                 r"encarga(r|s)? (tu|el) tfm|aprobado garantizado|garantiza", todo, re.I):
        err.append("vende hacer el TFM o promete resultados: fuera del enfoque de asesoría")
    return err


# ------------------------------------------------------------------ voz y tiempos
def _voz(g):
    import voz
    bs = g["golpes"]
    textos = [b["voz"] for b in bs] + [g["compartir"]]
    est = []
    for i, b in enumerate(bs):
        t = b.get("tono") or ("gancho" if i == 0 else "mito" if b.get("tachado") else "dato" if b.get("escena") in ("cifra", "barras", "rejilla")
                              else "reencuadre" if i == len(bs) - 1 else "porque")
        est.append(ESTILO_VOZ.get(t, t))
    est.append(ESTILO_VOZ["compartir"])
    clips = voz.grabar(textos, est)
    tiempos = []
    for c_, t_ in zip(clips, textos):                            # cada palabra, en proporción a su longitud
        ws = t_.split(); L = sum(len(w) + 1 for w in ws); acc = 0; al = []
        for w in ws:
            al.append(((len(c_) / SR) * acc / L * 0.93, w)); acc += len(w) + 1 + (3 if w[-1:] in ".,:;?!…" else 0)
        tiempos.append(al)
    return clips, tiempos


def linea_tiempo(g, clips, tiempos):
    """Golpes con sus tiempos, escenas agrupadas, parámetros acumulados y palabras con su instante."""
    bs = [dict(b) for b in g["golpes"]] + [{"voz": g["compartir"], "escena": "movil", "p": {}, "_compartir": True}]
    t = 0.0; golpes = []
    for b, c_, tm in zip(bs, clips, tiempos):
        d = len(c_) / SR
        dur = max(d + float(b.get("pausa", 0.30)), 1.5 if not b.get("_compartir") else 3.1)
        golpes.append(dict(b, t0=t, t1=t + dur, v0=t + 0.10, palabras=[(t + 0.10 + a, w) for a, w in tm]))
        t += dur
    golpes.append({"voz": "", "escena": "cierre", "p": {}, "t0": t, "t1": t + 2.0, "v0": t, "palabras": []})
    total = t + 2.0
    escenas = []                                                 # [(nombre, [golpes con P acumulado])]
    for b in golpes:
        e = b.get("escena", "=")
        if e == "=" and escenas:
            P = dict(escenas[-1][1][-1]["P"]); P.update(b.get("p") or {})
            b["P"] = P; escenas[-1][1].append(b)
        else:
            b["P"] = dict(b.get("p") or {}); escenas.append((e, [b]))
        b["_esc"] = len(escenas) - 1
    return golpes, escenas, total


# ------------------------------------------------------------------ capas de texto
def _norm(w):
    return re.sub(r"[^\wáéíóúñü%€]", "", w.lower())


def _trozos(golpes):
    """Subtítulos: trozos de 2-4 palabras; cada uno = [(t, palabra, clave?)]."""
    out = []
    for b in golpes:
        claves = {_norm(x) for x in b.get("claves", [])}
        cur = []
        for t, w in b["palabras"]:
            cur.append((t, w, _norm(w) in claves))
            larg = sum(len(x[1]) + 1 for x in cur)
            if w[-1:] in ".,:;?!…" or larg >= 20 or len(cur) >= 4:
                out.append((cur, b["t1"])); cur = []
        if cur:
            out.append((cur, b["t1"]))
    return [(tr, tr[0][0], fin) for tr, fin in out]


def subtitulos(c, trozos, t):
    act = None
    for i, (tr, t0, fin) in enumerate(trozos):
        nxt = trozos[i + 1][1] if i + 1 < len(trozos) else fin
        if t0 - 0.05 <= t < max(nxt, tr[-1][0] + 0.25) and t < fin + 0.1:
            act = tr
    if not act:
        return
    size = 62
    ancho = lambda s_: sum(K.tw(w, s_) for _, w, _ in act) + (len(act) - 1) * s_ * 0.28
    while ancho(size) > 940 and size > 40:
        size -= 3
    x = W / 2 - ancho(size) / 2
    cur = max((i for i, (tw_, _, _) in enumerate(act) if tw_ <= t), default=0)
    for i, (tw_, w, clave) in enumerate(act):
        wd = K.tw(w, size)
        if tw_ <= t + 0.03:
            k = eo((t - tw_) / 0.12)
            if clave:
                K.rrect(c, x - 12, Y_SUB - size * 0.86, wd + 24, size * 1.2, 12, ORO_L, None, 0, clamp(k))
                K.text(c, w, x, Y_SUB - (1 - k) * 10, size, NEGRO, clamp(k), align="l")
            else:
                a = 1.0 if i == cur else 0.62
                K.text(c, w, x, Y_SUB - (1 - k) * 10, size, CREMA, a * clamp(k), align="l", outline=10)
        x += wd + size * 0.28


def rotulo(c, b, t, sig=None):
    txt = b.get("rotulo")
    if not txt:
        return
    t_in = b["t0"] + float(b.get("rotulo_t", 0.12))
    if b.get("rotulo_en"):
        m = [tt for tt, w in b["palabras"] if _norm(w).startswith(_norm(b["rotulo_en"]))]
        if m:
            t_in = m[0] - 0.05
    u = t - t_in
    if u < 0:
        return
    mismo = sig is not None and sig.get("rotulo") == txt
    out = 0.0 if mismo else clamp((t - (b["t1"] - 0.16)) / 0.16)
    k = eob(u / 0.28); a = clamp(u / 0.1) * (1 - out)
    rgb = COLOR.get(b.get("color", "crema"), CREMA)
    size, ls = K.fit(txt.upper(), 100, 960, 2, min_size=58)
    tach = b.get("tachado"); tt = u - float(b.get("tachado_t", 0.45))
    if tach and tt > 0:
        rgb = K.mixc(rgb, (150, 140, 128), clamp(tt * 4))
    c.save(); c.translate(W / 2, Y_ROT + (len(ls) - 1) * size * 0.55); c.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k)
    for i, l_ in enumerate(ls):
        y = (i - (len(ls) - 1)) * size * 1.08 + size * 0.36
        K.text(c, l_, 0, y, size, rgb, a, outline=16, ocol=NEGRO, track=0.02)
        if tach and tt > 0:
            wl = K.tw(l_, size) * 1.04 + 40
            kk = eo(tt / 0.25 - i * 0.4)
            c.drawLine(-wl / 2, y - size * 0.3, -wl / 2 + wl * kk, y - size * 0.33, K.stroke(CORAL, 14, a))
    c.restore()


def marca_agua(c, n_esc, a=0.8):
    pos = [(900, 212), (180, 212)][n_esc % 2]                        # esquinas superiores: nunca pisa el dibujo
    c.save(); c.translate(*pos)
    K.rrect(c, -17, -17, 34, 34, 9, None, CREMA, 3, a); K.circle(c, 0, 0, 7.5, None, CREMA, 3, a)
    c.drawCircle(9.5, -9.5, 2.2, K.fill(CREMA, a))
    K.text(c, WEB.upper(), 0, 46, 17, CREMA, a * 0.95, track=0.06)                     # la web, visible en todo el vídeo
    c.restore()


# ------------------------------------------------------------------ fotogramas
class Montaje:
    def __init__(self, g, golpes, escenas, total, seed=0):
        self.g, self.golpes, self.escenas, self.total, self.seed = g, golpes, escenas, total, seed
        self.trozos = _trozos(golpes)
        info = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
        self.sf = skia.Surface.MakeRaster(info)
        self.capa = skia.Surface.MakeRaster(info)
        self.capa2 = skia.Surface.MakeRaster(info)
        self.mini = skia.Surface.MakeRaster(skia.ImageInfo.Make(W // 4, H // 4, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        vel = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, 700, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        sh = skia.GradientShader.MakeLinear([(0, 0), (0, 700)], [K.col(NEGRO, 0.78), K.col(NEGRO, 0.0)])
        vel.getCanvas().drawRect(skia.Rect.MakeWH(W, 700), skia.Paint(Shader=sh))
        self.velo = vel.makeImageSnapshot()                      # degradado superior: subtítulos y rótulo siempre legibles
        self.extra = {}
        try:
            import fx
            lg = np.asarray(fx.logo(260, CREMA, ORO).convert("RGBA"))                 # logotipo de AC (papel + amarillo)
            self.extra["_logo"] = skia.Image.fromarray(np.ascontiguousarray(lg), colorType=skia.kRGBA_8888_ColorType)
        except Exception as e:
            say("logo no disponible:", str(e)[:80])

    def _cam(self, b, sig_t):
        return tuple(b.get("cam") or CAM0)

    def _escena(self, surf, ie, t):
        """Dibuja la escena ie en el instante t (absoluto) sobre surf (transparente), con su cámara."""
        nombre, bs = self.escenas[ie]
        c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
        k = max((i for i, b in enumerate(bs) if b["t0"] <= t), default=0)
        b = bs[k]; u = t - b["t0"]
        t_esc = t - bs[0]["t0"]
        rel = [dict(x, t0=x["t0"] - bs[0]["t0"], t1=x["t1"] - bs[0]["t0"]) for x in bs]
        st = K.St(t_esc, rel, k, u, self.seed)
        st.p = dict(st.p); st.p.update(self.extra)
        cam1 = tuple(b.get("cam") or CAM0); cam0 = tuple(bs[k - 1].get("cam") or CAM0) if k > 0 else cam1
        m = eio(u / 0.75)
        fx_, fy_, z = (lerp(cam0[i], cam1[i], m) for i in range(3))
        fy_ = min(fy_, 640 + 410 / max(z, 1.0))                                    # el zoom nunca sube el dibujo al rótulo
        z *= 1 + 0.035 * clamp(u / max(0.5, b["t1"] - b["t0"]))                    # empuje lento hacia dentro
        c.save(); c.translate(W / 2, 1050); c.scale(z, z); c.translate(-fx_, -fy_)
        E.ESCENAS[nombre](c, st)
        c.restore()
        return surf.makeImageSnapshot()

    def cuadro(self, t, textos=True):
        c = self.sf.getCanvas()
        gi = max((i for i, b in enumerate(self.golpes) if b["t0"] <= t), default=0)
        b = self.golpes[gi]; ie = b["_esc"]
        K.fondo(c, t, seed=self.seed if isinstance(self.seed, int) else 1)
        t0e = self.escenas[ie][1][0]["t0"]; ue = t - t0e
        capas = []
        TR = 0.26
        if ie > 0 and ue < TR:
            k = eo(ue / TR)
            capas.append((self._escena(self.capa2, ie - 1, t0e - 1e-3), 1 - k, lerp(1.0, 1.10, k)))
            capas.append((self._escena(self.capa, ie, t), k, lerp(0.90, 1.0, k)))
        else:
            capas.append((self._escena(self.capa, ie, t), 1.0, 1.0))
        lin = skia.SamplingOptions(skia.FilterMode.kLinear)
        for img, a, sc in capas:
            # brillo de neón: copia a 1/4 de tamaño, desenfocada y sumada (rápido), y encima el dibujo nítido
            mc = self.mini.getCanvas(); mc.clear(skia.ColorTRANSPARENT)
            mc.drawImageRect(img, skia.Rect.MakeWH(W // 4, H // 4), lin, skia.Paint(ImageFilter=skia.ImageFilters.Blur(4.5, 4.5)))
            dst = skia.Rect.MakeXYWH(W / 2 - W / 2 * sc, 1050 - 1050 * sc, W * sc, H * sc)
            c.drawImageRect(self.mini.makeImageSnapshot(), dst, skia.SamplingOptions() if sc == 1.0 else lin,
                            skia.Paint(BlendMode=skia.BlendMode.kPlus, Color=K.col((255, 255, 255), 0.62 * a)))
            c.drawImageRect(img, dst, lin, skia.Paint(Color=K.col((255, 255, 255), a)))
        if textos:
            c.drawImage(self.velo, 0, 0)
            if self.escenas[ie][0] != "cierre":
                marca_agua(c, ie)
                rotulo(c, b, t, self.golpes[gi + 1] if gi + 1 < len(self.golpes) else None)
                if b.get("fuente"):
                    K.text(c, b["fuente"], W / 2, 1474, 29, CREMA, 0.8 * eo((t - b["t0"]) / 0.5), bold=False)
                subtitulos(c, self.trozos, t)
        return self.sf

    def bytes(self, t):
        return self.cuadro(t).makeImageSnapshot().tobytes()

    def imagen(self, t, textos=True):
        from PIL import Image
        im = self.cuadro(t, textos).makeImageSnapshot()
        a = im.toarray(colorType=skia.kRGBA_8888_ColorType)
        return Image.fromarray(a[..., :3].copy())


def render(g, out, seed=0):
    import fx, soundfile as sf
    clips, tiempos = _voz(g)
    golpes, escenas, total = linea_tiempo(g, clips, tiempos)
    M = Montaje(g, golpes, escenas, total, seed)
    # miniatura para el móvil de «pásaselo»: el segundo golpe del vídeo, sin textos
    th = M.imagen(min(golpes[1]["t0"] + 0.9, golpes[1]["t1"] - 0.05), textos=False).crop((0, 300, W, 1620)).resize((500, 611))
    from PIL import Image
    lienzo = Image.new("RGB", (500, 900), (9, 9, 10)); lienzo.paste(th, (0, 110))
    M.extra["_thumb"] = skia.Image.fromarray(np.ascontiguousarray(np.asarray(lienzo.convert("RGBA"))), colorType=skia.kRGBA_8888_ColorType)
    # ---- audio: voz + música + efectos
    n = int(SR * (total + 0.2))
    vo = np.zeros(n, np.float32)
    for b, c_ in zip(golpes, clips):
        i = int(b["v0"] * SR); j = min(n, i + len(c_)); vo[i:j] += c_[: j - i]
    music = fx.premium_beat(total + 0.3, 92, seed=seed, energy=1.15)
    music = np.pad(music, (0, max(0, n - len(music))))[:n]
    venv = np.convolve((np.abs(vo) > 0.01).astype(np.float32), np.ones(3000) / 3000, "same")
    sfx = np.zeros(n, np.float32)

    def put(a, at, gain=1.0):
        i = int(at * SR)
        if i < 0:
            a = a[-i:]; i = 0
        j = min(n, i + len(a))
        if j > i:
            sfx[i:j] += a[: j - i] * gain
    put(fx.impact(), 0.0, 0.5)
    for ie, (nombre, bs) in enumerate(escenas[1:], 1):
        put(fx.whoosh2(0.4), bs[0]["t0"] - 0.22, 0.55)
    for b in golpes:
        if b.get("rotulo"):
            put(fx.blip(1 if b.get("tachado") else 0), b["t0"] + 0.12, 0.5)
        if b.get("tachado"):
            put(fx.whoosh2(0.25), b["t0"] + 0.55, 0.4)
        if b.get("escena") in ("cifra", "barras"):
            put(fx.shimmer(), b["t0"] + 0.5, 0.35)
    put(fx.shimmer(), golpes[-1]["t0"] + 0.15, 0.5)
    mix = vo * 1.15 + sfx + music * (0.42 - 0.30 * np.clip(venv * 3, 0, 1))
    mix = fx.dehiss(np.tanh(mix * 1.05) * 0.92)
    wav = out.replace(".mp4", ".wav")
    sf.write(wav, mix, SR)
    sf.write(out.replace(".mp4", "_voz.wav"), np.tanh((vo * 1.15 + sfx) * 1.05) * 0.92, SR)       # TikTok con su música
    # ---- vídeo
    fmt = "rgba"
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", fmt, "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", wav, "-shortest", "-c:v", "libx264", "-preset", "veryfast",
                             "-profile:v", "high", "-crf", "19", "-maxrate", "9M", "-bufsize", "14M", "-g", str(FPS * 2),
                             "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                             "-ac", "2", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        proc.stdin.write(M.bytes(fi / FPS))
    proc.stdin.close(); proc.wait()
    if os.path.exists(wav):
        os.remove(wav)
    if proc.returncode:
        raise RuntimeError("ffmpeg falló al codificar el reel explicado")
    return {"duration": round(total, 1), "golpes": golpes, "montaje": M,
            "lineas": [b["voz"] for b in g["golpes"]] + [g["compartir"]]}


# ------------------------------------------------------------------ portada
def portada(g, info, path):
    M = info["montaje"]; golpes = info["golpes"]
    k = int(g.get("portada", 1))
    b = golpes[min(k, len(golpes) - 3)]
    sf_ = M.cuadro(min(b["t0"] + 1.4, b["t1"] - 0.05), textos=False)
    c = sf_.getCanvas()
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, 900)], [K.col(NEGRO, 0.9), K.col(NEGRO, 0.0)])
    c.drawRect(skia.Rect.MakeWH(W, 900), skia.Paint(Shader=sh))
    size, ls = K.fit(g["hook"], 118, 940, 3, min_size=70)
    y0 = 430
    for i, l_ in enumerate(ls):
        K.text(c, l_, W / 2, y0 + i * size * 1.1, size, CREMA if i % 2 == 0 or len(ls) == 1 else ORO_L, 1.0, outline=18)
    K.rrect(c, W / 2 - 190, 250, 380, 62, 10, ORO, None, 0)                       # etiqueta sobre el titular (no tapa el dibujo)
    K.text(c, "EXPLICADO EN 40 S", W / 2, 293, 30, NEGRO, 1, track=0.08)
    K.rrect(c, 34, 34, W - 68, H - 68, 4, None, ORO_D, 3, 0.9)
    from PIL import Image
    a = sf_.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    Image.fromarray(a[..., :3].copy()).save(path, "JPEG", quality=92)
    return path


# ------------------------------------------------------------------ revisión
def revisar(path, g, info):
    import gemini
    small = path.replace(".mp4", "_rev.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf", "scale=360:640", "-r", "12", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "30", "-c:a", "aac", "-b:a", "64k", small], check=True)
        data = base64.b64encode(open(small, "rb").read()).decode()
        rot = [b.get("rotulo") for b in g["golpes"] if b.get("rotulo")]
        res = gemini.ask([{"text": f"""Eres director creativo de una cuenta de TikTok, Instagram y YouTube Shorts para ESTUDIANTES DE
ARQUITECTURA (TFM, TFG, Proyectos). VE y ESCUCHA este reel EXPLICATIVO ANIMADO (ilustración vectorial amarilla sobre fondo
oscuro, a propósito; subtítulos palabra a palabra arriba; rótulos grandes; voz sintética de España, a propósito).
Titular: «{g['hook']}».  Guion (voz): {' / '.join(info['lineas'])}   Rótulos: {rot}
Comprueba SOLO defectos objetivos: que la voz diga el guion (sin frases repetidas, cortadas ni palabras leídas letra a
letra) con acento de España; que subtítulos y rótulos se lean en el móvil, no se pisen ni los tape la interfaz; que
ningún dibujo salga roto, cortado o superpuesto de forma ilegible; que cada dibujo tenga que ver con lo que se dice; que
el primer segundo enganche; y que NO se diga ni insinúe que alguien hace el TFM por el alumno (eso es defecto grave).
NO es defecto: el rótulo tachado, el estilo de dibujo, la voz sintética ni que los subtítulos vayan una fracción de
segundo por delante o por detrás de la voz.
ESCALA ANCLADA: 8 = profesional y publicable SIN defectos objetivos (lo opinable va en "suggestions"); 6-7 = algún
defecto objetivo; 5 o menos = grave. Devuelve JSON: {{"overall": number, "issues": [str], "suggestions": [str], "critical": bool}}"""},
                          {"inline_data": {"mime_type": "video/mp4", "data": data}}], 0.3)
    except Exception as e:
        say("revisión no disponible:", str(e)[:200])
        return {"overall": 0, "issues": [f"revisor no disponible: {str(e)[:100]}"]}
    finally:
        if os.path.exists(small):
            os.remove(small)
    ov = float(res.get("overall") or 0)
    if ov < 8 and not (res.get("issues") or []) and not res.get("critical"):
        res["overall_raw"] = ov; ov = 8.0
    res["overall"] = ov
    try:
        with open(os.path.join(HERE, "review_log.jsonl"), "a") as f:
            f.write(json.dumps({"date": str(datetime.date.today()), "kind": "video", "tematica": "explicado", "hook": g["hook"],
                                **{k: res.get(k) for k in ("overall", "issues", "suggestions")}}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    say(f"revisión: {ov}/10", res.get("issues") or "")
    return res


def descripcion(g):
    cuerpo = g.get("descripcion") or ""
    puntos = "\n".join(f"▪️ {p}" for p in g.get("puntos", []))
    tags = g.get("hashtags") or "#tfmarquitectura #arquitectura #estudiantesdearquitectura #tfm #proyectosarquitectura"
    return (f"{g['hook']} 👇\n{g.get('busqueda', 'tfm arquitectura · consejos tfm · estudiante de arquitectura')}\n\n"
            f"{cuerpo}\n\n{puntos}\n\n📩 {g['compartir']}\n💬 {g.get('pregunta', '¿Te ha pasado? Cuéntalo en comentarios.')}\n"
            f"📌 Guárdalo para tu próxima entrega.\n\n{marca.CTA_SUAVE}\n\n{tags}").replace("\n\n\n\n", "\n\n")


# ------------------------------------------------------------------ todo junto
def hacer(out, seed=0, max_rondas=2, cual=None):
    import voz
    t0 = time.time()
    g = elegir(seed, cual or os.environ.get("EXPLICADO_ID") or None)
    err = validar(g)
    if err:
        raise RuntimeError(f"guion {g['id']} no válido: {err[:3]}")
    say(f"«{g['hook']}» ({g['id']}) · {len(g['golpes'])} golpes")
    rev, rondas = {}, 0
    for ronda in range(max_rondas):
        rondas += 1
        info = render(g, out, seed=f"{seed}-{ronda}")
        if not os.environ.get("GEMINI_API_KEY"):
            rev = {"overall": None}; break
        rev = revisar(out, g, info)
        if rev["overall"] >= 8 and not rev.get("critical"):
            break
    else:
        raise RuntimeError(f"explicado sin el 8: {rev.get('overall')} · {(rev.get('issues') or [''])[:2]}")
    cover = portada(g, info, out.replace(".mp4", "_portada.jpg"))
    cap = descripcion(g)
    if not marca.limpio(cap):
        raise RuntimeError("la descripción contiene una promesa prohibida")
    open(out.replace(".mp4", ".txt"), "w").write(cap)
    for extra in (out.replace(".mp4", "_voz.wav"),):
        if os.path.exists(extra):
            os.remove(extra)
    meta = {"tematica": "explicado", "hook": g["hook"], "hook_voz": g["golpes"][0]["voz"], "duration": info["duration"],
            "cover": cover, "thumb_ms": 1200, "review_score": rev.get("overall"), "ids": [f"explicado:{g['id']}"],
            "voz": voz.ENGINE, "venta": False, "solucion": None, "titulo": (g["hook"] + " · TFM de arquitectura")[:95],
            "montajes": rondas, "pregunta": g.get("pregunta"), "segundos": round(time.time() - t0)}
    say(f"listo en {meta['segundos']} s · {info['duration']} s de vídeo · nota {rev.get('overall')}")
    return meta


# ------------------------------------------------------------------ el banco se amplía solo
DOC_ESCENAS = """despacho: tu mesa de trabajo vista desde atrás (monitor, reloj, calendario, pila de tareas, tú). p: hora (0-24), luz
  ("noche"/"dia"), pantalla ("plano" | "pendientes" + pendientes:int | "correo" + correos:int | "aviso" + aviso:str +
  aviso_color | "vacia" | "ok"), pila (0-6) + pila_color ("coral"), pose ("trabaja" | "agobio" | "celebra" | "mira"),
  entrega (bool: día de entrega marcado en el calendario).
lamina: los 7 bloques de un TFM (Urbanismo, Planos, Construcción, Instalaciones, Estructuras, Imágenes 3D, Memoria) como un
  panel que se llena. p: hechos (0-7 cerrados), resaltar (lista de índices atascados, en coral), activo (índice).
tribunal: la mesa del tribunal o del tutor con tu panel detrás. p: miembros (1-3), gesto ("duda" | "ok" | "no"), foco.
rejilla: N iconos. p: n (3-40), cols, icono ("doc" | "casa" | "persona" | "calendario"), resaltar (int o lista),
  resaltar_fin (bool), color ("oro_l" | "coral"), numeros (bool), marca ("check" | "cruz").
barras: p: barras = [{"e": etiqueta, "v": 0-100, "c": "oro" | "oro_l" | "coral", "t": texto encima}] (2 o 3).
cifra: un número grande. p: valor, desde, sufijo, sub (texto debajo), dur.
curva: una línea a lo largo del curso. p: datos (lista de 0 a 1), eje (etiquetas), eje_texto, resalta ("picos" |
  "valles"), txt_picos, txt_valles, capacidad ("fija" + nivel + cap_texto).
plano: una planta que se dibuja. p: capas (lista de "cotas", "estructura", "fontaneria", "electricidad"), etiqueta.
flujo: tres pasos. p: pasos = [{"t": texto, "i": "lapiz" | "planos" | "firma" | "doc" | "persona" | "calendario",
  "c": "coral"}], activo (índice o lista).
versus: dos columnas. p: a = {"t": título, "filas": [str]}, b = {...}, n (filas visibles).
equipo: p: propios (int, tú), extra (int, quien te acompaña), extra_texto, saturado (bool)."""
HECHOS_AC = """- AC · ArquitecturaConfidencial es asesoría y acompañamiento para el TFM, TFG y PFC de arquitectura.
- Ofrece una auditoría gratuita del TFM: rellenas el formulario de la web con tu proyecto y tu fecha de entrega; en una
  llamada se ve dónde estás, qué te falta y qué pide tu escuela; y sales con un plan por fases.
- Acompaña en planificación, revisión técnica y apoyo en las fases que se atascan (planos, construcción, estructuras,
  instalaciones, imágenes, memoria). El proyecto, las decisiones y la defensa son SIEMPRE del alumno.
- Web: arquitecturaconfidencial.com"""


def _numeros_ok(g, hechos=""):
    """Sin estadísticas ni cifras inventadas: solo números pequeños de uso cotidiano (semanas, bloques, pasos)."""
    todo = " ".join(b.get("voz", "") + " " + b.get("rotulo", "") for b in g["golpes"]) + " " + g.get("descripcion", "") + " " + g.get("hook", "")
    malos = sorted({n for n in re.findall(r"\d[\d.,]*%?", todo) if "%" in n or len(re.sub(r"\D", "", n)) >= 3
                    or (re.sub(r"\D", "", n) and int(re.sub(r"\D", "", n)) > 30 and n not in ("1:20", "1:50", "1:100"))})
    return not malos, malos


def ampliar(n=3, forzar=False, prueba=False):
    """Cuando quedan 2 guiones sin usar (o menos), un agente escribe guiones nuevos con la misma estructura y el mismo
    enfoque de asesoría. Solo entran los que pasan el validador (reglas de marca incluidas), un verificador
    independiente y un montaje de prueba."""
    import gemini
    B = json.load(open(BANCO)); G = B["guiones"]; u = _usados()
    libres = [g for g in G if f"explicado:{g['id']}" not in u]
    if len(libres) > 2 and not forzar:
        return say(f"banco: {len(libres)} guiones sin usar de {len(G)}; no hace falta ampliar")
    nuevos = []
    ej = [g for g in G if not g.get("auto")][:12]
    rng = random.Random(str(datetime.date.today()))
    for intento in range(n * 3):
        if len(nuevos) >= n:
            break
        e1, e2 = rng.sample(ej, 2)
        try:
            g = gemini.ask(f"""Eres guionista de reels EXPLICATIVOS ANIMADOS para AC · ArquitecturaConfidencial. Público: estudiantes de
arquitectura de España (22-28 años) agobiados con su TFM, TFG o la asignatura de Proyectos.
Escribe UN guion nuevo que ENSEÑE algo útil y aplicable hoy sobre un atasco real (planificación, correcciones, tribunal,
paneles, memoria, estructura, instalaciones, construcción, renders, bloqueo, defensa…), distinto de estos titulares:
{[x['hook'] for x in G + nuevos]}

ENFOQUE OBLIGATORIO: asesoría y acompañamiento. El proyecto, las decisiones y la defensa son del alumno. PROHIBIDO decir o
insinuar que alguien hace el TFM por él, «delegar el TFM», ocultar nada al tutor, prometer aprobados o notas, y la
palabra «confidencial». AC, como mucho, aparece en un golpe como quien revisa, planifica contigo o te acompaña.
Sin estadísticas ni porcentajes; sin normativa; sin cifras grandes.

ESTRUCTURA OBLIGATORIA (9-12 golpes; cada golpe = una frase hablada de 4-17 palabras + una escena):
1) escena en segunda persona con un giro  2) el mito, tachado («Y no, no es que…»; "tachado": true y el rótulo = lo
tachado)  3) el porqué, explicado con el dibujo  4) la salida, en pasos concretos  5) el reencuadre, último golpe («No
es X: es Y»).  Y aparte "compartir": «Pásaselo a ese compañero que…».
Tono: de compañero mayor a compañero, español de España (tú), frases cortas, con algo de humor de escuela.
LO ÚNICO que puedes afirmar sobre AC:
{HECHOS_AC}

ESCENAS disponibles («=» = sigue en la escena anterior cambiando solo los parámetros que indiques en "p"):
{DOC_ESCENAS}
Cada golpe: {{"voz", "escena", "p": {{}}, "rotulo" (máx. 22 caracteres, opcional), "color" ("oro_l" | "coral" | "crema"),
"tachado" (bool), "claves" ([palabra de la voz a resaltar]), "cam" ([x, y, zoom 1-1.25], opcional),
"tono" ("giro" | "porque" | "dato" | "salida" | "reencuadre")}}.
EJEMPLOS de nuestro estilo:
{json.dumps(e1, ensure_ascii=False)}
{json.dumps(e2, ensure_ascii=False)}

Devuelve SOLO el JSON del guion: {{"id" (minúsculas_con_guion_bajo), "hook" (titular de portada, máx. 42 caracteres),
"portada" (índice del golpe más vistoso), "golpes": [...], "compartir", "pregunta" (para comentarios), "descripcion"
(2 frases), "puntos": [3 ideas]}}""", 0.9)
            g["id"] = re.sub(r"[^a-z0-9_]", "", str(g.get("id", "")).lower())[:24] or f"auto{len(G) + len(nuevos)}"
            if any(x["id"] == g["id"] for x in G + nuevos):
                g["id"] += f"_{len(G) + len(nuevos)}"
            err = validar(g)
            ok_n, malos = _numeros_ok(g)
            if err or not ok_n:
                say("guion descartado:", g.get("hook"), err[:2], malos[:4]); continue
            v = gemini.ask(f"""Eres verificador de una cuenta para estudiantes de arquitectura. Reglas: el guion debe dar consejos
sensatos y ciertos sobre cómo sacar adelante un TFM; NO puede decir ni insinuar que alguien hace el TFM por el alumno, ni
prometer notas o aprobados, ni inventar estadísticas; sobre AC solo puede afirmar esto:\n{HECHOS_AC}\nGUION:\n
{json.dumps(g, ensure_ascii=False)}\nDevuelve JSON: {{"ok": bool, "motivo": str}}""", 0.1)
            if not v.get("ok"):
                say("guion rechazado por el verificador:", g.get("hook"), str(v.get("motivo"))[:160]); continue
            clips = [np.zeros(int(SR * (0.45 * len(b["voz"].split()) + 0.4)), np.float32) for b in g["golpes"]] + [np.zeros(SR * 3, np.float32)]
            tms = [[(i * 0.4, w) for i, w in enumerate(b["voz"].split())] for b in g["golpes"]] + [[(i * 0.4, w) for i, w in enumerate(g["compartir"].split())]]
            go, es, tot = linea_tiempo(g, clips, tms); M = Montaje(g, go, es, tot, 1)
            for b in go:
                M.cuadro(b["t0"] + (b["t1"] - b["t0"]) * 0.8)
            g["auto"] = True; g["fecha"] = str(datetime.date.today())
            nuevos.append(g); say("guion nuevo:", g["hook"])
        except Exception as e:
            say("intento de guion fallido:", str(e)[:200])
    if prueba:
        print(json.dumps(nuevos, ensure_ascii=False, indent=1)); return nuevos
    if nuevos:
        B["guiones"] += nuevos
        json.dump(B, open(BANCO, "w"), ensure_ascii=False, indent=1)
    say(f"{len(nuevos)} guiones nuevos en el banco")
    return nuevos


if __name__ == "__main__":
    if "--ampliar" in sys.argv:
        ampliar(forzar="--forzar" in sys.argv, prueba="--prueba" in sys.argv); sys.exit(0)
    if "--lista" in sys.argv:
        u = _usados()
        for g in banco():
            print(f"{u.count('explicado:' + g['id']):>2}  {g['id']:<22} {g['hook']}")
    elif "--valida" in sys.argv:
        mal = 0
        for g in banco():
            e = validar(g)
            print(("✗ " if e else "✓ ") + g["id"], e or "")
            mal += bool(e)
        sys.exit(1 if mal else 0)
    elif "--render" in sys.argv:
        i = sys.argv.index("--render")
        g = elegir(0, sys.argv[i + 1]); out = sys.argv[i + 2]
        t0 = time.time(); info = render(g, out, seed=1)
        portada(g, info, out.replace(".mp4", "_portada.jpg"))
        print("render", round(time.time() - t0), "s ·", info["duration"], "s de vídeo")

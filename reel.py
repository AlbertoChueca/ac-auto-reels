"""Motor de reels de AC con voz: imágenes (IA o portfolio real), voz expresiva, subtítulos al ritmo de la voz, música que
baja cuando se habla y la web visible en TODOS los fotogramas.

Tipos de montaje:
    lista     tips_tfm, tips_proyectos, referentes, ia, documentacion, auditoria: gancho + N escenas + cierre
    quiz      test, vf, encuesta: pregunta, opciones, cuenta atrás (la solución NO sale: la publica el bot mañana)
    postpro   render sin y con postproducción: 3 parejas con cortinilla

Velocidad: los agentes preparan el guion; después imágenes y voz se generan A LA VEZ; un solo montaje; revisión del
vídeo con audio (mínimo 8). Si no llega: se rehacen solo las imágenes o la voz que señala el revisor (máx. 3 montajes).
"""
import base64, datetime, glob, io, json, math, os, random, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx
import marca
from fx import W, H, FPS, SR, F_BOLD, F_REG, clamp, eo, eob

HERE = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(HERE, "fuentes", "banco.json")
PORTFOLIO = os.path.join(HERE, "assets", "portfolio")
LISTA = ["tips_tfm", "tips_proyectos", "referentes", "ia", "documentacion", "auditoria"]
QUIZ = ["test", "vf", "encuesta"]
TEMATICAS = LISTA + QUIZ + ["postpro"]
NOMBRE = {"tips_tfm": "Tips para el TFM", "tips_proyectos": "Tips para la asignatura de Proyectos",
          "referentes": "Referentes para proyectar", "ia": "IA para arquitectura", "documentacion": "Documentación (venta)",
          "auditoria": "Auditoría gratuita (venta)", "test": "Test", "vf": "Verdadero o falso", "encuesta": "Encuesta",
          "postpro": "Render sin y con postproducción"}
ACENTO, CLARO, OSCURO = fx.AMARILLO, fx.PAPEL, fx.TINTA
FOTO = "Fotografía de arquitectura de revista: luz natural bonita, colores reales, encuadre editorial, nítida"
REGLAS = ("Imagen vertical 9:16. NADA de texto, letras, números, rótulos, cotas legibles ni logotipos. Arquitectura "
          "ORIGINAL y verosímil (nunca un edificio famoso o reconocible), construcción coherente, sin personas "
          "identificables (si aparecen, de espaldas o desenfocadas).")
SAFE_TOP, SAFE_BOT = 250, 1480
GRID = (240, 1680)
WEB = marca.WEB
LETRAS = "ABCD"


def say(*a):
    print("reel:", *a, flush=True)


# ------------------------------------------------------------------ banco
def _usados():
    try:
        return {x["id"] for x in json.load(open(os.path.join(HERE, "used.json")))}
    except Exception:
        return set()


def pieza(tematica, seed=0):
    B = json.load(open(BANCO)); rng = random.Random(str(seed)); us = _usados()
    lista = B[tematica]
    frescas = [p for p in lista if f"{tematica}:{p['id']}" not in us] or lista
    if tematica == "postpro":
        rng.shuffle(frescas)
        el = (frescas + [p for p in lista if p not in frescas])[:3]
        return {"id": "+".join(p["id"] for p in el), "ids": [f"postpro:{p['id']}" for p in el], "escenas_pp": el,
                "hook": "Tu render sin y con postproducción"}
    p = json.loads(json.dumps(rng.choice(frescas))); p["ids"] = [f"{tematica}:{p['id']}"]
    if tematica in ("test", "vf"):                     # la correcta va primera en el banco: se baraja
        ops = list(p["opciones"]); buena = ops[0]
        ops = ["Verdadero", "Falso"] if tematica == "vf" else (rng.shuffle(ops) or ops)
        p["opciones"] = ops; p["correcta"] = ops.index(buena)
    return p


def solucion(tematica, P):
    if tematica not in QUIZ:
        return None
    s = {"tipo": tematica, "pregunta": P["pregunta"], "opciones": P["opciones"],
         "letras": "VF" if tematica == "vf" else LETRAS[:len(P["opciones"])]}
    if tematica != "encuesta":
        s.update(correcta=P["correcta"], explicacion=P["explicacion"])
    return s


# ------------------------------------------------------------------ imágenes
def revisa(img, idea):
    """Directora de arte (revisión): solo defectos objetivos. (ok, motivo)."""
    import gemini
    b = io.BytesIO(); im = img.copy(); im.thumbnail((640, 640)); im.convert("RGB").save(b, "JPEG", quality=82)
    try:
        r = gemini.ask([{"text": f"""Revisa esta imagen para un reel de arquitectura para estudiantes. Debía mostrar: {idea[:400]}.
Rechaza (ok=false) SOLO por un defecto objetivo visible en el móvil: texto, letras o números legibles; geometría
imposible (escaleras sin sentido, ventanas o muebles deformados, objetos fundidos); un edificio famoso reconocible;
caras reconocibles; algo inquietante; o que no se parezca a lo pedido. El estilo NO es motivo de rechazo.
Devuelve JSON: {{"ok": bool, "problemas": [str]}}"""},
                        {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}], 0.2)
        return bool(r.get("ok")), "; ".join(r.get("problemas") or [])[:300]
    except Exception as e:
        return True, f"revisora no disponible ({str(e)[:80]})"


def gen(prompt, refs=(), revisar=True, intentos=3, estilo=FOTO):
    if os.environ.get("IMAGEN") == "mock":
        r = random.Random(prompt); im = Image.new("RGB", (768, 1365), tuple(r.randint(60, 200) for _ in range(3)))
        d = ImageDraw.Draw(im)
        for _ in range(14):
            x, y = r.randint(0, 700), r.randint(0, 1300)
            d.rectangle([x, y, x + r.randint(60, 300), y + r.randint(60, 400)], fill=tuple(r.randint(0, 255) for _ in range(3)))
        return im
    import gemini
    idea = prompt
    for k in range(intentos):
        try:
            img = gemini.image(f"{estilo}. {idea}. {REGLAS}" if estilo else f"{idea}. {REGLAS}", "9:16", refs)
        except Exception as e:
            say("imagen no generada:", str(e)[:150]); continue
        if not revisar:
            return img
        ok, why = revisa(img, prompt)
        try:
            with open(os.path.join(HERE, "image_log.jsonl"), "a") as f:
                f.write(json.dumps({"date": str(datetime.date.today()), "idea": prompt[:160], "ok": ok, "problemas": why},
                                   ensure_ascii=False) + "\n")
        except Exception:
            pass
        if ok:
            return img
        say(f"directora de arte rechaza ({why[:100]}); intento {k + 2}")
        idea = f"{prompt}. Evita esto: {why[:200]}"
    return None


def portfolio(cat, seed):
    """Plano real (anónimo) del portfolio: assets/portfolio/<cat>/ (o un archivo concreto «cat/archivo.jpg»), montado
    como lámina vertical sobre papel. None si no hay."""
    if cat.endswith((".jpg", ".png")):
        fs = [os.path.join(PORTFOLIO, cat)] if os.path.exists(os.path.join(PORTFOLIO, cat)) else []
    else:
        fs = sorted(glob.glob(os.path.join(PORTFOLIO, cat, "*.jp*g")) + glob.glob(os.path.join(PORTFOLIO, cat, "*.png")))
    if not fs:
        return None
    try:
        return lamina(Image.open(random.Random(str(seed)).choice(fs)).convert("RGB"))
    except Exception:
        return None


def lamina(img):
    """El plano entero sobre papel, en vertical (el zoom lento del montaje enseña el detalle)."""
    base = Image.new("RGB", (W, H), (244, 241, 234))
    im = img.copy(); im.thumbnail((W - 40, 760), Image.LANCZOS)
    sh = Image.new("RGBA", (im.width + 60, im.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([30, 34, im.width + 30, im.height + 34], fill=(0, 0, 0, 60))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    y = int(700 - im.height / 2); x = (W - im.width) // 2
    base.paste(sh.convert("RGB"), (x - 30, y - 30), sh)
    base.paste(im, (x, y))
    return base


SIN_POSTPRO = ("Render arquitectónico SIN postproducción, recién salido de un motor básico: materiales grises y planos, "
               "cielo blanco liso, luz plana, sin vegetación ni personas. De")
CON_POSTPRO = ("El MISMO render de la imagen de referencia (mismo edificio, misma geometría, MISMA cámara) tras una "
               "postproducción profesional: cielo de atardecer, luz cálida, sombras marcadas, materiales con textura, "
               "vegetación, personas desenfocadas de espaldas y una ligera atmósfera")


def imagenes(tematica, P, prompts, seed=0):
    """[(imagen, es_portfolio)] por escena (lista), [img] (quiz) o [(sin, con)] (postpro)."""
    with ThreadPoolExecutor(6) as ex:
        if tematica in QUIZ:
            img = gen(P["idea"])
            if img is None:
                raise RuntimeError("quiz: sin imagen de fondo aprobada")
            return [(img, False)]
        if tematica == "postpro":
            def par(e):
                a = gen(f"{SIN_POSTPRO} {e['descripcion']}", estilo="")
                d = gen(CON_POSTPRO, [a]) if a is not None else None
                return (a, d) if d is not None else None
            pares = [x for x in ex.map(par, P["escenas_pp"]) if x]
            if len(pares) < 2:
                raise RuntimeError("postpro: menos de 2 parejas aprobadas")
            return pares
        cats = P.get("portfolio") or []
        reales = [portfolio(cats[k], f"{seed}-{k}") if k < len(cats) and cats[k] else None for k in range(len(prompts))]
        fs = [None if reales[k] is not None else ex.submit(gen, prompts[k]) for k in range(len(prompts))]
        out = [(reales[k], True) if reales[k] is not None else (fs[k].result(), False) for k in range(len(prompts))]
    if sum(1 for im, _ in out if im is None) > 1:
        raise RuntimeError("lista: faltan imágenes aprobadas")
    return out


# ------------------------------------------------------------------ piezas gráficas
def _cover_fit(img, zoom=1.0):
    iw, ih = img.size; s = max(W / iw, H / ih) * zoom
    im = img.resize((int(iw * s), int(ih * s)), Image.BICUBIC)
    x = (im.width - W) // 2; y = (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def _plano(img, seed, oscuro=0.0):
    r = random.Random(str(seed))
    z0, z1 = (1.0, 1.12) if r.random() < 0.6 else (1.12, 1.0)
    c0 = (r.uniform(0.35, 0.65), r.uniform(0.4, 0.6)); c1 = (r.uniform(0.35, 0.65), r.uniform(0.4, 0.6))
    iw, ih = img.size; s = max(W / iw, H / ih) * 1.14
    big = img.convert("RGB").resize((int(iw * s), int(ih * s)), Image.BICUBIC)
    if oscuro:
        big = Image.blend(big, Image.new("RGB", big.size, OSCURO), oscuro)
    bw, bh = big.size; base = min(bw / W, bh / H)

    def f(p):
        p = clamp(p); z = z0 + (z1 - z0) * eo(p); c = (c0[0] + (c1[0] - c0[0]) * p, c0[1] + (c1[1] - c0[1]) * p)
        ww, wh = W * base / z, H * base / z; x = (bw - ww) * c[0]; y = (bh - wh) * c[1]
        return big.resize((W, H), Image.BILINEAR, box=(x, y, x + ww, y + wh))
    return f


_GRAD = []


def _degradados():
    if not _GRAD:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
        for y in range(0, 620, 4):
            d.rectangle([0, y, W, y + 4], fill=(0, 0, 0, int(170 * (1 - y / 620) ** 1.6)))
        for y in range(900, H, 4):
            d.rectangle([0, y, W, y + 4], fill=(0, 0, 0, int(225 * ((y - 900) / (H - 900)) ** 1.2)))
        _GRAD.append(g)
    return _GRAD[0]


def _panel(im, pad=36, alpha=150):
    w, h = im.width + 2 * pad, im.height + 2 * pad
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([pad // 2, pad // 2, w - pad // 2, h - pad // 2], 40, fill=(0, 0, 0, alpha))
    p = p.filter(ImageFilter.GaussianBlur(pad / 2)); p.alpha_composite(im, (pad, pad))
    return p


def _hot(t):
    return tuple(w.lower().strip("¿?¡!.,:") for w in t.split()
                 if w[:1].isdigit() or w.strip("¿?¡!.,:").upper() in ("TFM", "IA", "PROYECTOS", "TRIBUNAL", "GRATIS", "GRATUITA"))


def _web_pill():
    return fx.pill(WEB, 34, (14, 16, 20, 200), CLARO, padx=26, pady=12, radius=8, outline=ACENTO)


def _cierre_marca():
    return fx.logo(96, CLARO, ACENTO), fx.pill(WEB, 50, ACENTO, OSCURO, padx=36, pady=18, radius=8)


def _trozos(texto, n=6):
    """Subtítulos: grupos de hasta n palabras (sin dejar una sola palabra al final)."""
    ws = texto.split(); out = []
    while ws:
        k = n if len(ws) > n + 1 else len(ws)
        out.append(" ".join(ws[:k])); ws = ws[k:]
    return out


def _subs(texto):
    """[(t0_rel, t1_rel, imagen)] proporcional a la longitud de cada trozo (0-1 del clip)."""
    tr = _trozos(texto); tot = sum(len(t) + 3 for t in tr); acc = 0; out = []
    for t in tr:
        a = acc / tot; acc += len(t) + 3
        im = fx.headline(t, 56, 920, 2, color=CLARO, hot=ACENTO, hot_words=_hot(t), shadow=True)
        out.append((a, acc / tot, _panel(im, 20, 120)))
    return out


def _opcion(letra, texto, ancho=900):
    size = fx.fit_font(texto, F_BOLD, 46, ancho - 180, 2, 34)
    tx = fx.text_block(texto, F_BOLD, size, ancho - 180, CLARO)
    h = max(108, tx.height + 30)
    im = Image.new("RGBA", (ancho, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, ancho - 1, h - 1], 28, fill=(20, 22, 27, 225), outline=ACENTO, width=3)
    d.ellipse([28, h / 2 - 36, 100, h / 2 + 36], fill=ACENTO)
    f = fx.font(F_BOLD, 46); bb = f.getbbox(letra)
    d.text((64 - (bb[2] - bb[0]) / 2 - bb[0], h / 2 - (bb[3] - bb[1]) / 2 - bb[1]), letra, font=f, fill=OSCURO)
    im.alpha_composite(tx, (128, int((h - tx.height) / 2) + 6))
    return im


# ------------------------------------------------------------------ audio
def _mezcla(total, voces, cortes, extra, seed, bpm):
    """voces: [(t0, clip)]. La música baja cuando se habla (ducking)."""
    n = int(SR * (total + 0.3))
    music = fx.premium_beat(total + 0.3, bpm, seed=str(seed), energy=1.1, jitter=False)
    music = np.pad(music, (0, max(0, n - len(music))))[:n]
    vo = np.zeros(n, np.float32); sfx = np.zeros(n, np.float32)

    def put(buf, a, at, g=1.0):
        i = int(at * SR)
        if i < 0: a = a[-i:]; i = 0
        j = min(n, i + len(a)); buf[i:j] += a[: j - i] * g
    for t0, c in voces:
        put(vo, c, t0)
    env = np.convolve(np.abs(vo), np.ones(int(SR * 0.25)) / int(SR * 0.25), "same")
    duck = 1 - 0.72 * clamp_arr(env / (np.percentile(env[env > 0], 80) if np.any(env > 0) else 1))
    put(sfx, fx.impact(), 0.0, 0.6)
    for t in cortes:
        put(sfx, fx.whoosh2(0.4), t - 0.3, 0.45); put(sfx, fx.impact(), t, 0.2)
    for snd, at, g in extra:
        put(sfx, snd, at, g)
    mix = music * 0.55 * duck + sfx * 0.8 + vo * 1.0
    return fx.dehiss(np.tanh(mix * 1.05) * 0.95)


def clamp_arr(a):
    return np.clip(a, 0, 1)


def _encode(out, frames, mix):
    wav = out.replace(".mp4", ".wav")
    import soundfile as sf
    sf.write(wav, mix, SR)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-shortest", "-c:v", "libx264", "-preset", "veryfast",
                          "-profile:v", "high", "-crf", "20", "-maxrate", "8M", "-bufsize", "12M", "-g", str(FPS * 2),
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for fr in frames:
        p.stdin.write(fr.convert("RGB").tobytes())
    p.stdin.close(); p.wait(); os.remove(wav)
    if p.returncode:
        raise RuntimeError("ffmpeg falló al codificar el reel")


def _cierre(fr, G, lt, lg, web, q, sub):
    a = eob(clamp(lt / 0.4))
    fx.paste_center(fr, q, W / 2, 620 - (1 - a) * 30, alpha=clamp(a))
    b = eob(clamp((lt - 0.4) / 0.4))
    fx.paste_center(fr, sub, W / 2, 620 + q.height / 2 + 80 - (1 - b) * 20, alpha=clamp(b))
    c = clamp((lt - 0.7) / 0.35)
    fx.paste_center(fr, lg, W / 2, 1120, alpha=c)
    d = eob(clamp((lt - 0.9) / 0.4))
    fx.paste_center(fr, web, W / 2, 1260, scale=0.9 + 0.1 * d, alpha=clamp(d))


# ------------------------------------------------------------------ montaje: lista
def render_lista(G, imgs, clips, out, tematica, seed=0, bpm=86):
    """clips: [hook, escena1..N, cierre]. imgs: [(img, real)] por escena."""
    esc = G["escenas"]
    pares = [(e, im) for e, im in zip(esc, imgs) if im[0] is not None]
    idx = [k for k, im in enumerate(imgs) if im[0] is not None]
    clips_esc = [clips[1 + k] for k in idx]
    d_hook = max(1.8, len(clips[0]) / SR + 0.35)
    d_esc = [max(2.4, len(c) / SR + 0.45) for c in clips_esc]
    d_fin = max(3.2, len(clips[-1]) / SR + 0.9)
    t0s = [d_hook]
    for d in d_esc[:-1]:
        t0s.append(t0s[-1] + d)
    t_fin = t0s[-1] + d_esc[-1]; total = t_fin + d_fin
    planos = [_plano(im[0], f"{seed}-{k}") for k, (e, im) in enumerate(pares)]
    hook_big = _panel(fx.headline(G["hook_pantalla"], 116, 960, 3, color=CLARO, hot=ACENTO,
                                  hot_words=_hot(G["hook_pantalla"]), shadow=True), 50, 140)
    tit = _panel(fx.headline(G["hook_pantalla"], 50, 900, 2, color=CLARO, hot=ACENTO, shadow=True), 22, 120)
    labs, subs = [], []
    for k, (e, im) in enumerate(pares):
        num = fx.pill(str(k + 1), 64, ACENTO, OSCURO, padx=30, pady=14, radius=40)
        tx = fx.headline(e["titulo"], 86, 940, 2, color=CLARO, hot=ACENTO, hot_words=_hot(e["titulo"]), shadow=True)
        partes = [num, tx]
        if e.get("sub"):
            partes.append(fx.text_block(e["sub"], F_REG, 38, 900, ACENTO, align="center"))
        if im[1]:
            partes.append(fx.pill("Trabajo real", 30, CLARO, OSCURO, padx=20, pady=8, radius=6))
        elif tematica == "referentes":
            partes.append(fx.text_block("Imagen conceptual creada con IA", F_REG, 26, 900, (200, 196, 186), align="center"))
        hh = sum(p.height for p in partes) + 12 * (len(partes) - 1)
        lab = Image.new("RGBA", (max(p.width for p in partes), hh), (0, 0, 0, 0)); y = 0
        for p in partes:
            lab.alpha_composite(p, ((lab.width - p.width) // 2, y)); y += p.height + 12
        labs.append(_panel(lab, 40, 140)); subs.append(_subs(e["voz"]))
    # posición de cada etiqueta: centrada (o bajo el plano real) y SIEMPRE con sitio para el subtítulo y la web
    ys = []
    for k, (e, im) in enumerate(pares):
        alto_sub = max([s.height for _, _, s in subs[k]] or [0])
        y = 1250 if im[1] else 1060
        ys.append(min(y, SAFE_BOT - 40 - alto_sub - 20 - labs[k].height / 2))
    sub_hook = _subs(G["hook_voz"]) if G["hook_voz"].strip(" .") != G["hook_pantalla"].strip(" .") else []
    fondo_fin = _cover_fit(pares[-1][1][0].convert("RGB")).filter(ImageFilter.GaussianBlur(18))
    fondo_fin = Image.blend(fondo_fin, Image.new("RGB", (W, H), OSCURO), 0.6).convert("RGBA")
    q = fx.headline(G["cierre_pantalla"][0], 96, 960, 2, color=CLARO, hot=ACENTO, hot_words=_hot(G["cierre_pantalla"][0]), shadow=True)
    sub = fx.pill(G["cierre_pantalla"][1], 44, CLARO, OSCURO, padx=34, pady=16, radius=8)
    lg, web = _cierre_marca(); wp = _web_pill(); grad = _degradados()
    voces = [(0.12, clips[0])] + [(t + 0.18, c) for t, c in zip(t0s, clips_esc)] + [(t_fin + 0.35, clips[-1])]
    mix = _mezcla(total, voces, t0s[1:] + [t_fin], [(fx.shimmer(), t_fin + 0.2, 0.4)], seed, bpm)

    def frames():
        for f in range(int(total * FPS)):
            tt = f / FPS
            if tt < t_fin:
                if tt < d_hook:                                       # gancho sobre la primera imagen
                    fr = planos[0](tt / (d_hook + d_esc[0]) * 0.5).convert("RGBA"); fr.alpha_composite(grad)
                    a = eob(clamp(tt / 0.3)); im = hook_big
                    if a < 1:
                        s_ = 0.9 + 0.1 * a; im = im.resize((int(im.width * s_), int(im.height * s_)))
                    fx.paste_center(fr, im, W / 2, 760, alpha=clamp(a * 1.5) * (1 - clamp((tt - d_hook + 0.2) / 0.2)))
                    for a0, a1, s in sub_hook:
                        if a0 <= (tt - 0.12) / max(0.1, len(clips[0]) / SR) < a1:
                            fx.paste_center(fr, s, W / 2, 1330)
                else:
                    k = max(i for i, a in enumerate(t0s) if a <= tt); lt = tt - t0s[k]
                    p = (0.5 + 0.5 * lt / d_esc[0]) if k == 0 else lt / d_esc[k]
                    fr = planos[k](p).convert("RGBA")
                    if k > 0 and lt < 0.16:
                        fr = Image.blend(planos[k - 1](1.0).convert("RGBA"), fr, lt / 0.16)
                    fr.alpha_composite(grad)
                    fx.paste_center(fr, tit, W / 2, SAFE_TOP + 50 + tit.height / 2)
                    a = eob(clamp((lt - 0.05) / 0.35))
                    fx.paste_center(fr, labs[k], W / 2, ys[k] - (1 - a) * 40, alpha=clamp(a))
                    dur_v = max(0.1, len(clips_esc[k]) / SR)
                    for a0, a1, s in subs[k]:
                        if a0 <= (lt - 0.18) / dur_v < a1:
                            fx.paste_center(fr, s, W / 2, ys[k] + labs[k].height / 2 + 20 + s.height / 2)
                fx.paste_center(fr, wp, W / 2, SAFE_BOT + 20)
            else:
                fr = fondo_fin.copy(); _cierre(fr, G, tt - t_fin, lg, web, q, sub)
            yield fr
    _encode(out, frames(), mix)
    return {"duration": round(total, 1), "t_fin": t_fin, "escenas": [e["titulo"] for e, _ in pares], "idx": idx,
            "reales": [k + 1 for k, (e, im) in enumerate(pares) if im[1]]}


# ------------------------------------------------------------------ montaje: quiz
def render_quiz(G, P, img, clips, out, tematica, seed=0, bpm=86):
    """clips: [hook, pregunta, cierre]."""
    ops = P["opciones"]; letras = "VF" if tematica == "vf" else LETRAS
    d_h = len(clips[0]) / SR; d_q = len(clips[1]) / SR
    t_q = 0.15 + d_h + 0.25
    t_ops = [t_q + d_q * 0.55 + 0.55 * k for k in range(len(ops))]
    t_cd = max(t_q + d_q + 0.4, t_ops[-1] + 0.8)
    t_fin = t_cd + 5.0; d_fin = max(3.2, len(clips[2]) / SR + 0.9); total = t_fin + d_fin
    plano = _plano(img, f"{seed}-q", oscuro=0.55)
    tag = fx.pill(G["hook_pantalla"][:34], 44, ACENTO, OSCURO, padx=34, pady=16, radius=8)
    q = fx.headline(P["pregunta"], 80 if len(P["pregunta"]) < 70 else 68, 960, 4, color=CLARO, hot=ACENTO, shadow=True)
    cards = [_opcion(letras[k], o) for k, o in enumerate(ops)]
    gap = 18; y_q = 380 + q.height / 2
    y0 = max(y_q + q.height / 2 + 30, 960 - (sum(c.height for c in cards) + gap * (len(cards) - 1)) / 2)
    cq = fx.headline(G["cierre_pantalla"][0], 96, 960, 2, color=CLARO, hot=ACENTO, shadow=True)
    sub = fx.pill(G["cierre_pantalla"][1], 42, CLARO, OSCURO, padx=32, pady=16, radius=8)
    lg, web = _cierre_marca(); wp = _web_pill(); grad = _degradados()
    voces = [(0.15, clips[0]), (t_q, clips[1]), (t_fin + 0.35, clips[2])]
    extra = [(fx.blip(k), t, 0.5) for k, t in enumerate(t_ops)] + [(fx.tick2(k == 4), t_cd + k, 0.6) for k in range(5)]
    mix = _mezcla(total, voces, [t_fin], extra, seed, bpm)

    def frames():
        for f in range(int(total * FPS)):
            tt = f / FPS
            fr = plano(min(1.0, tt / total)).convert("RGBA"); fr.alpha_composite(grad)
            if tt < t_fin:
                a = eob(clamp(tt / 0.35))
                fx.paste_center(fr, tag, W / 2, 310 - (1 - a) * 20, alpha=clamp(a))
                b = eo(clamp((tt - t_q + 0.3) / 0.4))
                fx.paste_center(fr, q, W / 2, y_q + (1 - b) * 30, alpha=b)
                y = y0
                for k, c in enumerate(cards):
                    e = eob(clamp((tt - t_ops[k]) / 0.35))
                    fx.paste_center(fr, c, W / 2 + (1 - e) * 120, y + c.height / 2, alpha=clamp(e * 1.4))
                    y += c.height + gap
                if tt >= t_cd:
                    k = int(tt - t_cd); s = (tt - t_cd) - k; R = 150
                    f_ = fx.font(F_BOLD, 88); txt = str(5 - k); bb = f_.getbbox(txt)
                    n = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
                    ImageDraw.Draw(n).text((4 - bb[0], 4 - bb[1]), txt, font=f_, fill=ACENTO)
                    ring = Image.new("RGBA", (R, R), (0, 0, 0, 0)); d = ImageDraw.Draw(ring)
                    d.ellipse([6, 6, R - 6, R - 6], fill=(0, 0, 0, 170))
                    d.arc([6, 6, R - 6, R - 6], -90, -90 + 360 * (1 - s), fill=ACENTO, width=10)
                    ring.alpha_composite(n, ((R - n.width) // 2, (R - n.height) // 2))
                    fx.paste_center(fr, ring, W / 2, min(SAFE_BOT - 60 - R / 2, y + 10 + R / 2))
                fx.paste_center(fr, wp, W / 2, SAFE_BOT + 20)
            else:
                fr = Image.blend(fr.convert("RGB"), Image.new("RGB", (W, H), OSCURO), 0.5).convert("RGBA")
                _cierre(fr, G, tt - t_fin, lg, web, cq, sub)
            yield fr
    _encode(out, frames(), mix)
    return {"duration": round(total, 1), "t_fin": t_fin, "escenas": [P["pregunta"]], "idx": [0]}


# ------------------------------------------------------------------ montaje: postpro
def render_postpro(G, pares, clips, out, seed=0, bpm=86):
    """clips: [hook, pareja1..N, cierre]. pares: [(sin, con)]."""
    n = len(pares); clips_p = clips[1:1 + n]
    d_hook = max(1.8, len(clips[0]) / SR + 0.3)
    d_p = [max(3.2, len(c) / SR + 1.3) for c in clips_p]
    t0s = [d_hook]
    for d in d_p[:-1]:
        t0s.append(t0s[-1] + d)
    t_fin = t0s[-1] + d_p[-1]; d_fin = max(3.2, len(clips[-1]) / SR + 0.9); total = t_fin + d_fin
    pa = [(_plano(a, f"{seed}-a{k}"), _plano(d, f"{seed}-a{k}")) for k, (a, d) in enumerate(pares)]
    hook_big = _panel(fx.headline(G["hook_pantalla"], 112, 960, 3, color=CLARO, hot=ACENTO, shadow=True), 50, 140)
    tit = _panel(fx.headline(G["hook_pantalla"], 50, 900, 2, color=CLARO, hot=ACENTO, shadow=True), 22, 120)
    p_sin = fx.pill("SIN POSTPRO", 60, (40, 42, 48), CLARO, padx=38, pady=16, radius=6)
    p_con = fx.pill("CON POSTPRO", 60, ACENTO, OSCURO, padx=38, pady=16, radius=6)
    subs = [_subs(G["escenas"][k]["voz"]) if k < len(G.get("escenas") or []) else [] for k in range(n)]
    fondo_fin = Image.blend(_cover_fit(pares[-1][1]).filter(ImageFilter.GaussianBlur(18)), Image.new("RGB", (W, H), OSCURO),
                            0.6).convert("RGBA")
    q = fx.headline(G["cierre_pantalla"][0], 96, 960, 2, color=CLARO, hot=ACENTO, shadow=True)
    sub = fx.pill(G["cierre_pantalla"][1], 44, CLARO, OSCURO, padx=34, pady=16, radius=8)
    lg, web = _cierre_marca(); wp = _web_pill(); grad = _degradados()
    voces = [(0.12, clips[0])] + [(t + 1.0, c) for t, c in zip(t0s, clips_p)] + [(t_fin + 0.35, clips[-1])]
    extra = [(fx.shimmer(), t + 1.0, 0.3) for t in t0s] + [(fx.shimmer(), t_fin + 0.2, 0.4)]
    mix = _mezcla(total, voces, t0s[1:] + [t_fin], extra, seed, bpm)

    def frames():
        for f in range(int(total * FPS)):
            tt = f / FPS
            if tt < t_fin:
                if tt < d_hook:
                    fr = pa[0][0](tt / d_hook * 0.3).convert("RGBA"); fr.alpha_composite(grad)
                    a = eob(clamp(tt / 0.3))
                    fx.paste_center(fr, hook_big, W / 2, 760, alpha=clamp(a * 1.5) * (1 - clamp((tt - d_hook + 0.2) / 0.2)))
                else:
                    k = max(i for i, a in enumerate(t0s) if a <= tt); lt = tt - t0s[k]; p = lt / d_p[k]
                    sin_f = pa[k][0](p).convert("RGBA")
                    w_ = eo(clamp((lt - 0.9) / 0.7))
                    if w_ <= 0:
                        fr = sin_f
                    else:
                        con_f = pa[k][1](p).convert("RGBA"); cut = int(W * w_)
                        fr = sin_f; fr.paste(con_f.crop((0, 0, cut, H)), (0, 0))
                        if w_ < 1:
                            ImageDraw.Draw(fr).rectangle([cut - 4, 0, cut + 4, H], fill=ACENTO)
                    fr.alpha_composite(grad)
                    fx.paste_center(fr, tit, W / 2, SAFE_TOP + 50 + tit.height / 2)
                    fx.paste_center(fr, p_con if w_ > 0.5 else p_sin, W / 2, 1060)
                    dur_v = max(0.1, len(clips_p[k]) / SR)
                    for a0, a1, s in subs[k]:
                        if a0 <= (lt - 1.0) / dur_v < a1:
                            fx.paste_center(fr, s, W / 2, 1200)
                fx.paste_center(fr, wp, W / 2, SAFE_BOT + 20)
            else:
                fr = fondo_fin.copy(); _cierre(fr, G, tt - t_fin, lg, web, q, sub)
            yield fr
    _encode(out, frames(), mix)
    return {"duration": round(total, 1), "t_fin": t_fin, "escenas": [f"pareja {k + 1}" for k in range(n)], "idx": list(range(n))}


# ------------------------------------------------------------------ portada
def _marco(base):
    d = ImageDraw.Draw(base); y0, y1 = GRID[0] + 36, GRID[1] - 36
    d.rectangle([44, y0, W - 44, y1], outline=ACENTO + (200,), width=3)
    for (x, y, dx, dy) in ((44, y0, 1, 1), (W - 44, y0, -1, 1), (44, y1, 1, -1), (W - 44, y1, -1, -1)):
        d.line([(x, y), (x + 70 * dx, y)], fill=ACENTO, width=9); d.line([(x, y), (x, y + 70 * dy)], fill=ACENTO, width=9)
    return base


def portada(G, tematica, P, imgs, path):
    if tematica in QUIZ:
        base = Image.blend(_cover_fit(imgs[0][0].convert("RGB")), Image.new("RGB", (W, H), OSCURO), 0.6).convert("RGBA")
        fx.paste_center(base, fx.pill(G["hook_pantalla"][:34], 46, ACENTO, OSCURO, padx=34, pady=16, radius=8), W / 2, GRID[0] + 150)
        fx.paste_center(base, fx.headline(P["pregunta"], 100, 940, 5, color=CLARO, hot=ACENTO, shadow=True), W / 2, (GRID[0] + GRID[1]) / 2)
    elif tematica == "postpro":
        a, d = imgs[0]
        base = _cover_fit(a.convert("RGB")).convert("RGBA")
        base.paste(_cover_fit(d.convert("RGB")).crop((W // 2, 0, W, H)), (W // 2, 0))
        ImageDraw.Draw(base).rectangle([W // 2 - 4, 0, W // 2 + 4, H], fill=ACENTO)
        base.alpha_composite(_degradados())
        hl = fx.headline(G["hook_pantalla"], 104, 960, 3, color=CLARO, hot=ACENTO, shadow=True)
        fx.paste_center(base, hl, W / 2, GRID[0] + 140 + hl.height / 2)
    else:
        img = next(im for im, _ in imgs if im is not None)
        base = _cover_fit(img.convert("RGB")).convert("RGBA"); base.alpha_composite(_degradados())
        hl = fx.headline(G["hook_pantalla"], 118, 960, 4, color=CLARO, hot=ACENTO, hot_words=_hot(G["hook_pantalla"]), shadow=True)
        fx.paste_center(base, _panel(hl, 40, 120), W / 2, GRID[0] + 170 + hl.height / 2)
    _marco(base)
    fx.paste_center(base, fx.logo(78, CLARO, ACENTO), W / 2, GRID[1] - 150)
    fx.paste_center(base, fx.pill(WEB, 34, ACENTO, OSCURO, padx=24, pady=10, radius=6), W / 2, GRID[1] - 75)
    base.convert("RGB").save(path, "JPEG", quality=92)
    return path


# ------------------------------------------------------------------ 7 · revisor de vídeo (ve y escucha)
def revisar(path, G, tematica, frases, meta_r):
    import gemini
    small = path.replace(".mp4", "_rev.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf", "scale=360:640", "-r", "12", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "30", "-c:a", "aac", "-b:a", "64k", small], check=True)
        data = base64.b64encode(open(small, "rb").read()).decode()
        res = gemini.ask([{"text": f"""Eres director creativo de una cuenta de TikTok, Instagram y YouTube Shorts para
estudiantes de arquitectura (TFM, TFG, asignatura de Proyectos). VE y ESCUCHA este reel completo.
Tipo: {NOMBRE[tematica]}. Gancho en pantalla: «{G['hook_pantalla']}». Escenas: {json.dumps(meta_r['escenas'], ensure_ascii=False)}.
Guion de la voz (debe decir esto): {json.dumps(frases, ensure_ascii=False)}
{'Es un test: la solución NO debe aparecer ni decirse; si aparece, es un defecto grave.' if tematica in QUIZ else ''}
{('Las escenas ' + ', '.join(map(str, meta_r['reales'])) + ' son PLANOS REALES del equipo (etiqueta «Trabajo real»): sus textos y cotas técnicas son normales, NO son defecto; solo cuenta que se vean nítidos.') if meta_r.get('reales') else ''}
Comprueba:
- VOZ: acento de España (con distinción z/c, sin seseo), que suene humana y con altibajos (no plana, no robótica, no de
  anuncio), que diga el guion sin trabarse, repetir ni leer indicaciones, volumen claro sobre la música.
- IMÁGENES: bonitas, verosímiles, coherentes con su título; sin defectos de IA (geometría imposible, letras raras).
- TEXTOS: legibles en el móvil, dentro de la zona segura, subtítulos sincronizados, la web visible.
- RITMO: que el gancho se entienda en 2 s y no decaiga; cierre claro.
ESCALA ANCLADA: 8 = profesional y publicable SIN defectos objetivos (lo opinable va a "suggestions" y no baja de 8);
6-7 = algún defecto objetivo; 5 o menos = grave (voz con acento latino o robótica, imagen absurda, solución desvelada,
vídeo roto).
"malas" = números (1 = primera escena) de las imágenes con defecto objetivo. "voz" = defectos objetivos de la voz.
Devuelve JSON: {{"overall": number, "issues": [str], "suggestions": [str], "malas": [int], "voz": [str], "critical": bool}}"""},
                          {"inline_data": {"mime_type": "video/mp4", "data": data}}], 0.3)
    except Exception as e:
        say("revisor de vídeo no disponible:", str(e)[:200])
        return {"overall": 0, "issues": [f"revisor no disponible: {str(e)[:100]}"], "malas": [], "voz": []}
    finally:
        if os.path.exists(small): os.remove(small)
    ov = float(res.get("overall") or 0)
    if ov < 8 and not (res.get("issues") or []) and not (res.get("voz") or []) and not res.get("critical"):
        res["overall_raw"] = ov; ov = 8.0                        # escala anclada: sin defectos objetivos, es un 8
    res["overall"] = ov
    try:
        with open(os.path.join(HERE, "review_log.jsonl"), "a") as f:
            f.write(json.dumps({"date": str(datetime.date.today()), "kind": "video", "tematica": tematica,
                                "hook": G["hook_pantalla"], **{k: res.get(k) for k in ("overall", "issues", "malas", "voz",
                                                                                       "suggestions")}}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    say(f"revisor: {ov}/10", res.get("issues") or "", res.get("voz") or "")
    return res


# ------------------------------------------------------------------ todo junto
def hacer(tematica, out, seed=0, recientes=(), max_montajes=3, limite_s=40 * 60):
    import agentes, voz
    t0 = time.time()
    P = pieza(tematica, seed)
    say(f"{tematica}: {P.get('hook') or P.get('pregunta')}")
    G, prompts, direcciones, desc, titulo = agentes.preparar(tematica, P, recientes)
    frases = agentes._frases(G)
    say(f"guion listo en {time.time() - t0:.0f} s · gancho «{G['hook_pantalla']}»")
    t1 = time.time()
    with ThreadPoolExecutor(2) as ex:                                 # imágenes y voz A LA VEZ
        fi = ex.submit(imagenes, tematica, P, prompts, seed)
        fv = ex.submit(voz.grabar, frases, direcciones)
        imgs = fi.result(); clips = fv.result()
    say(f"imágenes y voz ({voz.ENGINE}) en {time.time() - t1:.0f} s")
    bpm = random.Random(str(seed)).choice((84, 88, 92))
    rev, montajes = {}, 0
    while True:
        montajes += 1; t2 = time.time()
        if tematica in QUIZ:
            # clips: [hook, pregunta, cierre]
            mr = render_quiz(G, P, imgs[0][0], clips, out, tematica, f"{seed}-{montajes}", bpm)
        elif tematica == "postpro":
            mr = render_postpro(G, imgs, clips, out, f"{seed}-{montajes}", bpm)
        else:
            mr = render_lista(G, imgs, clips, out, tematica, f"{seed}-{montajes}", bpm)
        say(f"montaje {montajes}: {mr['duration']} s de vídeo en {time.time() - t2:.0f} s")
        if not os.environ.get("GEMINI_API_KEY"):
            rev = {"overall": None}; break
        rev = revisar(out, G, tematica, frases, mr)
        if rev["overall"] >= 8 and not rev.get("critical"):
            break
        if montajes >= max_montajes or time.time() - t0 > limite_s:
            raise RuntimeError(f"no llega al 8 tras {montajes} montajes: {rev.get('overall')} · "
                               f"{'; '.join((rev.get('issues') or []) + (rev.get('voz') or []))[:300]}")
        malas = sorted({int(m) - 1 for m in rev.get("malas") or [] if str(m).isdigit() and 0 < int(m) <= len(mr["idx"])})
        arreglos = []
        with ThreadPoolExecutor(6) as ex:
            if malas and tematica not in QUIZ and tematica != "postpro":
                evita = "; ".join(rev.get("issues") or [])[:250]
                futs = {mr["idx"][m]: ex.submit(gen, f"{prompts[mr['idx'][m]]}. Evita: {evita}") for m in malas
                        if not imgs[mr["idx"][m]][1]}
                for k, f in futs.items():
                    nuevo = f.result()
                    if nuevo is not None:
                        imgs[k] = (nuevo, False); arreglos.append(f"imagen {k + 1}")
            elif malas and tematica in QUIZ:
                nuevo = gen(f"{P['idea']}. Evita: {'; '.join(rev.get('issues') or [])[:250]}")
                if nuevo is not None:
                    imgs = [(nuevo, False)]; arreglos.append("imagen de fondo")
            if rev.get("voz"):                                       # el director de voz rehace la dirección
                direcciones = agentes.director_voz(frases, tematica, agentes.playbook(), "; ".join(rev["voz"])[:300])
                clips = voz.grabar(frases, direcciones); arreglos.append("voz")
        if not arreglos:
            bpm = {84: 92, 88: 84, 92: 88}[bpm]; arreglos.append("ritmo/música")
        say("arreglos:", arreglos)
    cover = portada(G, tematica, P, imgs, out.replace(".mp4", "_portada.jpg"))
    open(out.replace(".mp4", ".txt"), "w").write(desc)
    meta = {"tematica": tematica, "hook": G["hook_pantalla"], "hook_voz": G["hook_voz"], "duration": mr["duration"],
            "cover": cover, "thumb_ms": 600, "review_score": rev.get("overall"), "ids": P["ids"], "voz": voz.ENGINE,
            "venta": tematica in agentes.VENTA, "solucion": solucion(tematica, P), "titulo": titulo, "montajes": montajes,
            "segundos": round(time.time() - t0)}
    say(f"listo en {meta['segundos']} s · {mr['duration']} s de vídeo · nota {rev.get('overall')}")
    return meta

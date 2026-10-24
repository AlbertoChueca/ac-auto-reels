"""Reels VISUALES de AC · ArquitecturaConfidencial para estudiantes de arquitectura (imagen primero, poca letra, cortes
al ritmo de la música y una razón para comentar o guardar). Motor clonado del de UDA y adaptado.

Formatos (banco: fuentes/visual.json):
    galeria         «Bibliotecas para inspirar tu TFM»: 6 imágenes numeradas -> «¿Cuál elegirías? Comenta el número»
    tips            «5 tips para que tus renders impresionen»: imagen + consejo (los marcados "ac" cierran con AC)
    antes_despues   «Tu render sin y con postproducción»: el MISMO encuadre, cortinilla amarilla
    proceso_visual  «Del boceto al render de un TFM»: el MISMO edificio en boceto, CAD, Revit y render
    obra            «Así se construye»: el MISMO edificio en cimentación, estructura, cerramientos y terminado
    test            Test de arquitectura: pregunta + 4 opciones + cuenta atrás «Comenta la letra». La solución NO sale
                    en el reel: la publica el bot de comunidad 12-24 h después (comunidad.py)
    vf              ¿Verdadero o falso?: igual que el test, con dos opciones
    encuesta        Pregunta sin respuesta correcta («¿Con qué programa haces tu TFM?»): el bot publica el recuento

Imágenes: originales, generadas con IA (Gemini) y revisadas una a una (sin texto, sin edificios reales, construcción
coherente). La descripción lo indica: «Imágenes creadas con IA». Revisión final del vídeo con nota mínima 8 (escala
anclada); si marca imágenes concretas, se regeneran solo esas.
"""
import base64, datetime, io, json, math, os, random, subprocess, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx
import marca
from fx import W, H, FPS, SR, F_BOLD, F_REG, clamp, eo, eob

HERE = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(HERE, "fuentes", "visual.json")
QUIZ = ["test", "vf", "encuesta"]
FORMATOS = ["galeria", "tips", "antes_despues", "proceso_visual", "obra"] + QUIZ
BANCO_DE = {"proceso_visual": "proceso"}
NOMBRE = {"galeria": "Galería de referentes", "tips": "Tips visuales", "antes_despues": "Render sin y con postproducción",
          "proceso": "Del boceto al render", "proceso_visual": "Del boceto al render", "obra": "Así se construye",
          "test": "Test de arquitectura", "vf": "¿Verdadero o falso?", "encuesta": "Encuesta"}
ACENTO, CLARO, OSCURO = fx.AMARILLO, fx.PAPEL, fx.TINTA
FOTO = ("Fotografía de arquitectura de revista: luz natural bonita, colores reales, encuadre editorial, nítida y "
        "aspiracional")
REGLAS = ("Imagen vertical 9:16. NADA de texto, letras, números, rótulos, cotas legibles ni logotipos. Arquitectura "
          "ORIGINAL y verosímil (nunca un edificio famoso o reconocible), construcción y detalles coherentes, sin personas "
          "identificables (si aparecen, de espaldas o desenfocadas). En obra: sin riesgos y con EPI correctos.")
SAFE_TOP, SAFE_BOT = 250, 1480
GRID = (240, 1680)                       # recorte 3:4 del perfil de Instagram: lo importante de la portada va aquí
LETRAS = "ABCD"


def say(*a):
    print("visual:", *a, flush=True)


# ------------------------------------------------------------------ elegir pieza
def _used():
    try:
        return {x["id"] for x in json.load(open(os.path.join(HERE, "used.json")))}
    except Exception:
        return set()


def pieza(formato, seed=0, solo_ac=None):
    """La pieza del banco que no se ha usado (si todas, una al azar). En antes/después, 3 escenas distintas.
    solo_ac=True/False filtra los tips de AC (20 % del calendario) o los de contenido puro."""
    B = json.load(open(BANCO)); rng = random.Random(seed); usados = _used()
    formato = BANCO_DE.get(formato, formato)
    lista = B[formato]
    if solo_ac is not None and formato == "tips":
        lista = [p for p in lista if bool(p.get("ac")) == solo_ac] or lista
    frescas = [p for p in lista if f"visual:{p['id']}" not in usados] or lista
    if formato == "antes_despues":
        rng.shuffle(frescas)
        el = (frescas + [p for p in lista if p not in frescas])[:3]
        return {"id": "+".join(p["id"] for p in el), "ids": [f"visual:{p['id']}" for p in el], "escenas_pp": el,
                "hook": "Tu render sin y con postproducción"}
    p = dict(rng.choice(frescas)); p["ids"] = [f"visual:{p['id']}"]
    if formato in ("test", "vf"):                          # la correcta va primera en el banco: se baraja
        ops = list(p["opciones"]); correcta = ops[0]
        if formato == "vf":
            ops = ["Verdadero", "Falso"]
        else:
            rng.shuffle(ops)
        p["opciones"] = ops; p["correcta"] = ops.index(correcta)
    return p


def solucion(formato, P):
    """Lo que necesita el bot de comunidad para publicar la solución o el recuento (se guarda en log.jsonl)."""
    if formato not in QUIZ:
        return None
    s = {"tipo": formato, "pregunta": P["pregunta"], "opciones": P["opciones"],
         "letras": "VF" if formato == "vf" else LETRAS[:len(P["opciones"])]}
    if formato != "encuesta":
        s.update(correcta=P["correcta"], explicacion=P["explicacion"])
    return s


# ------------------------------------------------------------------ imágenes (IA + revisora)
def revisa(img, idea):
    """Revisora: SOLO defectos objetivos. Devuelve (ok, motivo)."""
    import gemini
    b = io.BytesIO(); im = img.copy(); im.thumbnail((640, 640)); im.convert("RGB").save(b, "JPEG", quality=82)
    try:
        r = gemini.ask([{"text": f"""Revisa esta imagen para un reel de arquitectura para estudiantes. Debía mostrar: {idea}.
Rechaza (ok=false) SOLO si hay un defecto objetivo que un arquitecto vería en el móvil: texto, letras o números legibles;
geometría imposible o absurda (escaleras sin sentido, ventanas o muebles deformados, objetos fundidos); un edificio
famoso reconocible; caras de personas reconocibles; algo inquietante; o si no se parece a lo pedido. Los detalles de
encuadre o estilo NO son motivo de rechazo.
Devuelve JSON: {{"ok": bool, "problemas": [str]}}"""},
                        {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}], 0.2)
        return bool(r.get("ok")), "; ".join(r.get("problemas") or [])[:300]
    except Exception as e:
        return True, f"revisora no disponible ({str(e)[:80]}); la revisión del vídeo hará de filtro"


def _gen(prompt, refs=(), revisar=True, intentos=3, estilo=FOTO):
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
                f.write(json.dumps({"date": str(datetime.date.today()), "idea": prompt[:200], "ok": ok,
                                    "problemas": why}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        if ok:
            return img
        say(f"revisora rechaza ({why[:120]}); intento {k + 2}")
        idea = f"{prompt}. Evita esto: {why[:200]}"
    return None


SIN_POSTPRO = ("Render arquitectónico SIN postproducción, recién salido de un motor de render básico: materiales grises y "
               "planos, cielo blanco liso, iluminación plana y uniforme, sin vegetación ni personas, sin atmósfera. De")
CON_POSTPRO = ("El MISMO render de la imagen de referencia (mismo edificio, misma geometría y la MISMA cámara) después de "
               "una postproducción profesional: cielo de atardecer, luz cálida y sombras marcadas, materiales con textura "
               "real, vegetación, personas desenfocadas de espaldas para dar escala y una ligera atmósfera")


def imagenes(formato, P):
    """Lista de (imagen, etiqueta) en orden."""
    formato = BANCO_DE.get(formato, formato)
    pasos = []
    with ThreadPoolExecutor(6) as ex:
        if formato == "galeria":
            fs = [ex.submit(_gen, e["idea"]) for e in P["escenas"]]
            pasos = [(f.result(), e["label"]) for f, e in zip(fs, P["escenas"])]
            pasos = [x for x in pasos if x[0] is not None]
            if len(pasos) < 5:
                raise RuntimeError("galería: menos de 5 imágenes aprobadas")
        elif formato == "tips":
            fs = [ex.submit(_gen, t["idea"]) for t in P["tips"]]
            pasos = [(f.result(), t["tip"]) for f, t in zip(fs, P["tips"])]
            pasos = [x for x in pasos if x[0] is not None]
            if len(pasos) < max(3, len(P["tips"]) - 1):
                raise RuntimeError("tips: faltan imágenes aprobadas")
            if len(pasos) < len(P["tips"]):                    # «5 tips» -> «4 tips» si una no salió bien
                P["hook"] = P["hook"].replace(str(len(P["tips"])), str(len(pasos)), 1)
        elif formato in QUIZ:
            img = _gen(P["idea"])
            if img is None:
                raise RuntimeError(f"{formato}: no hay imagen de fondo aprobada")
            pasos = [(img, P["pregunta"])]
        elif formato in ("proceso", "obra"):
            final = _gen(f"Render fotorrealista exterior de {P['descripcion']}, terminado, entorno cuidado, luz de atardecer")
            if final is None:
                raise RuntimeError(f"{formato}: no hay render final aprobado")
            if formato == "proceso":
                etapas = [
                    ("La idea, a mano", "Boceto a mano alzada con lápiz y rotulador sobre papel de croquis de ESTE MISMO "
                     "edificio (misma forma y proporciones que la imagen de referencia), trazo suelto de arquitecto", False),
                    ("Planta en CAD", "Planta arquitectónica de ESTE edificio dibujada en CAD: líneas negras finas sobre "
                     "fondo blanco, muros en gris, puertas y ventanas; SIN ningún texto, cota ni número", False),
                    ("Modelo en Revit", "Maqueta digital blanca de ESTE MISMO edificio como un modelo BIM de Revit: "
                     "volúmenes blancos, sombras suaves, fondo gris claro, vista axonométrica", True)]
                fin = "Render final"
            else:
                etapas = [
                    ("Cimentación", "La obra de ESTE MISMO edificio en fase de cimentación: zanjas, armaduras y hormigón "
                     "de limpieza en el solar, sin personas", True),
                    ("Estructura", "La obra de ESTE MISMO edificio con la estructura de hormigón terminada: pilares y "
                     "forjados, andamio perimetral, sin personas", True),
                    ("Cerramientos", "La obra de ESTE MISMO edificio con fachadas y cubierta cerradas, aún sin acabar, "
                     "andamios", True)]
                fin = "¡Terminado!"
            fs = [ex.submit(_gen, txt, [final], rev) for _, txt, rev in etapas]
            pasos = [(f.result(), lab) for f, (lab, _, _) in zip(fs, etapas)]
            pasos = [x for x in pasos if x[0] is not None] + [(final, fin)]
            if len(pasos) < 3:
                raise RuntimeError(f"{formato}: faltan etapas")
        else:                                                      # sin / con postproducción
            def par(e):
                antes = _gen(f"{SIN_POSTPRO} {e['descripcion']}", estilo="")
                if antes is None:
                    return None
                despues = _gen(CON_POSTPRO, [antes])
                return (antes, despues) if despues is not None else None
            fs = [ex.submit(par, e) for e in P["escenas_pp"]]
            pares = [x for x in (f.result() for f in fs) if x]
            if len(pares) < 2:
                raise RuntimeError("antes/después: menos de 2 parejas aprobadas")
            for a, d in pares:
                pasos += [(a, "SIN POSTPRO"), (d, "CON POSTPRO")]
    return pasos


# ------------------------------------------------------------------ montaje
def _cover_fit(img, zoom=1.0, cx=0.5, cy=0.5):
    iw, ih = img.size
    s = max(W / iw, H / ih) * zoom
    nw, nh = int(iw * s), int(ih * s)
    im = img.resize((nw, nh), Image.BICUBIC)
    x = int((nw - W) * cx); y = int((nh - H) * cy)
    return im.crop((x, y, x + W, y + H))


def _ventana(big, z, c):
    bw, bh = big.size
    base = min(bw / W, bh / H)
    ww, wh = W * base / z, H * base / z
    x = (bw - ww) * c[0]; y = (bh - wh) * c[1]
    return big.resize((W, H), Image.BICUBIC, box=(x, y, x + ww, y + wh))


def _plano(img, seed, oscuro=0.0):
    r = random.Random(seed)
    z0, z1 = (1.0, 1.13) if r.random() < 0.6 else (1.13, 1.0)          # Ken Burns bien visible
    c0 = (r.uniform(0.35, 0.65), r.uniform(0.4, 0.6)); c1 = (r.uniform(0.35, 0.65), r.uniform(0.4, 0.6))
    iw, ih = img.size; s = max(W / iw, H / ih) * 1.15
    big = img.convert("RGB").resize((int(iw * s), int(ih * s)), Image.BICUBIC)
    if oscuro:                                                          # tests: foto de fondo oscurecida
        big = Image.blend(big, Image.new("RGB", big.size, OSCURO), oscuro)
    return lambda p: _ventana(big, z0 + (z1 - z0) * eo(clamp(p)), (c0[0] + (c1[0] - c0[0]) * p, c0[1] + (c1[1] - c0[1]) * p))


def _degradados():
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for y in range(0, 620, 4):
        d.rectangle([0, y, W, y + 4], fill=(0, 0, 0, int(170 * (1 - y / 620) ** 1.6)))
    for y in range(1000, H, 4):
        d.rectangle([0, y, W, y + 4], fill=(0, 0, 0, int(210 * ((y - 1000) / (H - 1000)) ** 1.3)))
    return g


def _panel(im, pad=36, alpha=150):
    """Texto grande sobre una banda oscura difuminada: legible aunque la foto sea muy clara."""
    w, h = im.width + 2 * pad, im.height + 2 * pad
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([pad // 2, pad // 2, w - pad // 2, h - pad // 2], 40, fill=(0, 0, 0, alpha))
    p = p.filter(ImageFilter.GaussianBlur(pad / 2))
    p.alpha_composite(im, (pad, pad))
    return p


def _hot(texto):
    return tuple(w.lower().strip("¿?¡!.,") for w in texto.split() if w[:1].isdigit() or w.strip("¿?¡!.,").upper() == "TFM")


def _opcion(letra, texto, ancho=900, marcada=False):
    """Tarjeta de opción: letra en un círculo amarillo + texto (hasta 2 líneas)."""
    size = fx.fit_font(texto, F_BOLD, 46, ancho - 180, 2, 34)
    tx = fx.text_block(texto, F_BOLD, size, ancho - 190, OSCURO if marcada else CLARO)
    h = max(108, tx.height + 30)
    im = Image.new("RGBA", (ancho, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, ancho - 1, h - 1], 28, fill=ACENTO + (255,) if marcada else (20, 22, 27, 225),
                        outline=ACENTO, width=3)
    d.ellipse([28, h / 2 - 36, 100, h / 2 + 36], fill=OSCURO if marcada else ACENTO)
    f = fx.font(F_BOLD, 46); bb = f.getbbox(letra)
    d.text((64 - (bb[2] - bb[0]) / 2 - bb[0], h / 2 - (bb[3] - bb[1]) / 2 - bb[1]), letra, font=f,
           fill=ACENTO if marcada else OSCURO)
    im.alpha_composite(tx, (128, int((h - tx.height) / 2) + 6))
    return im


def guion(formato, P, pasos, bpm):
    formato = BANCO_DE.get(formato, formato)
    beat = 60 / bpm
    if formato in QUIZ:                                              # una sola imagen: pregunta, opciones y cuenta atrás
        n = len(P["opciones"])
        dur = beat * 4 + beat * 2 * n + 5.0                          # gancho+pregunta, una opción cada 2 tiempos, 5 s
        hook = {"test": "TEST DE ARQUITECTURA", "vf": "¿VERDADERO O FALSO?", "encuesta": "ENCUESTA"}[formato]
        cierre = (("Comenta tu voto", "Mañana, los resultados en comentarios") if formato == "encuesta" else
                  ("Comenta tu respuesta", "Solución mañana en comentarios"))
        return {"formato": formato, "hook": hook, "pregunta": P["pregunta"], "opciones": P["opciones"],
                "golpes": [{"img": pasos[0][0], "label": P["pregunta"], "dur": dur, "n": 0}], "cierre": cierre,
                "beat": beat, "fin": beat * 5, "ac": False}
    por = {"galeria": 2, "tips": 4, "proceso": 3, "obra": 3, "antes_despues": 2}[formato]
    hook = P.get("hook") or {"proceso": "Del boceto al render de un TFM", "obra": "Así se construye: de la zanja a la llave"}[formato]
    golpes = []
    for k, (img, lab) in enumerate(pasos):
        d = beat * por
        if k == 0:
            d += beat * 3                                            # el primero lleva antes el gancho (≈2 s)
        if formato == "antes_despues" and lab == "CON POSTPRO":
            d = beat * 3
        golpes.append({"img": img, "label": lab, "dur": d, "n": k})
    ac = bool(P.get("ac"))
    cierre = {"galeria": (P.get("cierre", "¿Cuál elegirías?"), "Comenta el número"),
              "tips": ("¿Cuál vas a aplicar?", "Guárdalo para tu TFM") if not ac else
                      ("¿Vas justo con el TFM?", "Auditoría gratuita en la bio"),
              "proceso": ("¿Qué fase se te da mejor?", "Guárdalo para tu próximo proyecto"),
              "obra": ("¿Qué fase te cuesta más en Construcción?", "Cuéntanoslo en comentarios"),
              "antes_despues": ("¿Cuál te sorprende más?", "Guárdalo para tu próxima entrega")}[formato]
    return {"formato": formato, "hook": hook, "golpes": golpes, "cierre": cierre, "beat": beat, "fin": beat * 6, "ac": ac}


def _audio(total, bpm, seed, cortes, t_fin, extra=()):
    n = int(SR * (total + 0.3))
    music = fx.premium_beat(total + 0.3, bpm, seed=seed, energy=1.2, jitter=False)
    music = np.pad(music, (0, max(0, n - len(music))))[:n] * 0.75
    sfx = np.zeros(n, np.float32)

    def put(a, at, gain=1.0):
        i = int(at * SR)
        if i < 0: a = a[-i:]; i = 0
        j = min(n, i + len(a)); sfx[i:j] += a[: j - i] * gain
    put(fx.impact(), 0.0, 0.7)
    for t0 in cortes:
        put(fx.whoosh2(0.4), t0 - 0.3, 0.7); put(fx.impact(), t0, 0.35)
    for snd, at, g in extra:
        put(snd, at, g)
    put(fx.shimmer(), t_fin + 0.2, 0.55)
    return fx.dehiss(np.tanh((music + sfx) * 1.1) * 0.9)


def _encode(out, frames, total, mix):
    wav = out.replace(".mp4", ".wav")
    import soundfile as sf
    sf.write(wav, mix, SR)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", wav, "-shortest",
                             "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-crf", "20", "-maxrate", "8M",
                             "-bufsize", "12M", "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-r", str(FPS),
                             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", out],
                            stdin=subprocess.PIPE)
    for fr in frames:
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close(); proc.wait(); os.remove(wav)
    if proc.returncode:
        raise RuntimeError("ffmpeg falló al codificar el reel")


def _cierre_marca():
    return fx.logo(96, CLARO, ACENTO), fx.text_block(f"{marca.FIRMA} · {marca.WEB}", F_REG, 30, 900, (205, 200, 190),
                                                      align="center")


def render_quiz(G, out, seed=0, bpm=84):
    """Test / V/F / encuesta: foto oscurecida, etiqueta, pregunta, opciones al ritmo, cuenta atrás y cierre."""
    beat = G["beat"]; g = G["golpes"][0]; ops = G["opciones"]; fmt = G["formato"]
    t_fin = g["dur"]; total = t_fin + G["fin"]
    plano = _plano(g["img"], f"{seed}-q", oscuro=0.55)
    tag = fx.pill(G["hook"], 44, ACENTO, OSCURO, padx=34, pady=16, radius=8)
    q = fx.headline(G["pregunta"], 82 if len(G["pregunta"]) < 70 else 70, 960, 4, color=CLARO, hot=ACENTO, shadow=True)
    letras = "VF" if fmt == "vf" else LETRAS
    cards = [_opcion(letras[k], o) for k, o in enumerate(ops)]
    t_q = beat * 4                                                    # la pregunta entra con el gancho
    t_ops = [t_q + beat * 2 * k for k in range(len(ops))]
    t_cd = t_ops[-1] + beat * 2                                       # cuenta atrás de 5 s
    gap = 18; alto = sum(c.height for c in cards) + gap * (len(cards) - 1)
    y_q = 370 + q.height / 2
    y0 = max(y_q + q.height / 2 + 30, 960 - alto / 2)              # opciones bajo la pregunta
    lg, web = _cierre_marca()
    cta = fx.headline(G["cierre"][0], 96, 960, 2, color=CLARO, hot=ACENTO, shadow=True)
    sub = fx.pill(G["cierre"][1], 44, ACENTO, OSCURO, padx=34, pady=18, radius=8)
    grad = _degradados()

    def frames():
        for f in range(int(total * FPS)):
            tt = f / FPS
            fr = plano(min(1.0, tt / total)).convert("RGBA"); fr.alpha_composite(grad)
            if tt < t_fin:
                a = eob(clamp(tt / 0.35))
                fx.paste_center(fr, tag, W / 2, 310 - (1 - a) * 20, alpha=clamp(a))
                b = eo(clamp((tt - 0.4) / 0.4))
                fx.paste_center(fr, q, W / 2, y_q + (1 - b) * 30, alpha=b)
                y = y0
                for k, c in enumerate(cards):
                    e = eob(clamp((tt - t_ops[k]) / 0.35))
                    fx.paste_center(fr, c, W / 2 + (1 - e) * 120, y + c.height / 2, alpha=clamp(e * 1.4))
                    y += c.height + gap
                if tt >= t_cd:                                        # 5, 4, 3, 2, 1
                    k = int(tt - t_cd); s = (tt - t_cd) - k
                    n = fx.headline(str(5 - k), 104, 300, 1, color=ACENTO, hot=ACENTO, shadow=True)
                    R = 170 if y + 200 < SAFE_BOT else 140
                    if R == 140:
                        n = n.resize((int(n.width * 0.8), int(n.height * 0.8)))
                    ring = Image.new("RGBA", (R, R), (0, 0, 0, 0)); d = ImageDraw.Draw(ring)
                    d.ellipse([6, 6, R - 6, R - 6], fill=(0, 0, 0, 170))
                    d.arc([6, 6, R - 6, R - 6], -90, -90 + 360 * (1 - s), fill=ACENTO, width=10)
                    ring.alpha_composite(n, ((R - n.width) // 2, (R - n.height) // 2 + 8))
                    fx.paste_center(fr, ring, W / 2, min(SAFE_BOT - R / 2, y - gap + 24 + R / 2))
            else:
                lt = tt - t_fin
                fr = Image.blend(fr.convert("RGB"), Image.new("RGB", (W, H), OSCURO), 0.5).convert("RGBA")
                a = eob(clamp(lt / 0.4))
                fx.paste_center(fr, cta, W / 2, 700 - (1 - a) * 30, alpha=clamp(a))
                b = eob(clamp((lt - 0.5) / 0.4))
                fx.paste_center(fr, sub, W / 2, 700 + cta.height / 2 + 90 - (1 - b) * 20, alpha=clamp(b))
                c_ = clamp((lt - 0.9) / 0.4)
                fx.paste_center(fr, lg, W / 2, 1300, alpha=c_)
                fx.paste_center(fr, web, W / 2, 1400, alpha=c_)
            yield fr
    extra = [(fx.blip(k), t, 0.5) for k, t in enumerate(t_ops)]
    extra += [(fx.tick2(k == 4), t_cd + k, 0.6) for k in range(5)]
    mix = _audio(total, bpm, seed, [], t_fin, extra)
    _encode(out, frames(), total, mix)
    return {"duration": round(total, 1), "t0s": [0.0], "t_fin": t_fin}


def render(G, out, seed=0, bpm=84):
    """Renderiza el reel (vídeo + audio) y devuelve meta."""
    if G["formato"] in QUIZ:
        return render_quiz(G, out, seed, bpm)
    golpes, beat = G["golpes"], G["beat"]
    fmt = G["formato"]
    t0s = []; t = 0.0
    for g in golpes:
        t0s.append(t); t += g["dur"]
    t_fin = t; total = t + G["fin"]
    planos = [_plano(g["img"], f"{seed}-{k}") for k, g in enumerate(golpes)]
    grad = _degradados()
    hook_big = _panel(fx.headline(G["hook"], 118, 960, 3, color=CLARO, hot=ACENTO, hot_words=_hot(G["hook"]),
                                  shadow=True), 50, 140)
    tit = _panel(fx.headline(G["hook"], 54, 900, 2, color=CLARO, hot=ACENTO, hot_words=(), shadow=True), 24, 120)
    labs = []
    for k, g in enumerate(golpes):
        lab = g["label"]
        if fmt == "galeria":
            num = fx.pill(f"{k + 1:02d}", 54, ACENTO, OSCURO, padx=24, pady=14, radius=6)
            txt = fx.pill(lab, 54, (18, 20, 24), CLARO, padx=28, pady=14, radius=6)
            im = Image.new("RGBA", (num.width + txt.width + 14, max(num.height, txt.height)), (0, 0, 0, 0))
            im.alpha_composite(num, (0, 0)); im.alpha_composite(txt, (num.width + 14, 0))
        elif fmt == "tips":
            n = fx.headline(str(k + 1), 230, 400, 1, color=ACENTO, hot=ACENTO, shadow=True)
            tx = fx.headline(lab, 92, 940, 3, color=CLARO, hot=ACENTO, shadow=True)
            im = Image.new("RGBA", (max(n.width, tx.width), n.height + tx.height - 30), (0, 0, 0, 0))
            im.alpha_composite(n, ((im.width - n.width) // 2, 0)); im.alpha_composite(tx, ((im.width - tx.width) // 2, n.height - 30))
            im = _panel(im, 44, 150)
        elif fmt == "antes_despues":
            on = lab == "CON POSTPRO"
            im = fx.pill(lab, 64, ACENTO if on else (40, 42, 48), OSCURO if on else CLARO, padx=40, pady=18, radius=6)
        else:
            num = fx.pill(f"{k + 1}", 60, ACENTO, OSCURO, padx=28, pady=14, radius=40)
            tx = fx.headline(lab, 88, 900, 2, color=CLARO, hot=ACENTO, shadow=True)
            im = Image.new("RGBA", (max(num.width, tx.width), num.height + 16 + tx.height), (0, 0, 0, 0))
            im.alpha_composite(num, ((im.width - num.width) // 2, 0)); im.alpha_composite(tx, ((im.width - tx.width) // 2, num.height + 16))
            im = _panel(im, 40, 140)
        labs.append(im)
    ult = golpes[-1]["img"].convert("RGB")
    fondo_fin = _cover_fit(ult).filter(ImageFilter.GaussianBlur(18))
    fondo_fin = Image.blend(fondo_fin, Image.new("RGB", (W, H), OSCURO), 0.55).convert("RGBA")
    if fmt == "galeria":
        tw, th, g_ = 290, 380, 22
        x0 = (W - 3 * tw - 2 * g_) // 2; y0 = 560
        for k, g in enumerate(golpes[:6]):
            th_ = _cover_fit(g["img"].convert("RGB")).resize((tw, th))
            x = x0 + (k % 3) * (tw + g_); y = y0 + (k // 3) * (th + g_)
            fondo_fin.paste(th_, (x, y))
            ImageDraw.Draw(fondo_fin).rectangle([x, y, x + tw - 1, y + th - 1], outline=ACENTO, width=3)
            fondo_fin.alpha_composite(fx.pill(str(k + 1), 44, ACENTO, OSCURO, padx=20, pady=8, radius=6), (x + 14, y + 14))
    q = fx.headline(G["cierre"][0], 100, 960, 2, color=CLARO, hot=ACENTO, hot_words=_hot(G["cierre"][0]), shadow=True)
    sv = fx.pill(G["cierre"][1], 46, ACENTO, OSCURO, padx=34, pady=18, radius=6)
    lg, web = _cierre_marca()
    lg_mini = fx.logo(68, CLARO, ACENTO)
    cortes = t0s[1:] + [t_fin]
    extra = [(fx.shimmer(), t0s[k] + 0.1, 0.35) for k, g in enumerate(golpes) if g["label"] == "CON POSTPRO"]
    mix = _audio(total, bpm, seed, cortes, t_fin, extra)

    def frames():
        for f in range(int(total * FPS)):
            tt = f / FPS
            if tt < t_fin:
                k = max(i for i, a in enumerate(t0s) if a <= tt)
                g = golpes[k]; lt = tt - t0s[k]
                fr = planos[k](lt / g["dur"]).convert("RGBA")
                if fmt == "antes_despues" and g["label"] == "CON POSTPRO" and k > 0:   # cortinilla amarilla
                    w_ = eo(clamp(lt / 0.7))
                    if w_ < 1:
                        prev = planos[k - 1](1.0).convert("RGBA")
                        cut = int(W * w_)
                        prev.paste(fr.crop((0, 0, cut, H)), (0, 0))
                        fr = prev
                        ImageDraw.Draw(fr).rectangle([cut - 4, 0, cut + 4, H], fill=ACENTO)
                elif k > 0 and lt < 0.16:
                    fr = Image.blend(planos[k - 1](1.0).convert("RGBA"), fr, lt / 0.16)
                fr.alpha_composite(grad)
                hook_t = 3 * beat
                if k == 0 and lt < hook_t:                            # gancho grande al principio
                    a = eob(clamp(lt / 0.35))
                    im = hook_big
                    if a < 1:
                        s_ = 0.9 + 0.1 * a; im = hook_big.resize((int(hook_big.width * s_), int(hook_big.height * s_)))
                    fx.paste_center(fr, im, W / 2, 760, alpha=clamp(a * 1.5) * (1 - clamp((lt - hook_t + 0.25) / 0.25)))
                else:
                    fx.paste_center(fr, tit, W / 2, SAFE_TOP + 60 + tit.height / 2)
                    la = labs[k]; a = eo(clamp((lt - (hook_t if k == 0 else 0.18) - (0.16 if k > 0 else 0)) / 0.3))
                    cy = 1270 if fmt != "tips" else 1180
                    fx.paste_center(fr, la, W / 2, cy - (1 - a) * 30, alpha=clamp(a))
            else:
                lt = tt - t_fin
                fr = fondo_fin.copy()
                a = eob(clamp(lt / 0.4))
                yq = 290 if fmt == "galeria" else 760
                fx.paste_center(fr, q, W / 2, yq + q.height / 2 - (1 - a) * 30, alpha=clamp(a))
                b = eob(clamp((lt - 0.5) / 0.4))
                ys = 1420 if fmt == "galeria" else yq + q.height + 90
                fx.paste_center(fr, sv, W / 2, ys - (1 - b) * 20, alpha=clamp(b))
                c_ = clamp((lt - 0.9) / 0.4)
                if fmt == "galeria":                                  # la cuadrícula ocupa el sitio: logo pequeño
                    fx.paste_center(fr, lg_mini, W / 2, 1550, alpha=c_)
                else:
                    fx.paste_center(fr, lg, W / 2, 1500, alpha=c_)
                    fx.paste_center(fr, web, W / 2, 1600, alpha=c_)
            yield fr
    _encode(out, frames(), total, mix)
    return {"duration": round(total, 1), "t0s": t0s, "t_fin": t_fin}


# ------------------------------------------------------------------ portada
def _marco(base):
    """Marco fino amarillo con esquinas marcadas dentro del recorte 3:4 del perfil (todas las portadas iguales)."""
    d = ImageDraw.Draw(base)
    y0, y1 = GRID[0] + 36, GRID[1] - 36
    d.rectangle([44, y0, W - 44, y1], outline=ACENTO + (200,), width=3)
    for (x, y, dx, dy) in ((44, y0, 1, 1), (W - 44, y0, -1, 1), (44, y1, 1, -1), (W - 44, y1, -1, -1)):
        d.line([(x, y), (x + 70 * dx, y)], fill=ACENTO, width=9); d.line([(x, y), (x, y + 70 * dy)], fill=ACENTO, width=9)
    return base


def portada(G, path):
    golpes = G["golpes"]; fmt = G["formato"]
    if fmt in QUIZ:                                            # la pregunta enorme sobre la foto oscurecida
        base = Image.blend(_cover_fit(golpes[0]["img"].convert("RGB")), Image.new("RGB", (W, H), OSCURO), 0.6).convert("RGBA")
        fx.paste_center(base, fx.pill(G["hook"], 46, ACENTO, OSCURO, padx=34, pady=16, radius=8), W / 2, GRID[0] + 150)
        hl = fx.headline(G["pregunta"], 104, 940, 5, color=CLARO, hot=ACENTO, shadow=True)
        fx.paste_center(base, hl, W / 2, (GRID[0] + GRID[1]) / 2)
        fx.paste_center(base, fx.pill("¿Tú qué eliges?" if fmt == "encuesta" else "¿Lo sabes?", 50, CLARO, OSCURO,
                                      padx=34, pady=16, radius=8), W / 2, GRID[1] - 220)
    elif fmt == "galeria":                                     # mosaico 2×2 con las 4 primeras
        base = Image.new("RGBA", (W, H), OSCURO + (255,))
        cw, ch = W // 2, (GRID[1] - GRID[0]) // 2
        for k, g in enumerate(golpes[:4]):
            ih = int(cw * H / W)
            im = _cover_fit(g["img"].convert("RGB")).resize((cw, ih)).crop((0, (ih - ch) // 2, cw, (ih - ch) // 2 + ch))
            base.paste(im, ((k % 2) * cw, GRID[0] + (k // 2) * ch))
        band = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
        for y in range(420):
            bd.line([(0, y), (W, y)], fill=(0, 0, 0, int(205 * math.sin(math.pi * y / 420) ** 0.6)))
        base.alpha_composite(band, (0, (GRID[0] + GRID[1]) // 2 - 210))
        hl = fx.headline(G["hook"], 110, 960, 3, color=CLARO, hot=ACENTO, hot_words=_hot(G["hook"]), shadow=True)
        fx.paste_center(base, hl, W / 2, (GRID[0] + GRID[1]) / 2)
    elif fmt == "antes_despues":                               # mitad sin / mitad con postpro
        a, d = golpes[0]["img"], golpes[1]["img"]
        base = _cover_fit(a.convert("RGB")).convert("RGBA")
        base.paste(_cover_fit(d.convert("RGB")).crop((W // 2, 0, W, H)), (W // 2, 0))
        ImageDraw.Draw(base).rectangle([W // 2 - 4, 0, W // 2 + 4, H], fill=ACENTO)
        base.alpha_composite(_degradados())
        fx.paste_center(base, fx.pill("SIN", 50, (40, 42, 48), CLARO, padx=30, pady=14, radius=6), W / 4, GRID[1] - 300)
        fx.paste_center(base, fx.pill("CON", 50, ACENTO, OSCURO, padx=30, pady=14, radius=6), 3 * W / 4, GRID[1] - 300)
        hl = fx.headline(G["hook"], 104, 960, 3, color=CLARO, hot=ACENTO, shadow=True)
        fx.paste_center(base, hl, W / 2, GRID[0] + 140 + hl.height / 2)
    else:                                                      # la imagen más bonita + el titular grande
        img = golpes[-1]["img"] if fmt in ("proceso", "obra") else golpes[0]["img"]
        base = _cover_fit(img.convert("RGB")).convert("RGBA")
        base.alpha_composite(_degradados())
        hl = fx.headline(G["hook"], 120, 960, 3, color=CLARO, hot=ACENTO, hot_words=_hot(G["hook"]), shadow=True)
        fx.paste_center(base, hl, W / 2, GRID[0] + 150 + hl.height / 2)
        if fmt == "proceso":                                   # miniatura del boceto en una esquina
            sk = _cover_fit(golpes[0]["img"].convert("RGB")).resize((300, 533))
            base.paste(sk, (W - 300 - 90, GRID[1] - 533 - 130))
            ImageDraw.Draw(base).rectangle([W - 390, GRID[1] - 663, W - 90, GRID[1] - 130], outline=ACENTO, width=4)
    _marco(base)
    fx.paste_center(base, fx.logo(80, CLARO, ACENTO), W / 2, GRID[1] - 100)
    base.convert("RGB").save(path, "JPEG", quality=92)
    return path


# ------------------------------------------------------------------ revisión
def revisar(path, G):
    """Agente de vídeo. Devuelve {"overall", "issues", "malas": [índices de imagen], ...}."""
    import reviewer
    small = path.replace(".mp4", "_review.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf", "scale=360:640", "-r", "12", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "30", "-c:a", "aac", "-b:a", "48k", small], check=True)
        data = base64.b64encode(open(small, "rb").read()).decode()
        if G["formato"] in QUIZ:
            que = (f"Pregunta: «{G['pregunta']}». Opciones: {'; '.join(G['opciones'])}. La solución NO debe aparecer en el "
                   "vídeo (la publicamos al día siguiente en comentarios): si aparece marcada, es un defecto grave. Una "
                   "sola imagen de fondo oscurecida, a propósito.")
        else:
            que = "Imágenes en orden: " + "; ".join(f"{k + 1}: «{g['label']}» ({g['dur']:.1f} s)" for k, g in enumerate(G["golpes"]))
        res = reviewer.ask_video([{"text": f"""Eres director creativo de una cuenta de TikTok, Instagram y YouTube Shorts
para ESTUDIANTES de arquitectura (TFG, TFM, PFC). Revisa este reel VISUAL (imágenes de arquitectura creadas con IA +
música, sin voz, a propósito). Formato: {NOMBRE[G['formato']]}. Gancho: «{G['hook']}». {que}
Comprueba: que cada imagen sea bonita, verosímil y coherente con su etiqueta (en sin/con postproducción y en el proceso,
que se reconozca el MISMO edificio o encuadre); defectos de IA (geometría imposible, texto o letras raras en la imagen,
objetos deformes); legibilidad de los textos en el móvil y zona segura; que el gancho se entienda en 1,5 s; ritmo;
cierre claro.
ESCALA ANCLADA: 8 = profesional y publicable SIN defectos objetivos (las opiniones de estilo no bajan de 8, van en
"suggestions"); 6-7 = algún defecto objetivo (imagen con defecto de IA visible, etiqueta que no corresponde, texto que se
sale o ilegible); 5 o menos = defecto grave (imagen absurda, edificio famoso reconocible, solución desvelada, vídeo roto).
"malas" = números (1, 2, ...) de las imágenes con defecto objetivo (vacío si ninguna).
Devuelve JSON: {{"overall": number, "issues": [str], "suggestions": [str], "malas": [int], "critical": bool}}"""},
                                  {"inline_data": {"mime_type": "video/mp4", "data": data}}])
    except Exception as e:
        say("revisión de vídeo no disponible:", str(e)[:200])
        return {"overall": 0, "issues": [f"revisor no disponible: {str(e)[:100]}"], "malas": []}
    finally:
        if os.path.exists(small): os.remove(small)
    ov = float(res.get("overall") or 0)
    if ov < 8 and not (res.get("issues") or []) and not res.get("critical"):
        res["overall_raw"] = ov; ov = 8.0                         # escala anclada: sin defectos objetivos, es un 8
    res["overall"] = ov
    reviewer.log("video", {"formato": G["formato"], "hook": G["hook"], "overall": ov, "issues": res.get("issues"),
                           "malas": res.get("malas"), "suggestions": res.get("suggestions")})
    say(f"revisión: {ov}/10", res.get("issues") or "")
    return res


# ------------------------------------------------------------------ descripción
TAGS = {"galeria": "#arquitectura #tfm #estudiantedearquitectura #referentes #architecture #tfg",
        "proceso": "#arquitectura #autocad #revit #render #tfm #estudiantedearquitectura",
        "antes_despues": "#render #postproduccion #arquitectura #tfm #lumion #photoshop",
        "tips": "#arquitectura #tfm #tfg #estudiantedearquitectura #tipsdearquitectura #pfc",
        "obra": "#construccion #arquitectura #obra #estudiantedearquitectura #tfm",
        "test": "#arquitectura #construccion #test #estudiantedearquitectura #tfm #quiz",
        "vf": "#arquitectura #verdaderoofalso #estudiantedearquitectura #construccion #tfm",
        "encuesta": "#arquitectura #tfm #estudiantedearquitectura #encuesta #tfg"}


def descripcion(G):
    fmt = G["formato"]; q, sv = G["cierre"]
    if fmt in QUIZ:
        letras = "VF" if fmt == "vf" else LETRAS
        ops = "\n".join(f"{letras[k]}) {o}" for k, o in enumerate(G["opciones"]))
        txt = (f"{G['pregunta']}\n\n{ops}\n\n👇 {q}: " + ("¿cuál eliges?" if fmt == "encuesta" else "¿cuál es la buena?")
               + f"\n📅 {sv}.\n\n{marca.CTA_SUAVE}\n\n{TAGS[fmt]}")
    else:
        cuerpo = {"galeria": "\n".join(f"{k + 1}. {g['label']}" for k, g in enumerate(G["golpes"])),
                  "tips": "\n".join(f"{k + 1}. {g['label']}" for k, g in enumerate(G["golpes"])),
                  "proceso": " → ".join(g["label"] for g in G["golpes"]),
                  "obra": " → ".join(g["label"] for g in G["golpes"]),
                  "antes_despues": "El mismo render, el mismo encuadre: sin postproducción y con ella."}[fmt]
        cierre = marca.CTA_AC if G.get("ac") else (f"📌 Guárdalo para tu próxima entrega.\n\n{marca.CTA_SUAVE}")
        txt = (f"{G['hook']} ✨\n\n{cuerpo}\n\n👇 {q}" + (f" {sv}" if fmt == "galeria" else "")
               + f"\n\n{cierre}\n\nImágenes creadas con IA.\n\n{TAGS[fmt]}")
    if not marca.limpio(txt):
        raise RuntimeError("la descripción contiene una frase prohibida para AC")
    return txt


# ------------------------------------------------------------------ todo junto
def hacer(formato, out, seed=0, max_rondas=2, solo_ac=None):
    """Genera, monta, revisa y deja el reel listo. Devuelve meta y la pieza (para marcarla usada)."""
    t0 = time.time()
    tematica = formato
    formato = BANCO_DE.get(formato, formato)
    P = pieza(formato, seed, solo_ac)
    say(f"{formato}: {P.get('hook') or P.get('pregunta') or P.get('descripcion')}")
    pasos = imagenes(formato, P)
    say(f"{len(pasos)} imágenes aprobadas en {time.time() - t0:.0f} s")
    bpm = random.Random(str(seed)).choice((80, 84, 88))
    mejor, rev = None, {}
    for ronda in range(max_rondas):
        G = guion(formato, P, pasos, bpm)
        info = render(G, out, seed=f"{seed}-{ronda}", bpm=bpm)
        if not os.environ.get("GEMINI_API_KEY"):                  # prueba local sin IA: sin revisión
            mejor = (G, info, {"overall": None}); break
        rev = revisar(out, G)
        if rev["overall"] >= 8 and not rev.get("critical"):
            mejor = (G, info, rev); break
        malas = [int(m) - 1 for m in (rev.get("malas") or []) if str(m).isdigit() and 0 < int(m) <= len(pasos)]
        if not malas or ronda == max_rondas - 1:
            break
        say("regenero las imágenes", [m + 1 for m in malas])
        for m in malas:                                         # solo las imágenes marcadas
            lab = pasos[m][1]
            ref = [pasos[m - 1][0]] if formato == "antes_despues" and lab == "CON POSTPRO" else \
                  ([pasos[-1][0]] if formato in ("proceso", "obra") and m < len(pasos) - 1 else [])
            idea = next((e["idea"] for e in P.get("escenas", []) + P.get("tips", []) if e.get("label", e.get("tip")) == lab),
                        P.get("idea") or lab)
            nuevo = _gen(f"{idea}. Evita: {'; '.join(rev.get('issues') or [])[:300]}", ref)
            if nuevo is not None:
                pasos[m] = (nuevo, lab)
    if not mejor:
        raise RuntimeError(f"reel visual sin el 8: {rev.get('overall')} · {(rev.get('issues') or [''])[:2]}")
    G, info, rev = mejor
    cover = portada(G, out.replace(".mp4", "_portada.jpg"))
    cap = descripcion(G)
    open(out.replace(".mp4", ".txt"), "w").write(cap)
    meta = {"formato": formato, "hook": G.get("pregunta") or G["hook"], "duration": info["duration"], "cover": cover,
            "thumb_ms": 1500, "review_score": rev["overall"], "ids": P["ids"], "tematica": tematica,
            "ac": bool(G.get("ac")), "solucion": solucion(formato, P),
            "titulo": (G.get("pregunta") or G["hook"])[:95]}
    say(f"listo en {time.time() - t0:.0f} s · {info['duration']} s de vídeo · nota {rev['overall']}")
    return meta

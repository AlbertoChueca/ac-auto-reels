"""Los 9 agentes que pulen cada reel de AC (todos con Gemini; en paralelo siempre que se puede, para ir rápido).

  0. cazatendencias   1 vez al día: busca en Google lo que está funcionando AHORA en reels, TikToks y Shorts del nicho
                      (formatos, ganchos, temas calientes por la época del curso, ejemplos con enlace) -> tendencias.json
  1. estratega        1 vez al día: cruza los resultados reales (performance.json) con las tendencias -> playbook.json
                      (ganchos, patrones, qué evitar, pesos de cada temática). Lo usan el guionista, el gancho, la
                      descripción, el calendario y la ampliación del banco.
  2. guionista        guion hablado a partir de la pieza del banco (sin añadir datos que no estén en ella).
  3. gancho           5 ganchos para los 2 primeros segundos, los puntúa y elige el mejor (sin repetir recientes).
  4. verificador      revisa el rigor de cada frase contra la pieza y las reglas de AC; corrige o vuelve al banco.
  5. director de voz  dirección de actor por frase: sube, baja, pausa, remata (los altibajos de la voz).
  6. directora de arte prompts de imagen coherentes de serie + revisión de cada imagen generada (visual.revisa).
  7. revisor de vídeo ve y ESCUCHA el reel terminado: nota anclada, mínimo 8 (reel.revisar).
  8. editor           descripción, hashtags y título de YouTube, siempre con la web.
3, 4 van a la vez; 5, 6 y 8 también. Si un agente falla, el reel sigue con la versión anterior (nunca se queda parado)
y todo lo que se publica sale del banco verificado o pasa el verificador.
"""
import datetime, json, os, re
from concurrent.futures import ThreadPoolExecutor

import marca

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYBOOK = os.path.join(HERE, "playbook.json")
PERF = os.path.join(HERE, "performance.json")
WEB_URL = "https://arquitecturaconfidencial.com"
VENTA = ("documentacion", "auditoria")
AUDIENCIA = ("estudiantes de arquitectura de España (y Latinoamérica) que preparan el TFM, el TFG/PFC o la asignatura de "
             "Proyectos: jóvenes, con poco tiempo, mucha presión de entregas y ganas de aprobar con buena nota")


def say(*a):
    print("agentes:", *a, flush=True)


def _ask(prompt, temp=0.6, careful=False):
    import gemini
    return gemini.ask(prompt, temp, careful=careful)


def _log(kind, data):
    try:
        with open(os.path.join(HERE, "review_log.jsonl"), "a") as f:
            f.write(json.dumps({"date": str(datetime.date.today()), "kind": kind, **data}, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ================================================================== 0 · cazatendencias
TENDENCIAS = os.path.join(HERE, "tendencias.json")


def tendencias():
    try:
        return json.load(open(TENDENCIAS))
    except Exception:
        return {}


def cazatendencias(force=False):
    """Qué está funcionando ESTA semana en el nicho. Dos búsquedas a la vez (nicho y formatos generales de reels) y una
    síntesis en JSON con ejemplos y enlaces. Si falla, se queda la versión anterior."""
    t = tendencias()
    if t.get("fecha") == str(datetime.date.today()) and not force:
        return t
    import gemini
    hoy = datetime.date.today()
    mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
           "diciembre"][hoy.month - 1]
    q1 = (f"Busca los reels de Instagram, TikToks y YouTube Shorts sobre arquitectura para estudiantes (TFM, TFG, PFC, "
          f"asignatura de Proyectos, renders, maquetas, referentes, IA para arquitectura, vida de estudiante de "
          f"arquitectura) que más están funcionando en {mes} de {hoy.year}, en español y en inglés. Para cada patrón: "
          f"formato, gancho de los 2 primeros segundos, duración, por qué funciona y un ejemplo concreto (cuenta o "
          f"vídeo). Responde en español, en viñetas, máx. 350 palabras.")
    q2 = (f"¿Qué formatos, estructuras de gancho y tendencias de edición de Reels, TikTok y YouTube Shorts educativos están "
          f"consiguiendo más guardados y compartidos en {mes} de {hoy.year}? ¿Qué penalizan ahora los algoritmos? "
          f"Responde en español, en viñetas, máx. 250 palabras.")
    try:
        with ThreadPoolExecutor(2) as ex:
            f1 = ex.submit(gemini.ask_search, q1, 0.4, True); f2 = ex.submit(gemini.ask_search, q2, 0.4, True)
            (t1, s1), (t2, s2) = f1.result(), f2.result()
    except Exception as e:
        say("cazatendencias sin búsqueda:", str(e)[:150])
        return t
    try:
        r = _ask(f"""Eres el cazatendencias de una cuenta de reels para {AUDIENCIA}. Hoy es {hoy}.
Con esta investigación (solo lo que esté respaldado; nada inventado), resume lo que funciona AHORA.
Investigación del nicho: {t1[:3500]}
Investigación de formatos: {t2[:2500]}
Ten en cuenta la época del curso en España ({mes}): entregas, correcciones, defensas, convocatorias.
Devuelve JSON: {{"formatos_que_funcionan": [str], "ganchos_que_funcionan": [str], "temas_calientes": [str],
"tendencias_de_edicion": [str], "que_penaliza_el_algoritmo": [str], "ejemplos": [{{"que": str, "por_que": str}}],
"ideas_de_reel": [str]}}""", 0.4)
        r["fecha"] = str(hoy)
        r["fuentes"] = [s for s in (s1 + s2) if s.get("url")][:12]
        json.dump(r, open(TENDENCIAS, "w"), ensure_ascii=False, indent=1)
        say(f"cazatendencias: {len(r.get('formatos_que_funcionan') or [])} formatos, "
            f"{len(r.get('temas_calientes') or [])} temas calientes, {len(r['fuentes'])} fuentes")
        return r
    except Exception as e:
        say("cazatendencias: síntesis fallida:", str(e)[:150])
        return t


def _tend_texto(t):
    if not t:
        return "(sin tendencias todavía)"
    return json.dumps({k: t.get(k) for k in ("formatos_que_funcionan", "ganchos_que_funcionan", "temas_calientes",
                                             "tendencias_de_edicion", "que_penaliza_el_algoritmo")}, ensure_ascii=False)[:2200]


# ================================================================== 1 · estratega
def _recompensa(r):
    v = max(1, r.get("views") or r.get("reach") or 0)
    return ((r.get("saved") or 0) * 3 + (r.get("shares") or 0) * 3 + (r.get("comments") or 0) * 2 + (r.get("likes") or 0)) / v


def resumen_resultados():
    try:
        perf = json.load(open(PERF))
    except Exception:
        return {}, []
    por = {}
    for r in perf.values():
        if r.get("views") or r.get("reach"):
            por.setdefault(r.get("tematica"), []).append(r)
    medias = {t: round(sum(_recompensa(x) for x in v) / len(v), 4) for t, v in por.items() if t}
    top = sorted(perf.values(), key=_recompensa, reverse=True)
    return medias, [{"tematica": r.get("tematica"), "hook": r.get("hook"), "views": r.get("views"),
                     "guardados": r.get("saved"), "compartidos": r.get("shares"), "comentarios": r.get("comments")}
                    for r in top[:6]]


def playbook():
    try:
        return json.load(open(PLAYBOOK))
    except Exception:
        return {}


def estratega(force=False):
    pb = playbook()
    if pb.get("fecha") == str(datetime.date.today()) and not force:
        return pb
    medias, top = resumen_resultados()
    investigacion = _tend_texto(cazatendencias(force=force))
    try:
        r = _ask(f"""Eres el estratega de contenido de una cuenta de TikTok, Instagram y YouTube Shorts para {AUDIENCIA}.
Objetivo: que guarden, compartan y comenten, y que el 20 % de venta lleve a pedir la auditoría gratuita del TFM.
Resultados reales por temática (recompensa = (guardados×3 + compartidos×3 + comentarios×2 + likes) / vistas): {json.dumps(medias, ensure_ascii=False)}
Mejores publicaciones: {json.dumps(top, ensure_ascii=False)}
Tendencias de esta semana (del cazatendencias): {investigacion}
Escribe el playbook de esta semana. Si hay pocos datos (menos de 10 publicaciones), pesos = 1 en todo.
Devuelve JSON: {{"ganchos_que_funcionan": [str], "patrones": [str], "evitar": [str], "tono_voz": str,
"duracion_objetivo_s": number, "pesos": {{"tips_tfm": number, "tips_proyectos": number, "referentes": number,
"ia": number, "test": number, "vf": number}}, "hashtags": [str]}}""", 0.4)
        r["fecha"] = str(datetime.date.today()); r["datos"] = medias
        json.dump(r, open(PLAYBOOK, "w"), ensure_ascii=False, indent=1)
        say("estratega: playbook actualizado")
        return r
    except Exception as e:
        say("estratega omitido:", str(e)[:150])
        return pb


def _pb_texto(pb):
    t = tendencias()
    if not pb and not t:
        return "(sin playbook todavía)"
    out = {k: pb.get(k) for k in ("ganchos_que_funcionan", "patrones", "evitar", "tono_voz", "duracion_objetivo_s")} if pb else {}
    if t:
        out["tendencias_ahora"] = {k: t.get(k) for k in ("ganchos_que_funcionan", "formatos_que_funcionan", "temas_calientes")}
    return json.dumps(out, ensure_ascii=False)[:2600]


# ================================================================== guion de reserva (sin IA): solo datos del banco
def guion_base(tematica, P):
    venta = tematica in VENTA
    if tematica in ("test", "vf", "encuesta"):
        cierre = ("Comenta la letra y mañana te leo los resultados." if tematica == "encuesta" else
                  "Comenta tu respuesta: mañana publicamos la solución en comentarios.")
        return {"hook_pantalla": {"test": "TEST DE ARQUITECTURA", "vf": "¿VERDADERO O FALSO?", "encuesta": "ENCUESTA"}[tematica],
                "hook_voz": {"test": "A ver si aciertas esta.", "vf": "¿Verdadero o falso? Piénsalo bien.",
                             "encuesta": "Te leo en comentarios."}[tematica],
                "pregunta_voz": P["pregunta"], "cierre_voz": cierre,
                "cierre_pantalla": ["Comenta tu voto" if tematica == "encuesta" else "Comenta tu respuesta",
                                    "Mañana, los resultados" if tematica == "encuesta" else "Solución mañana en comentarios"]}
    if tematica == "postpro":
        return {"hook_pantalla": "Tu render sin y con postproducción", "hook_voz": "Mira lo que cambia tu render con una buena postproducción.",
                "escenas": [{"titulo": "Con postpro", "sub": "", "voz": v} for v in
                            ("Cielo, luz cálida y sombras: el edificio cobra vida.", "Materiales con textura y vegetación: ya parece real.",
                             "Personas y atmósfera: ahora tiene escala.")],
                "cierre_voz": "Guárdalo para tu próxima entrega. Más en arquitectura confidencial punto com.",
                "cierre_pantalla": ["¿Cuál te sorprende más?", "Guárdalo para tu entrega"]}
    esc = [{"titulo": p["titulo"], "sub": p.get("ref", ""), "voz": (f"{p['ref'].split(' (')[0].replace(' · ', ', de ')}. " if p.get("ref") else "") + p["dato"],
            "idea": p["idea"]} for p in P["puntos"]]
    hook = P["hook"]
    cierre_voz = ("Si vas justo con el TFM, pide tu auditoría gratuita en arquitectura confidencial punto com." if venta else
                  "Guárdalo para tu TFM y compártelo con quien lo necesite. Tienes más en arquitectura confidencial punto com.")
    cierre = (["¿Vas justo con el TFM?", "Auditoría gratuita en la web"] if venta else
              ["¿Cuál te ha servido más?", "Guárdalo para tu entrega"])
    return {"hook_pantalla": hook, "hook_voz": hook + ".", "escenas": esc, "cierre_voz": cierre_voz, "cierre_pantalla": cierre}


# ================================================================== forma segura del guion
def normaliza(G, base, tematica):
    """Tras cada agente: si algo viene mal formado, se repara con el borrador del banco (nunca rompe el montaje)."""
    G = dict(G)
    for k in ("hook_pantalla", "hook_voz", "cierre_voz"):
        if not isinstance(G.get(k), str) or not G[k].strip():
            G[k] = base[k]
    cp = G.get("cierre_pantalla")
    if not (isinstance(cp, list) and len(cp) >= 2 and all(isinstance(x, str) and x.strip() for x in cp[:2])):
        G["cierre_pantalla"] = base["cierre_pantalla"]
    G["cierre_pantalla"] = G["cierre_pantalla"][:2]
    if "confidencial" not in G["cierre_voz"].lower():
        G["cierre_voz"] = G["cierre_voz"].rstrip(". ") + ". Más en arquitectura confidencial punto com."
    if tematica in ("test", "vf", "encuesta"):                     # el cierre del test anuncia la solución, siempre
        G["cierre_pantalla"] = base["cierre_pantalla"]
        G["hook_pantalla"] = re.split(r"[:·|-]", G["hook_pantalla"])[0].strip().upper()[:30] or base["hook_pantalla"]
        if not re.match(r"^(TEST|¿?VERDADERO|ENCUESTA)", G["hook_pantalla"]):
            G["hook_pantalla"] = base["hook_pantalla"]
        if "mañana" not in G["cierre_voz"].lower():
            G["cierre_voz"] = base["cierre_voz"]
    if tematica in VENTA:
        G["cierre_pantalla"] = base["cierre_pantalla"]
        if "auditor" not in G["cierre_voz"].lower():
            G["cierre_voz"] = base["cierre_voz"]
    if "confidencial" not in G["cierre_voz"].lower():
        G["cierre_voz"] = G["cierre_voz"].rstrip(". ") + ". Más en arquitectura confidencial punto com."
    if "pregunta_voz" in base and not (isinstance(G.get("pregunta_voz"), str) and G["pregunta_voz"].strip()):
        G["pregunta_voz"] = base["pregunta_voz"]
    if not base.get("escenas"):
        G.pop("escenas", None)
    else:
        esc = G.get("escenas") if isinstance(G.get("escenas"), list) else []
        if len(esc) != len(base["escenas"]):
            esc = base["escenas"]
        G["escenas"] = [{"titulo": (e.get("titulo") if isinstance(e, dict) and e.get("titulo") else b["titulo"]),
                         "voz": (e.get("voz") if isinstance(e, dict) and e.get("voz") else b["voz"]),
                         "sub": b.get("sub", "") if tematica == "referentes" else (e.get("sub", "") if isinstance(e, dict) else ""),
                         "idea": b.get("idea")} for e, b in zip(esc, base["escenas"])]
    return G


# ================================================================== 2 · guionista
def guionista(tematica, P, pb):
    base = guion_base(tematica, P)
    venta = tematica in VENTA
    quiz = tematica in ("test", "vf", "encuesta")
    reglas = ("Es un test: NO digas la respuesta ni la insinúes. 'pregunta_voz' lee la pregunta (puedes hacerla más "
              "natural sin cambiar su sentido). Las opciones salen en pantalla, no las leas." if quiz else
              "Una 'voz' por escena, en el mismo orden. Cada 'voz': 1 o 2 frases, máx. 14 palabras (en referentes, 18), que expliquen el "
              "punto con SOLO la información de su 'dato' (y en referentes, nombra la obra y su autor). Empieza alguna con "
              "un conector natural («Ojo,», «Y esto es clave:», «Truco:»). 'titulo' en pantalla: máx. 5 palabras.")
    try:
        r = _ask(f"""Eres guionista de reels para {AUDIENCIA}. Escribe el guion HABLADO de este reel (voz en off de 25-35 s EN TOTAL;
más largo se abandona). Español de España, de tú, como un compañero mayor que ya aprobó: cercano, directo, con ritmo, frases cortas,
nada de lenguaje de anuncio ni de IA («descubre», «sumérgete», «increíble», «en el mundo de»: prohibido).
{reglas}
{'Reel de VENTA (20 %): enseña con naturalidad el tipo de documentación que el equipo de AC ayuda a preparar (si la pieza tiene «portfolio», las imágenes son TRABAJOS REALES del equipo: puedes decir «esto es un trabajo real de nuestro equipo»). Asesoría y apoyo técnico en las fases que se atascan; nunca «te hacemos el TFM».' if venta else 'Contenido ÚTIL (80 %): valor puro, cero venta en el cuerpo.'}
'cierre_voz': 1 frase que invite a {'pedir la auditoría gratuita' if venta else 'guardarlo o compartirlo'} y diga la web «arquitectura confidencial punto com».
Lo que mejor funciona ahora (playbook): {_pb_texto(pb)}
Pieza del banco (verificada; no añadas datos nuevos): {json.dumps(P, ensure_ascii=False)[:3500]}
Devuelve JSON con la misma forma que este borrador, mejorado: {json.dumps(base, ensure_ascii=False)[:3000]}""", 0.75)
        if not quiz and len(r.get("escenas") or []) != len(base["escenas"]):
            raise ValueError("número de escenas distinto")
        for k in base:
            r.setdefault(k, base[k])
        if not quiz:
            lim = 18 if tematica == "referentes" else 16
            for e, b in zip(r["escenas"], base["escenas"]):
                if len(str(e.get("voz", "")).split()) > lim:
                    e["voz"] = b["voz"] if len(b["voz"].split()) <= lim + 6 else e["voz"]
                e["idea"] = b.get("idea"); e.setdefault("sub", b.get("sub", ""))
                if tematica == "referentes":
                    e["sub"] = b["sub"]                               # la referencia, siempre la verificada
        if venta:                                                     # el cierre de venta no se toca
            r["cierre_pantalla"] = base["cierre_pantalla"]
            if "auditor" not in r.get("cierre_voz", "").lower():
                r["cierre_voz"] = base["cierre_voz"]
        return r, base
    except Exception as e:
        say("guionista omitido, uso el banco:", str(e)[:150])
        return dict(base), base


# ================================================================== 3 · gancho
def gancho(tematica, G, P, pb, recientes=()):
    quiz = tematica in ("test", "vf", "encuesta")
    n = len(G.get("escenas") or [])
    try:
        r = _ask(f"""Eres editor de ganchos de reels para {AUDIENCIA}. Los 2 primeros segundos deciden si se quedan.
Tema del reel: «{P.get('hook') or P.get('pregunta')}». Lo que se ve, en orden: {json.dumps([e.get('titulo') for e in G.get('escenas') or []], ensure_ascii=False)}.
El gancho tiene que describir FIELMENTE ese contenido (si son aciertos, no digas «errores»; si son 5, que sean 5).
Gancho actual: pantalla «{G['hook_pantalla']}», voz «{G['hook_voz']}».
Escribe 5 ganchos distintos (curiosidad, error, promesa concreta, pregunta directa al estudiante...) y puntúa cada uno de
1 a 10 por lo que haría parar el scroll a un estudiante de TFM o de Proyectos.
Reglas: 'pantalla' máx. 7 palabras{'; si lleva número, debe ser ' + str(n) if n else ''}{'; en tests, la pantalla es una etiqueta corta de 2-4 palabras SIN dos puntos, tipo «TEST DE CONSTRUCCIÓN»' if quiz else ''};
'voz' máx. 14 palabras, natural, de España, sin clickbait falso ni promesas («apruebas seguro», «garantizado»: prohibido).
NO nombres obras, arquitectos, escuelas, herramientas ni datos que no estén en el reel: el gancho tiene que cumplirse en el propio vídeo.
No repitas estos ganchos recientes: {json.dumps(list(recientes)[-12:], ensure_ascii=False)}
Lo que funciona (playbook): {_pb_texto(pb)}
Devuelve JSON: {{"opciones": [{{"pantalla": str, "voz": str, "nota": number}}]}}""", 0.9)
        permitido = json.dumps(P, ensure_ascii=False).lower()
        nombres = lambda t: [w for w in re.findall(r"\b[A-ZÁÉÍÓÚ][a-záéíóúñ]+(?:\s[A-ZÁÉÍÓÚ][a-záéíóúñ]+)+", t)]
        ops = [o for o in r.get("opciones") or [] if o.get("pantalla") and o.get("voz") and marca.limpio(o["pantalla"] + o["voz"])
               and all(n.lower() in permitido for n in nombres(o["pantalla"] + " " + o["voz"]))
               and len(o["pantalla"].split()) <= 8 and o["pantalla"] not in recientes]
        if n:
            ops = [o for o in ops if not re.search(r"\d", o["pantalla"]) or str(n) in o["pantalla"]]
        if not ops:
            return G["hook_pantalla"], G["hook_voz"], []
        mejor = max(ops, key=lambda o: float(o.get("nota") or 0))
        return mejor["pantalla"], mejor["voz"], [o for o in ops if o is not mejor]
    except Exception as e:
        say("gancho omitido:", str(e)[:150])
        return G["hook_pantalla"], G["hook_voz"], []


# ================================================================== 4 · verificador
def _frases(G):
    out = [G["hook_voz"], G.get("pregunta_voz", "")] + [e["voz"] for e in G.get("escenas") or []] + [G["cierre_voz"]]
    return [x for x in out if x]


def verificador(tematica, G, P, base):
    """Devuelve el guion verificado: corregido por el verificador o, si no, con las frases del banco."""
    todo = json.dumps(G, ensure_ascii=False)
    if not marca.limpio(todo):
        say("verificador: frase prohibida; vuelvo al banco")
        return dict(base), ["frase prohibida"]
    try:
        r = _ask(f"""Eres el verificador técnico de una cuenta para estudiantes de arquitectura. Eres arquitecto y
profesor, muy estricto. Revisa este guion contra su pieza verificada.
NO son problema: la web «arquitectura confidencial punto com» / arquitecturaconfidencial.com, la invitación a guardar,
compartir o comentar y que se le hable de tú al estudiante. {'La auditoría gratuita del TFM es obligatoria en el cierre.' if tematica in VENTA else 'Este reel es de contenido ÚTIL: NO añadas la auditoría ni ninguna venta (no es obligatoria aquí).'}
Marca como problema: cualquier dato técnico falso o dudoso; cualquier dato que NO esté en la pieza (obra, autor, año,
cifra, norma, herramienta); que en un test se desvele la respuesta; promesas («apruebas seguro», «te hacemos el TFM»,
«nadie lo sabrá»); frases que no suenen a español de España; títulos de pantalla de más de 6 palabras.
{'Es un reel de VENTA: SÍ está permitido decir que el equipo de AC ayuda o acompaña a preparar esa documentación y que las imágenes son trabajos reales del equipo; NO está permitido decir que se le hace el TFM al alumno ni que nadie lo sabrá.' if tematica in VENTA else ''}
Pieza: {json.dumps(P, ensure_ascii=False)[:3500]}
Guion: {todo[:3500]}
Si hay problemas, devuelve el guion corregido (misma forma, mismo número de escenas, corrige solo lo necesario).
Devuelve JSON: {{"ok": bool, "problemas": [str], "guion": object|null}}""", 0.1, careful=True)
        probs = r.get("problemas") or []
        if r.get("ok") and not probs:
            return G, []
        g2 = r.get("guion")
        if isinstance(g2, dict) and marca.limpio(json.dumps(g2, ensure_ascii=False)) and \
                len(g2.get("escenas") or []) == len(G.get("escenas") or []):
            for k in G:
                g2.setdefault(k, G[k])
            for e, b in zip(g2.get("escenas") or [], G.get("escenas") or []):
                e["idea"] = b.get("idea"); e["sub"] = b.get("sub", "") if tematica == "referentes" else e.get("sub", "")
            if tematica in VENTA:
                g2["cierre_pantalla"] = base["cierre_pantalla"]
                if "auditor" not in g2.get("cierre_voz", "").lower():
                    g2["cierre_voz"] = base["cierre_voz"]
            say("verificador: corregido:", "; ".join(probs)[:200])
            return g2, probs
        say("verificador: problemas sin corrección válida; vuelvo al banco:", "; ".join(probs)[:200])
        b = dict(base); b["hook_pantalla"], b["hook_voz"] = G["hook_pantalla"], G["hook_voz"]
        return b, probs
    except Exception as e:
        say("verificador no disponible; uso el banco:", str(e)[:150])
        b = dict(base); b["hook_pantalla"], b["hook_voz"] = G["hook_pantalla"], G["hook_voz"]
        return b, ["verificador no disponible"]


# ================================================================== 5 · director de voz
ARCO = ["excited and punchy, rising intonation, grab attention", "confident, explaining to a friend",
        "lower and closer, confiding, then lift on the key word", "energetic, faster, emphasise the key word",
        "surprised, playful", "calm and clear, slight pause before the key idea", "warm, upbeat, smiling, inviting"]


def director_voz(frases, tematica, pb, insistir=""):
    defecto = [ARCO[0]] + [ARCO[1 + (i % 5)] for i in range(len(frases) - 2)] + [ARCO[-1]]
    defecto = defecto[:len(frases)] if len(frases) > 1 else [ARCO[0]]
    try:
        r = _ask(f"""You are a voice director for short vertical videos for architecture students (Spain). The narrator is
ALWAYS the same young Castilian-Spanish man: directions change energy, pace and emphasis, NEVER the character,
gender, age or accent (no whispering, no character voices). Write one short acting direction (max 14 words, English) per line so the whole reel
has clear ups and downs and sounds human, never flat: a hook with punch, variety in the middle (closer/softer, then
energetic, surprised, a deliberate pause before the key idea...), and a warm, energetic close. Never the same direction
twice in a row. Mention pace (faster/slower) and which word to stress.
{('Previous take was criticised: ' + insistir + '. Fix that.') if insistir else ''}
Tone guide: {pb.get('tono_voz', '') if pb else ''}
Lines (Spanish): {json.dumps(frases, ensure_ascii=False)}
Return JSON: {{"direcciones": [str]}}""", 0.7)
        d = [str(x)[:160] for x in r.get("direcciones") or []]
        if len(d) == len(frases):
            return d
    except Exception as e:
        say("director de voz omitido:", str(e)[:120])
    return defecto


# ================================================================== 6 · directora de arte (prompts; la revisión está en visual.revisa)
def directora_arte(tematica, escenas):
    ideas = [e.get("idea") or e.get("titulo") for e in escenas]
    try:
        r = _ask(f"""Eres directora de arte de una cuenta de arquitectura para estudiantes. Convierte cada idea en un
prompt de imagen fotográfica vertical potente y coherente con las demás (misma serie: misma luz, misma paleta, mismo
tipo de cámara), que ilustre bien su título. {'Son referentes: la imagen es CONCEPTUAL, un edificio ORIGINAL que aplica la misma estrategia, NUNCA una copia de la obra real.' if tematica == 'referentes' else ''}
Sin texto en la imagen, sin edificios famosos, sin personas reconocibles.
Escenas: {json.dumps([{'titulo': e['titulo'], 'idea': i} for e, i in zip(escenas, ideas)], ensure_ascii=False)}
Devuelve JSON: {{"estilo_serie": str, "prompts": [str]}}""", 0.6)
        ps = r.get("prompts") or []
        if len(ps) == len(escenas):
            est = r.get("estilo_serie") or ""
            return [f"{p}. {est}".strip() for p in ps]
    except Exception as e:
        say("directora de arte omitida:", str(e)[:120])
    return ideas


# ================================================================== 8 · editor (descripción, hashtags, título de YouTube)
TAGS = {"tips_tfm": "#tfm #arquitectura #estudiantedearquitectura #tfmarquitectura #tfg #arquitecto",
        "tips_proyectos": "#proyectosarquitectonicos #arquitectura #estudiantedearquitectura #etsam #tfg #arquitecto",
        "referentes": "#referentes #arquitectura #estudiantedearquitectura #architecture #tfm #historiadelaarquitectura",
        "ia": "#iaarquitectura #arquitectura #ia #render #tfm #estudiantedearquitectura",
        "documentacion": "#tfm #arquitectura #construccion #detallesconstructivos #estudiantedearquitectura",
        "auditoria": "#tfm #tfmarquitectura #arquitectura #estudiantedearquitectura #tfg",
        "postpro": "#render #postproduccion #arquitectura #tfm #photoshop",
        "test": "#arquitectura #construccion #quiz #estudiantedearquitectura #tfm",
        "vf": "#arquitectura #verdaderoofalso #estudiantedearquitectura #construccion",
        "encuesta": "#arquitectura #tfm #estudiantedearquitectura #encuesta"}


def descripcion_base(tematica, G, P):
    venta = tematica in VENTA
    if tematica in ("test", "vf", "encuesta"):
        letras = "VF" if tematica == "vf" else "ABCD"
        ops = "\n".join(f"{letras[k]}) {o}" for k, o in enumerate(P["opciones"]))
        cuerpo = f"{P['pregunta']}\n\n{ops}\n\n👇 {G['cierre_pantalla'][0]}. 📅 {G['cierre_pantalla'][1]}."
    else:
        lin = []
        for k, e in enumerate(G.get("escenas") or []):
            lin.append(f"{k + 1}. {e['titulo']}" + (f" — {e['sub']}" if e.get("sub") else ""))
        cuerpo = f"{G['hook_pantalla']} 👇\n\n" + "\n".join(lin) + "\n\n📌 Guárdalo para tu próxima entrega."
    fin = (f"👉 Pide tu auditoría gratuita del TFM: {WEB_URL}" if venta else
           f"¿Vas justo con el TFM? Auditoría gratuita en {WEB_URL}")
    if P.get("portfolio") and any(P["portfolio"]):
        nota = "Planos: trabajos reales de nuestro equipo (datos del proyecto anonimizados)."
    else:
        nota = "Imágenes creadas con IA" + (" (conceptuales: busca las obras reales)." if tematica == "referentes" else ".")
    return f"{cuerpo}\n\n{fin}\n\n{nota}\n\n{TAGS.get(tematica, TAGS['tips_tfm'])}"


def editor(tematica, G, P, pb):
    base = descripcion_base(tematica, G, P)
    titulo = (G.get("hook_pantalla") if tematica not in ("test", "vf", "encuesta") else P["pregunta"])[:90]
    try:
        r = _ask(f"""Eres el editor de redes de una cuenta para {AUDIENCIA}. Mejora esta descripción para que la guarden y
la compartan: primera línea con gancho (máx. 90 caracteres), cuerpo escaneable, sin inventar datos, sin desvelar la
solución de un test. Mantén la línea con la web {WEB_URL} y la nota final sobre el origen de las imágenes TAL CUAL (IA o planos reales). 5-7 hashtags del nicho en
español (playbook: {', '.join((pb or {}).get('hashtags') or [])}). Título de YouTube Shorts: máx. 80 caracteres, con
palabras que busquen los estudiantes (TFM, Proyectos, arquitectura).
Descripción actual: {base}
Devuelve JSON: {{"descripcion": str, "titulo_youtube": str}}""", 0.6)
        d, t = (r.get("descripcion") or "").strip(), (r.get("titulo_youtube") or "").strip()
        if not d or WEB_URL not in d or not marca.limpio(d) or len(d) > 2100:
            raise ValueError("descripción no válida")
        if tematica in ("test", "vf", "encuesta") and "mañana" not in d.lower():
            d = d.replace(f"\n\n¿Vas", f"\n📅 {G['cierre_pantalla'][1]}.\n\n¿Vas", 1) if "\n\n¿Vas" in d else d + f"\n📅 {G['cierre_pantalla'][1]}."
        if P.get("portfolio") and any(P["portfolio"]) and "trabajos reales" not in d.lower():
            raise ValueError("falta la nota de planos reales")
        if tematica in ("test", "vf") and P.get("explicacion") and P["explicacion"][:40].lower() in d.lower():
            raise ValueError("desvela la solución")
        return d, (t if t and marca.limpio(t) else titulo)[:95]
    except Exception as e:
        say("editor omitido, descripción base:", str(e)[:120])
        return base, titulo


# ================================================================== todo el guion de un reel
def preparar(tematica, P, recientes=()):
    """Agentes 1-6 y 8. Devuelve (guion final, prompts de imagen, direcciones de voz, descripción, título YouTube)."""
    pb = estratega() if os.environ.get("GEMINI_API_KEY") else {}
    if not os.environ.get("GEMINI_API_KEY"):
        G = guion_base(tematica, P)
        esc = G.get("escenas") or []
        frases = _frases(G)
        return G, [e.get("idea") for e in esc], [ARCO[i % len(ARCO)] for i in range(len(frases))], \
            descripcion_base(tematica, G, P), G["hook_pantalla"][:90]
    G, base = guionista(tematica, P, pb)
    G = normaliza(G, base, tematica)
    with ThreadPoolExecutor(2) as ex:                                 # gancho y verificador, a la vez
        fg = ex.submit(gancho, tematica, G, P, pb, recientes)
        fv = ex.submit(verificador, tematica, G, P, base)
        hp, hv, _ = fg.result(); G, probs = fv.result()
    G = normaliza(G, base, tematica)
    G["hook_pantalla"], G["hook_voz"] = hp, hv
    G = normaliza(G, base, tematica)
    frases = _frases(G)
    with ThreadPoolExecutor(3) as ex:                                 # voz, arte y descripción, a la vez
        fd = ex.submit(director_voz, frases, tematica, pb)
        fa = ex.submit(directora_arte, tematica, G.get("escenas") or []) if G.get("escenas") else None
        fe = ex.submit(editor, tematica, G, P, pb)
        direcciones = fd.result(); prompts = fa.result() if fa else []; desc, titulo = fe.result()
    _log("guion", {"tematica": tematica, "hook": hp, "verificador": probs, "frases": frases, "voz": direcciones})
    return G, prompts, direcciones, desc, titulo

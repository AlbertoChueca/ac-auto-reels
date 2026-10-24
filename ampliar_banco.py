"""Amplía fuentes/visual.json cuando una sección se queda con pocas piezas sin usar (menos de MIN_LIBRES).

    python ampliar_banco.py            # amplía lo que haga falta
    python ampliar_banco.py test 6     # fuerza 6 piezas nuevas de «test»

Tests y V/F: un modelo escribe la pregunta y OTRO (modo cuidadoso, temperatura baja) la resuelve a ciegas, sin ver la
solución propuesta. Solo entra si los dos coinciden, el verificador está seguro y no es ambigua. Galerías, tips,
encuestas y escenas: se comprueba el formato y que no haya frases prohibidas para AC (marca.limpio).
"""
import hashlib, json, os, sys

import marca

HERE = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(HERE, "fuentes", "visual.json")
MIN_LIBRES = {"test": 4, "vf": 3, "encuesta": 2, "galeria": 3, "tips": 3, "antes_despues": 3, "proceso": 2, "obra": 2}
LOTE = {"test": 8, "vf": 6, "encuesta": 4, "galeria": 4, "tips": 4, "antes_despues": 4, "proceso": 3, "obra": 2}
TEMAS = ("construcción, estructuras, instalaciones, dibujo arquitectónico, BIM y Revit, urbanismo, materiales, "
         "acondicionamiento y eficiencia energética, historia de la construcción (sin nombrar edificios ni arquitectos)")


def libres(B, sec):
    try:
        usados = {x["id"] for x in json.load(open(os.path.join(HERE, "used.json")))}
    except Exception:
        usados = set()
    return sum(1 for p in B[sec] if f"visual:{p['id']}" not in usados)


def _id(sec, texto):
    return f"{sec[:3]}_{hashlib.sha1(texto.encode()).hexdigest()[:8]}"


def _ejemplos(B, sec, n=3):
    return json.dumps(B[sec][:n], ensure_ascii=False)[:2500]


def proponer(B, sec, n):
    import gemini
    ya = [p.get("pregunta") or p.get("hook") or p.get("descripcion") for p in B[sec]]
    reglas = {
        "test": f"Preguntas de test con 4 opciones para estudiantes de arquitectura en España ({TEMAS}). La CORRECTA va "
                "SIEMPRE la primera en 'opciones'. Una sola respuesta correcta sin discusión posible; distractores "
                "verosímiles; pregunta de máx. 110 caracteres y opciones de máx. 45. 'explicacion' de 1-2 frases. "
                "'idea': escena para una imagen de fondo SIN texto que ilustre el tema.",
        "vf": f"Afirmaciones de verdadero o falso para estudiantes de arquitectura en España ({TEMAS}). 'opciones' = "
              "[\"Verdadero\", \"Falso\"] con la CORRECTA PRIMERO (si es falsa: [\"Falso\", \"Verdadero\"]). Sin "
              "ambigüedad. Máx. 110 caracteres. 'explicacion' de 1-2 frases. 'idea': escena para la imagen de fondo.",
        "encuesta": "Encuestas sin respuesta correcta para estudiantes de arquitectura que preparan el TFM/TFG (hábitos, "
                    "programas, gustos, miedos). 4 opciones cortas (máx. 30 caracteres). 'idea': escena de fondo.",
        "galeria": "Galerías de referentes para un TFM: 'hook' (máx. 45 caracteres, menciona el TFM o el proyecto), "
                   "'cierre' (pregunta corta) y 6 'escenas' con 'label' (1-3 palabras) e 'idea' (descripción de una "
                   "imagen de arquitectura ORIGINAL, nunca un edificio real o famoso).",
        "tips": "Tips visuales para estudiantes de arquitectura: 'hook' («5 tips para...», máx. 50 caracteres), 'ac': "
                "false y 5 'tips' con 'tip' (máx. 40 caracteres) e 'idea' (imagen SIN texto que lo ilustre).",
        "antes_despues": "Escenas para «render sin y con postproducción»: solo 'descripcion' (qué se ve: edificio o "
                         "estancia, máx. 80 caracteres).",
        "proceso": "Edificios típicos de TFM para «del boceto al render»: solo 'descripcion' (máx. 90 caracteres).",
        "obra": "Edificios para «así se construye, de la zanja a la llave»: solo 'descripcion' (máx. 90 caracteres).",
    }[sec]
    r = gemini.ask(f"""Crea {n} piezas NUEVAS para el banco de reels de una cuenta para estudiantes de arquitectura.
{reglas}
No repitas ninguna de estas: {json.dumps(ya, ensure_ascii=False)[:3000]}
Formato exacto de cada pieza (sin 'id'), como estos ejemplos: {_ejemplos(B, sec)}
Devuelve JSON: {{"piezas": [...]}}""", 0.8)
    return r.get("piezas") or []


def verificar(sec, p):
    """Test y V/F: otro modelo resuelve la pregunta a ciegas. True si coincide y está seguro."""
    import gemini, random
    ops = list(p["opciones"]); correcta = ops[0]
    random.shuffle(ops)
    r = gemini.ask(f"""Eres profesor de una escuela de arquitectura en España. Resuelve esta pregunta con rigor.
Pregunta: {p['pregunta']}
Opciones: {json.dumps(ops, ensure_ascii=False)}
Si hay más de una opción defendible, o la pregunta es ambigua o depende de la normativa de un país, dilo.
Devuelve JSON: {{"respuesta": "<texto exacto de la opción>", "seguro": bool, "ambigua": bool, "motivo": str}}""",
                   0.1, careful=True)
    ok = r.get("respuesta") == correcta and r.get("seguro") and not r.get("ambigua")
    if not ok:
        print(f"  descartada: «{p['pregunta'][:70]}» -> {r.get('respuesta')} ({str(r.get('motivo'))[:120]})")
    return bool(ok)


def valida(sec, p):
    txt = json.dumps(p, ensure_ascii=False)
    if not marca.limpio(txt):
        return False
    try:
        if sec in ("test", "vf"):
            return (isinstance(p["opciones"], list) and len(p["opciones"]) == (4 if sec == "test" else 2)
                    and len(p["pregunta"]) <= 130 and p.get("explicacion") and p.get("idea"))
        if sec == "encuesta":
            return len(p["opciones"]) == 4 and p.get("idea") and len(p["pregunta"]) <= 110
        if sec == "galeria":
            return p.get("hook") and len(p["escenas"]) >= 6 and all(e.get("idea") and e.get("label") for e in p["escenas"])
        if sec == "tips":
            p["ac"] = False
            return p.get("hook") and len(p["tips"]) >= 4 and all(t.get("tip") and t.get("idea") for t in p["tips"])
        return bool(p.get("descripcion"))
    except Exception:
        return False


def ampliar(sec, n):
    B = json.load(open(BANCO))
    nuevas = []
    for p in proponer(B, sec, n):
        if not valida(sec, p) or (sec in ("test", "vf") and not verificar(sec, p)):
            continue
        clave = p.get("pregunta") or p.get("hook") or p.get("descripcion")
        p["id"] = _id(sec, clave)
        if any(x["id"] == p["id"] for x in B[sec] + nuevas):
            continue
        nuevas.append(p)
    B = json.load(open(BANCO))                         # relee por si otro proceso lo ha cambiado
    B[sec] += nuevas
    json.dump(B, open(BANCO, "w"), ensure_ascii=False, indent=1)
    print(f"{sec}: {len(nuevas)} piezas nuevas")
    return len(nuevas)


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("sin GEMINI_API_KEY: no se amplía"); return
    if len(sys.argv) > 1:
        ampliar(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else LOTE[sys.argv[1]]); return
    B = json.load(open(BANCO))
    for sec, minimo in MIN_LIBRES.items():
        if libres(B, sec) < minimo:
            try:
                ampliar(sec, LOTE[sec])
            except Exception as e:
                print(f"{sec}: no se ha podido ampliar ({str(e)[:150]})")


if __name__ == "__main__":
    main()

"""Amplía fuentes/banco.json cuando una sección se queda con pocas piezas sin usar.

    python ampliar_banco.py              # amplía lo que haga falta
    python ampliar_banco.py referentes 3 # fuerza 3 piezas nuevas de una sección

Control de calidad: un modelo propone y OTRO (modo cuidadoso, temperatura baja) verifica cada pieza:
  · test / vf: la resuelve a ciegas; solo entra si coincide, está seguro y no es ambigua.
  · referentes: comprueba obra, autor, ciudad, año y que el dato sea cierto; si algo falla, se tira el punto.
  · tips e IA: comprueba que no haya nada falso ni dudoso.
Además: forma correcta y ninguna frase prohibida para AC (marca.limpio). Documentación y auditoría no se amplían solas
(son de venta: las escribes tú).
"""
import hashlib, json, os, random, sys

import marca

HERE = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(HERE, "fuentes", "banco.json")
MIN_LIBRES = {"tips_tfm": 3, "tips_proyectos": 3, "ia": 2, "referentes": 2, "test": 3, "vf": 2, "encuesta": 1}
LOTE = {"tips_tfm": 4, "tips_proyectos": 4, "ia": 3, "referentes": 3, "test": 6, "vf": 4, "encuesta": 3}
TEMAS = ("construcción, estructuras, instalaciones, dibujo arquitectónico, BIM y Revit, urbanismo, materiales, "
         "acondicionamiento y eficiencia energética, historia de la arquitectura")
REGLAS = {
    "tips_tfm": "Reels de tips para aprobar el TFM de arquitectura. 'hook' (máx. 60 caracteres) y 5 'puntos' con 'titulo' "
                "(máx. 5 palabras), 'dato' (1 frase útil y cierta, máx. 22 palabras) e 'idea' (imagen SIN texto).",
    "tips_proyectos": "Reels de tips para la asignatura de Proyectos Arquitectónicos. Misma forma: 'hook' y 5 'puntos' con "
                      "'titulo', 'dato' e 'idea'.",
    "ia": "Reels sobre cómo usar la IA de forma honesta y útil en proyectos de arquitectura (iterar, imágenes, textos, "
          "preparar la defensa), sin prometer aprobar y recordando revisar las normas de la escuela. Misma forma.",
    "referentes": "Reels de 5 referentes de arquitectura MUY conocidos y documentados para estudiantes. 'hook' y 5 'puntos' "
                  "con 'titulo' (la estrategia, máx. 5 palabras), 'ref' («Obra · Autor (Ciudad, año)»), 'dato' (qué "
                  "aprender, cierto y verificable) e 'idea' (imagen CONCEPTUAL de un edificio ORIGINAL con esa estrategia, "
                  "nunca la obra real).",
    "test": f"Preguntas de test de 4 opciones para estudiantes de arquitectura en España ({TEMAS}). La CORRECTA va "
            "SIEMPRE primera en 'opciones'. Una sola respuesta correcta sin discusión; pregunta máx. 110 caracteres, "
            "opciones máx. 45; 'explicacion' de 1-2 frases; 'idea' para la imagen de fondo SIN texto.",
    "vf": f"Afirmaciones de verdadero o falso para estudiantes de arquitectura ({TEMAS}). 'opciones' = [\"Verdadero\", "
          "\"Falso\"] con la CORRECTA primero. Sin ambigüedad, máx. 110 caracteres. 'explicacion' e 'idea'.",
    "encuesta": "Encuestas sin respuesta correcta para estudiantes que preparan el TFM o Proyectos. 4 opciones cortas "
                "(máx. 30 caracteres) e 'idea' para la imagen de fondo.",
}


def libres(B, sec):
    try:
        us = {x["id"] for x in json.load(open(os.path.join(HERE, "used.json")))}
    except Exception:
        us = set()
    return sum(1 for p in B[sec] if f"{sec}:{p['id']}" not in us)


def tendencias_txt():
    try:
        t = json.load(open(os.path.join(HERE, "tendencias.json")))
        return json.dumps((t.get("temas_calientes") or []) + (t.get("ideas_de_reel") or []), ensure_ascii=False)[:1200]
    except Exception:
        return "(ninguno)"


def proponer(B, sec, n):
    import gemini
    ya = [p.get("pregunta") or p.get("hook") for p in B[sec]]
    r = gemini.ask(f"""Crea {n} piezas NUEVAS para el banco de reels de una cuenta para estudiantes de arquitectura.
{REGLAS[sec]}
Español de España. Aprovecha, si encajan, estos temas calientes de esta semana: {tendencias_txt()}
No repitas: {json.dumps(ya, ensure_ascii=False)[:3000]}
Forma exacta (sin 'id'), como estos ejemplos: {json.dumps(B[sec][:2], ensure_ascii=False)[:2500]}
Devuelve JSON: {{"piezas": [...]}}""", 0.85)
    return r.get("piezas") or []


def _cuidadoso(prompt):
    import gemini
    return gemini.ask(prompt, 0.1, careful=True)


def verificar(sec, p):
    if sec in ("test", "vf"):
        ops = list(p["opciones"]); buena = ops[0]; random.shuffle(ops)
        r = _cuidadoso(f"""Eres profesor de una escuela de arquitectura en España. Resuelve con rigor.
Pregunta: {p['pregunta']}
Opciones: {json.dumps(ops, ensure_ascii=False)}
Devuelve JSON: {{"respuesta": "<texto exacto de la opción>", "seguro": bool, "ambigua": bool}}""")
        return r.get("respuesta") == buena and r.get("seguro") and not r.get("ambigua")
    if sec == "encuesta":
        return True
    r = _cuidadoso(f"""Eres arquitecto, historiador de la arquitectura y profesor, muy estricto. Revisa cada punto de esta
pieza para un reel. Marca como malo cualquier punto con algo falso, dudoso o inventado
{'(obra, autor, ciudad, año o dato que no sean exactos)' if sec == 'referentes' else ''}, o que prometa resultados.
Pieza: {json.dumps(p, ensure_ascii=False)}
Devuelve JSON: {{"malos": [int], "motivos": [str]}}  (índices desde 0)""")
    malos = {int(i) for i in r.get("malos") or [] if str(i).lstrip("-").isdigit()}
    if malos:
        print(f"  {sec}: quito {len(malos)} puntos: {'; '.join(r.get('motivos') or [])[:200]}")
    p["puntos"] = [x for i, x in enumerate(p["puntos"]) if i not in malos]
    return len(p["puntos"]) >= 4


def valida(sec, p):
    if not marca.limpio(json.dumps(p, ensure_ascii=False)):
        return False
    try:
        if sec in ("test", "vf"):
            return len(p["opciones"]) == (4 if sec == "test" else 2) and len(p["pregunta"]) <= 130 \
                and p.get("explicacion") and p.get("idea")
        if sec == "encuesta":
            return len(p["opciones"]) == 4 and p.get("idea")
        claves = ("titulo", "dato", "idea") + (("ref",) if sec == "referentes" else ())
        return p.get("hook") and len(p["puntos"]) >= 4 and all(all(x.get(k) for k in claves) for x in p["puntos"])
    except Exception:
        return False


def ampliar(sec, n):
    B = json.load(open(BANCO)); nuevas = []
    for p in proponer(B, sec, n):
        try:
            if not valida(sec, p) or not verificar(sec, p):
                continue
        except Exception as e:
            print(f"  {sec}: verificación fallida ({str(e)[:100]})"); continue
        p["puntos"] = p.get("puntos", [])[:5] if "puntos" in p else p.get("puntos")
        if p.get("puntos") is None:
            p.pop("puntos", None)
        clave = p.get("pregunta") or p.get("hook")
        p["id"] = f"{sec[:4]}_{hashlib.sha1(clave.encode()).hexdigest()[:8]}"
        if any(x["id"] == p["id"] for x in B[sec] + nuevas):
            continue
        nuevas.append(p)
    B = json.load(open(BANCO)); B[sec] += nuevas
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

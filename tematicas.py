"""Calendario semanal de AC: 2 reels al día, 14 a la semana. 80 % útil (11) y 20 % venta (3).

           14:00             20:30
    lun    tips_tfm          referentes
    mar    ia                test
    mié    tips_proyectos    documentacion   (venta)
    jue    tips_tfm          vf
    vie    referentes        auditoria       (venta)
    sáb    ia                tips_proyectos
    dom    tips_tfm          documentacion   (venta)

El estratega (agentes.py) aprende de los resultados reales: cuando hay datos suficientes, los huecos ÚTILES pueden
cambiar a la temática útil que mejor funciona (sin repetir la anterior). Los de venta no se tocan (siempre el 20 %).
"""
import datetime, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS = {"mediodia": 0, "noche": 1}
PLAN = [["tips_tfm", "referentes"], ["ia", "test"], ["tips_proyectos", "documentacion"], ["tips_tfm", "vf"],
        ["referentes", "auditoria"], ["ia", "tips_proyectos"], ["tips_tfm", "documentacion"]]
UTIL = ["tips_tfm", "tips_proyectos", "referentes", "ia", "test", "vf"]
VENTA = ["documentacion", "auditoria"]
TEMAS = UTIL + VENTA + ["encuesta", "postpro"]


def plan(fecha, slot):
    return PLAN[fecha.weekday()][SLOTS.get(slot, 0)]


def _ultimo(t, rec):
    return max([i for i, r in enumerate(rec) if r == t], default=-1)


def _pesos():
    try:
        pb = json.load(open(os.path.join(HERE, "playbook.json")))
        n = sum(1 for _ in open(os.path.join(HERE, "performance.json")) if _.strip()) if os.path.exists(
            os.path.join(HERE, "performance.json")) else 0
        datos = len(json.load(open(os.path.join(HERE, "performance.json")))) if n else 0
        return pb.get("pesos") or {}, datos
    except Exception:
        return {}, 0


def tema_de(fecha, slot, recientes=()):
    rec = [r for r in recientes if r]
    if slot not in SLOTS:                                    # lanzamiento manual: la que lleva más sin salir
        return min([t for t in UTIL + VENTA if not rec or t != rec[-1]], key=lambda t: (_ultimo(t, rec), TEMAS.index(t)))
    p = plan(fecha, slot)
    if p in VENTA:
        return p
    pesos, datos = _pesos()
    if datos >= 12 and pesos:                                # con datos: la útil que mejor funciona, con algo de variedad
        rng = random.Random(f"{fecha}{slot}")
        cand = [t for t in UTIL if not rec or t != rec[-1]]
        w = [max(0.2, float(pesos.get(t, 1))) * (1.6 if t == p else 1.0) for t in cand]
        return rng.choices(cand, weights=w)[0]
    return p if not rec or p != rec[-1] else next(t for t in UTIL if t != rec[-1])


def reserva(tema, recientes=(), n=2):
    """Si un reel no sale: otros del mismo grupo (venta con venta, útil con útil), los menos recientes."""
    rec = [r for r in recientes if r]
    grupo = VENTA + ["tips_tfm"] if tema in VENTA else UTIL
    return sorted([t for t in grupo if t != tema], key=lambda t: _ultimo(t, rec))[:n]


def semana(lunes=None):
    lunes = lunes or datetime.date.today()
    return [[plan(lunes + datetime.timedelta(d), s) for s in SLOTS] for d in range(7)]

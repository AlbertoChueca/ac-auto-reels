"""Calendario semanal de AC: 2 reels al día (14 a la semana), mezcla de interacción, inspiración y AC.

    mediodía (14:00)          noche (20:30)
    lun  test                 galeria
    mar  tips                 vf
    mié  antes_despues        test
    jue  encuesta             tips_ac
    vie  test                 proceso_visual
    sáb  galeria              vf
    dom  obra                 tips_ac

Interacción (tests, V/F, encuesta): 6 · inspiración y aprendizaje: 6 · AC (tips con cierre de AC): 2. Además, TODAS las
descripciones acaban con una línea discreta de la auditoría gratuita del TFM.
"""
import datetime

SLOTS = {"mediodia": 0, "noche": 1}
PLAN = [["test", "galeria"], ["tips", "vf"], ["antes_despues", "test"], ["encuesta", "tips_ac"],
        ["test", "proceso_visual"], ["galeria", "vf"], ["obra", "tips_ac"]]
QUIZ = ["test", "vf", "encuesta"]
VISUAL = ["galeria", "tips", "antes_despues", "proceso_visual", "obra"]
TEMAS = QUIZ + VISUAL + ["tips_ac"]


def plan(fecha, slot):
    return PLAN[fecha.weekday()][SLOTS.get(slot, 0)]


def _ultimo(t, rec):
    return max([i for i, r in enumerate(rec) if r == t], default=-1)


def tema_de(fecha, slot, recientes=()):
    """La del calendario; si es un lanzamiento manual, la que lleva más tiempo sin salir (sin repetir la última)."""
    rec = [r for r in recientes if r]
    if slot in SLOTS:
        return plan(fecha, slot)
    opciones = [t for t in TEMAS if not rec or t != rec[-1]]
    return min(opciones, key=lambda t: (_ultimo(t, rec), TEMAS.index(t)))


def reserva(tema, recientes=(), n=2):
    """Si un reel no sale (imágenes rechazadas, nota < 8): otros del mismo grupo, los menos recientes."""
    rec = [r for r in recientes if r]
    grupo = QUIZ if tema in QUIZ else ["galeria", "tips", "antes_despues"]
    return sorted([t for t in grupo if t != tema], key=lambda t: _ultimo(t, rec))[:n]


def semana(lunes=None):
    lunes = lunes or datetime.date.today()
    return [[plan(lunes + datetime.timedelta(d), s) for s in SLOTS] for d in range(7)]

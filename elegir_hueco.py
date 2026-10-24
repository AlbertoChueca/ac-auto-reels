"""¿Qué toca publicar ahora? Lo usa el workflow programado, que GitHub lanza cada hora y a veces con horas de retraso.

    python elegir_hueco.py   -> mediodia | noche | skip

Un hueco toca si aún no se ha publicado hoy y la hora de España está entre 75 min antes de su hora (da tiempo a generar
el reel y esperar a la hora exacta) y el inicio del siguiente hueco: si GitHub se retrasa, el reel sale tarde, pero sale.
"""
import datetime, json, os
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
HUECOS = [("mediodia", 14, 0), ("noche", 20, 30)]
HASTA = {"mediodia": (19, 15), "noche": (23, 45)}
HORA = {s: (h, m) for s, h, m in HUECOS}


def publicado(slot, hoy):
    try:
        for line in open(os.path.join(HERE, "log.jsonl")):
            e = json.loads(line)
            if e.get("date") == hoy and e.get("slot") == slot and any(
                    not str(v).startswith("error") for v in (e.get("publicado") or {}).values()):
                return True
    except Exception:
        pass
    return False


def elegir(now=None):
    now = now or datetime.datetime.now(ZoneInfo("Europe/Madrid"))
    hoy = str(now.date())
    for slot, h, m in HUECOS:
        t = now.replace(hour=h, minute=m, second=0, microsecond=0)
        hh, mm = HASTA[slot]
        fin = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if t - datetime.timedelta(minutes=75) <= now <= fin and not publicado(slot, hoy):
            return slot
    return "skip"


if __name__ == "__main__":
    print(elegir())

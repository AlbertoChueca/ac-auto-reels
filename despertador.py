"""Despertador de AC: lanza cada reel a su hora sin depender de los programados de GitHub, que llegan con horas de
retraso o no llegan (en noviembre se perdieron 6 de 22 huecos y casi todos salieron tarde).

Cómo funciona: este trabajo espera dentro de GitHub (un runner puede esperar hasta 6 h) hasta 55 min antes del siguiente
hueco sin publicar (14:00 y 21:00, hora de España) y entonces lanza «Reels diarios» con ese hueco: el reel se genera,
espera a la hora exacta y publica. Cuando termina, vuelve a lanzar el despertador para el siguiente. Si el siguiente
hueco está a más de 5 h 30 min, espera ese rato y se relanza a sí mismo. Los lanzamientos manuales (workflow_dispatch)
sí son puntuales en GitHub, a diferencia de los programados. El programado de cada hora sigue como red de seguridad.

    python despertador.py           # espera y lanza (en GitHub)
    python despertador.py --plan    # solo dice qué haría
"""
import datetime, subprocess, sys, time
from zoneinfo import ZoneInfo

import elegir_hueco as E

TZ = ZoneInfo("Europe/Madrid")
ANTES = datetime.timedelta(minutes=55)          # el reel tarda 10-45 min en generarse y luego espera a la hora exacta
MAX_ESPERA = datetime.timedelta(hours=5, minutes=30)


def proximo(now):
    """(hueco, hora) del siguiente hueco aún sin publicar."""
    for d in range(3):
        dia = (now + datetime.timedelta(days=d)).date()
        for slot, h, m in E.HUECOS:
            t = datetime.datetime(dia.year, dia.month, dia.day, h, m, tzinfo=TZ)
            hh, mm = E.HASTA[slot]
            if now <= t.replace(hour=hh, minute=mm) and not E.publicado(slot, str(dia)):
                return slot, t
    return None


def lanzar(wf, inputs):
    args = ["gh", "workflow", "run", wf, "--ref", "main"] + sum((["-f", f"{k}={v}"] for k, v in inputs.items()), [])
    r = subprocess.run(args, capture_output=True, text=True)
    print("lanzado:", wf, inputs, r.returncode, r.stderr.strip()[:200], flush=True)
    return r.returncode == 0


def main():
    now = datetime.datetime.now(TZ)
    p = proximo(now)
    if not p:
        print("nada pendiente"); return
    slot, t = p
    cuando = t - ANTES
    print(f"siguiente: {slot} a las {t:%d/%m %H:%M} (lanzo a las {cuando:%H:%M})", flush=True)
    if "--plan" in sys.argv:
        return
    espera = (cuando - now).total_seconds()
    if espera > MAX_ESPERA.total_seconds():
        time.sleep(MAX_ESPERA.total_seconds())
        lanzar("despertador.yml", {}); return             # sigue esperando en un trabajo nuevo
    if espera > 0:
        time.sleep(espera)
    subprocess.run(["git", "pull", "-q", "--rebase"], capture_output=True)      # ¿lo ha publicado otro mientras esperaba?
    if E.publicado(slot, str(t.date())):
        print("ya publicado; paso al siguiente"); lanzar("despertador.yml", {}); return
    lanzar("reels.yml", {"hueco": slot, "dry_run": "false"})


if __name__ == "__main__":
    main()

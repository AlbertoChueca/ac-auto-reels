"""Un hueco de publicación de AC · ArquitecturaConfidencial.

    python run_daily.py <mediodia|noche|manual> [--dry-run]

1. elige la temática del calendario (tematicas.py) o la pedida a mano (TEMATICA);
2. visual.py genera las imágenes, monta el reel, lo revisa (mínimo 8) y escribe la descripción;
   si no sale, prueba hasta 2 temáticas de reserva del mismo grupo;
3. espera a la hora exacta y publica en Instagram, TikTok y YouTube Shorts;
4. lo apunta en log.jsonl (de ahí lee el bot de comunidad para contestar y publicar soluciones).
Si nada llega al 8, ese hueco no se publica (mejor nada que algo mal hecho).
"""
import datetime, json, os, sys, time, traceback
from zoneinfo import ZoneInfo

import tematicas
import visual

slot = sys.argv[1] if len(sys.argv) > 1 else "manual"
dry = "--dry-run" in sys.argv or os.environ.get("DRY_RUN") == "true"
now = datetime.datetime.now(ZoneInfo("Europe/Madrid"))
today = now.date()
os.makedirs("out", exist_ok=True)
T0 = time.time()


def log(entry):
    with open("log.jsonl", "a") as f:
        f.write(json.dumps({"date": str(today), "slot": slot, **entry}, ensure_ascii=False) + "\n")


def recientes(n=10):
    out = []
    try:
        for line in open("log.jsonl"):
            t = json.loads(line).get("tematica")
            if t:
                out.append(t)
    except Exception:
        pass
    return out[-n:]


def ya_publicado():
    import elegir_hueco
    return elegir_hueco.publicado(slot, str(today))


def esperar_hueco():
    """Si el reel está listo antes de la hora, espera (máx. PUBLISH_MAX_WAIT_MIN)."""
    import elegir_hueco
    objetivo = elegir_hueco.HORA.get(slot)
    if os.environ.get("PUBLISH_AT_MANUAL"):                      # lanzado a mano con hora: "20:30"
        try:
            objetivo = tuple(int(x) for x in os.environ["PUBLISH_AT_MANUAL"].split(":")[:2])
        except Exception:
            pass
    if not objetivo:
        return
    ahora = datetime.datetime.now(ZoneInfo("Europe/Madrid"))
    meta_t = ahora.replace(hour=objetivo[0], minute=objetivo[1], second=0, microsecond=0)
    secs = (meta_t - ahora).total_seconds()
    if 0 < secs <= float(os.environ.get("PUBLISH_MAX_WAIT_MIN") or "90") * 60:
        print(f"esperando {secs / 60:.1f} min para publicar a las {objetivo[0]}:{objetivo[1]:02d}", flush=True)
        time.sleep(secs)


def resumen(txt):
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(txt + "\n")


if slot in tematicas.SLOTS and not dry and ya_publicado() and os.environ.get("FORCE") != "true":
    raise SystemExit(f"El hueco {slot} de hoy ya está publicado; no se repite")
if not os.environ.get("GEMINI_API_KEY"):
    resumen("## ❌ Falta el secreto GEMINI_API_KEY (imágenes y revisión)")
    raise SystemExit("Falta GEMINI_API_KEY")

pedida = (os.environ.get("TEMATICA") or "").strip()
rec = recientes()
tema = pedida if pedida in tematicas.TEMAS else tematicas.tema_de(today, slot, rec)
cadena = [tema] + tematicas.reserva(tema.replace("tips_ac", "tips"), rec)
print("temática:", tema, "· reserva:", cadena[1:], flush=True)

out = f"out/{today}_{slot}_{now.hour:02d}.mp4"
meta, errores = None, []
for t in cadena:
    if meta is None and errores and time.time() - T0 > 55 * 60:
        print("tiempo agotado: no pruebo más temáticas", flush=True)
        break
    try:
        formato = "tips" if t == "tips_ac" else t
        solo_ac = True if t == "tips_ac" else (False if t == "tips" else None)
        meta = visual.hacer(formato, out, seed=f"{today}-{slot}-{t}", solo_ac=solo_ac)
        meta["tematica"] = t
        break
    except Exception as e:
        errores.append(f"{t}: {str(e)[:300]}")
        print(f"[{t}] no ha salido:\n{traceback.format_exc()[-1500:]}", flush=True)
        with open("errores_reels.log", "a") as f:
            f.write(f"{now:%Y-%m-%d %H:%M} {slot} [{t}] {str(e)[:500]}\n")

if meta is None:
    resumen("## ❌ Hoy no sale reel en este hueco\n" + "".join(f"- `{e}`\n" for e in errores))
    raise SystemExit("Ninguna temática llegó al 8")
caption = open(out.replace(".mp4", ".txt")).read()
resumen(f"## ✅ Reel listo: {meta['tematica']} · nota {meta['review_score']}\n\n- Gancho: **{meta['hook']}**\n"
        f"- Duración: {meta['duration']} s\n" + "".join(f"- Antes falló: `{e}`\n" for e in errores))
print(caption)
if dry:
    print("PRUEBA: no se publica")
    sys.exit(0)

import publish_all
esperar_hueco()
res = publish_all.publish(out, caption, meta)
print("publicado:", json.dumps(res, ensure_ascii=False), flush=True)
resumen("\n### Publicación\n" + "".join(f"- {'✅' if not str(v).startswith('error') else '❌'} {k}: {v}\n"
                                         for k, v in res.items()))
ok = any(not str(v).startswith("error") for v in res.values())
if ok:                                             # piezas usadas: no se repiten hasta agotar el banco
    usados = []
    try:
        usados = json.load(open("used.json"))
    except Exception:
        pass
    usados += [{"id": i, "fecha": str(today)} for i in meta["ids"]]
    json.dump(usados, open("used.json", "w"), ensure_ascii=False, indent=0)
log({"tematica": meta["tematica"], "formato": meta["formato"], "hook": meta["hook"], "ids": meta["ids"],
     "duration": meta["duration"], "review_score": meta["review_score"], "ac": meta["ac"], "solucion": meta["solucion"],
     "publicado": res, "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
if not ok:
    raise SystemExit("No se pudo publicar en ninguna red")

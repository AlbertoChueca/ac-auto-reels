"""Resultados reales de cada reel -> performance.json (lo usa el estratega). Instagram por la API de Meta; TikTok y
YouTube por Zernio. Se actualiza desde las 12 h hasta los 60 días de vida de cada publicación.
"""
import datetime, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PERF = os.path.join(HERE, "performance.json")
MAP = {"views": "views", "impressions": "views", "plays": "views", "reach": "reach", "likes": "likes",
       "comments": "comments", "shares": "shares", "saves": "saved", "saved": "saved", "follows": "follows",
       "ig_reels_avg_watch_time": "watch_ms", "avgWatchTime": "watch_ms", "averageWatchTime": "watch_ms",
       "profile_visits": "profile_visits", "profileViews": "profile_visits", "clicks": "clicks", "website_clicks": "clicks"}


def actualizar(dias=60):
    if not os.environ.get("ZERNIO_API_KEY") and not os.environ.get("IG_TOKEN"):
        return "métricas: sin claves"
    perf = json.load(open(PERF)) if os.path.exists(PERF) else {}
    hoy = datetime.date.today(); n = 0
    try:
        filas = [json.loads(l) for l in open(os.path.join(HERE, "log.jsonl")) if l.strip()]
    except Exception:
        filas = []
    for e in filas:
        try:
            edad = (hoy - datetime.date.fromisoformat(e["date"])).days
        except Exception:
            continue
        if edad < 1 or edad > dias:
            continue
        tot, por = {}, {}
        for dest, pid in (e.get("publicado") or {}).items():
            pid = str(pid)
            if pid.startswith("error") or pid in ("ok", "None"):
                continue
            try:
                if pid.startswith("ig:"):
                    import publish_ig as IG
                    m = IG.media_insights(pid[3:])
                else:
                    import publish_zernio as Z
                    a = Z.analytics(pid) or {}
                    if os.environ.get("METRICAS_DEBUG"):
                        print("zernio", dest, json.dumps(a)[:600], flush=True)
                    if isinstance(a.get("data"), dict):                   # a veces viene envuelto en data
                        a = a["data"]
                    m = dict(a.get("analytics") or a.get("metrics") or {})
                    for pa in a.get("platformAnalytics") or []:          # métricas por red (Zernio)
                        for k, v in (pa.get("analytics") or {}).items():
                            m.setdefault(k, v)
            except Exception as err:
                print("métricas:", dest, str(err)[:120], flush=True); continue
            m = {MAP[k]: v for k, v in m.items() if k in MAP and isinstance(v, (int, float))}
            por[dest] = m
            for k, v in m.items():
                if k == "watch_ms":
                    tot[k] = max(tot.get(k, 0), v)
                else:
                    tot[k] = tot.get(k, 0) + v
        if por:
            ig = next((str(v)[3:] for v in (e.get("publicado") or {}).values() if str(v).startswith("ig:")), None)
            clave = f"{e['date']}_{e.get('slot')}" + (f"_{ig[-6:]}" if ig and e.get("slot") == "manual" else "")
            perf[clave] = {"date": e["date"], "tematica": e.get("tematica"), "hook": e.get("hook"), "duration": e.get("duration"),
                                                     "review_score": e.get("review_score"), **tot, "por_red": por}
            n += 1
    json.dump(perf, open(PERF, "w"), ensure_ascii=False, indent=0)
    return f"métricas: {n} reels con datos"


def informe():
    """Tabla legible (metricas.md): por reel y por red, con las tasas que importan (guardados, compartidos, comentarios
    por cada 100 vistas) y el tiempo medio de visionado frente a la duración."""
    try:
        perf = json.load(open(PERF))
    except Exception:
        return "sin datos"
    dur = {}
    try:
        for l in open(os.path.join(HERE, "log.jsonl")):
            e = json.loads(l); dur[f"{e['date']}_{e.get('slot')}"] = e.get("duration")
    except Exception:
        pass
    filas = ["| fecha | temática | gancho | red | vistas | alcance | likes | coment. | compart. | guard. | retención | interacción/100 vistas |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in sorted(perf.items()):
        for red, m in (r.get("por_red") or {}).items():
            v = m.get("views") or m.get("reach") or 0
            inter = (m.get("saved", 0) + m.get("shares", 0) + m.get("comments", 0))
            d_ = dur.get(r.get("hook")); ret = f"{m['watch_ms'] / 1000:.1f} s / {d_} s" if m.get("watch_ms") and d_ else "—"
            filas.append(f"| {r['date']} | {r.get('tematica')} | {(r.get('hook') or '')[:38]} | {red.split('_')[0]} | {m.get('views', '—')} | "
                         f"{m.get('reach', '—')} | {m.get('likes', 0)} | {m.get('comments', 0)} | {m.get('shares', 0)} | {m.get('saved', 0)} | "
                         f"{ret} | {(100 * inter / v):.1f} |" if v else
                         f"| {r['date']} | {r.get('tematica')} | {(r.get('hook') or '')[:38]} | {red.split('_')[0]} | sin datos | | | | | | | |")
    txt = f"# Métricas reales ({datetime.date.today()})\n\n" + "\n".join(filas) + "\n"
    open(os.path.join(HERE, "metricas.md"), "w").write(txt)
    return txt


if __name__ == "__main__":
    print(actualizar())
    print(informe())

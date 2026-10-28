"""Resultados reales de cada reel -> performance.json (lo usa el estratega). Instagram por la API de Meta; TikTok y
YouTube por Zernio. Se actualiza desde las 12 h hasta los 60 días de vida de cada publicación.
"""
import datetime, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PERF = os.path.join(HERE, "performance.json")
MAP = {"views": "views", "impressions": "views", "plays": "views", "reach": "reach", "likes": "likes",
       "comments": "comments", "shares": "shares", "saves": "saved", "saved": "saved", "follows": "follows"}


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
                    m = dict(a.get("analytics") or {})
            except Exception as err:
                print("métricas:", dest, str(err)[:120], flush=True); continue
            m = {MAP[k]: v for k, v in m.items() if k in MAP and isinstance(v, (int, float))}
            por[dest] = m
            for k, v in m.items():
                tot[k] = tot.get(k, 0) + v
        if por:
            perf[f"{e['date']}_{e.get('slot')}"] = {"date": e["date"], "tematica": e.get("tematica"), "hook": e.get("hook"),
                                                     "review_score": e.get("review_score"), **tot, "por_red": por}
            n += 1
    json.dump(perf, open(PERF, "w"), ensure_ascii=False, indent=0)
    return f"métricas: {n} reels con datos"


if __name__ == "__main__":
    print(actualizar())

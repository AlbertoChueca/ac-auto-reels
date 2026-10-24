"""Comprueba que todo está conectado: Gemini, Instagram (Meta), TikTok y YouTube (Zernio) y el banco de contenido.

    python comprobar.py      -> estado.md (y el resumen del workflow)
"""
import datetime, json, os

filas = []


def fila(ok, que, detalle):
    filas.append(f"| {'✅' if ok else '❌'} {que} | {detalle} |")


try:
    import gemini
    m = gemini.available()
    fila(bool(m), "Gemini texto", f"{len(m)} modelos disponibles")
    im = [x for x in m if "image" in x]
    fila(bool(im), "Gemini imagen", ", ".join(im[:3]) or "sin modelos de imagen: revisa la clave")
except Exception as e:
    fila(False, "Gemini", f"falta o falla GEMINI_API_KEY: {str(e)[:120]}")

if os.environ.get("IG_TOKEN"):
    try:
        import publish_ig
        w = publish_ig.whoami(os.environ["IG_TOKEN"])
        fila(True, "Instagram (API de Meta)", f"@{w['username']} · publica directo")
    except Exception as e:
        fila(False, "Instagram (API de Meta)", str(e)[:200])
else:
    fila(False, "Instagram (API de Meta)", "falta el secreto IG_TOKEN (si no, se intenta por Zernio)")

if os.environ.get("ZERNIO_API_KEY"):
    try:
        import publish_zernio as Z
        acc, seen = Z.accounts(verbose=True)
        for p, nombre in (("tiktok", "TikTok"), ("youtube", "YouTube"), ("instagram", "Instagram en Zernio")):
            if p == "instagram" and os.environ.get("IG_TOKEN"):
                continue
            fila(bool(acc.get(p)), f"{nombre} (Zernio)", "conectada" if acc.get(p) else
                 f"no hay cuenta de AC; conectadas en Zernio: {seen.get(p) or 'ninguna'}")
    except Exception as e:
        fila(False, "Zernio", str(e)[:200])
else:
    fila(False, "Zernio", "falta el secreto ZERNIO_API_KEY (TikTok y YouTube)")

try:
    B = json.load(open("fuentes/visual.json"))
    usados = {x["id"] for x in json.load(open("used.json"))}
    libres = {k: sum(1 for p in v if f"visual:{p['id']}" not in usados) for k, v in B.items() if isinstance(v, list)}
    fila(all(libres.values()), "Banco de contenido", " · ".join(f"{k} {n}" for k, n in libres.items()) + " sin usar")
except Exception as e:
    fila(False, "Banco de contenido", str(e)[:150])

txt = (f"# Estado ({datetime.date.today()})\n\n| comprobación | detalle |\n|---|---|\n" + "\n".join(filas) + "\n")
open("estado.md", "w").write(txt)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(txt)
print(txt)

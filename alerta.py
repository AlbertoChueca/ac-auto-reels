"""Avisos automáticos: si una red (Instagram, TikTok o YouTube) lleva 2 o más publicaciones seguidas fallando, abre una
incidencia en GitHub asignada al dueño del repositorio (GitHub la manda por correo y al móvil) con el error y cómo
arreglarlo. Cuando la red vuelve a publicar, la cierra sola. Así un token caducado no pasa días sin que nadie lo vea.

    python alerta.py            # en GitHub (usa gh con GH_TOKEN); lo lanzan los workflows al terminar
    python alerta.py --plan     # solo dice qué haría
Opcional: variable SLACK_WEBHOOK_URL para recibir el aviso también en Slack.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REDES = {"instagram": "Instagram", "tiktok": "TikTok", "youtube": "YouTube"}
ARREGLO = {
    "instagram": "Casi siempre es el token de Meta (caduca o se invalida al cambiar la contraseña). Dos salidas:\n"
                 "1. **Conectar Instagram en Zernio** (recomendado: renueva el token solo). El sistema publica por ahí en cuanto lo detecta.\n"
                 "2. Generar un token nuevo en Meta y guardarlo en el secreto `IG_TOKEN` (Settings → Secrets and variables → Actions).",
    "tiktok": "Entra en Zernio y comprueba que la cuenta de TikTok sigue conectada (a veces pide volver a autorizar).",
    "youtube": "Entra en Zernio y comprueba que el canal de YouTube sigue conectado (a veces pide volver a autorizar).",
}


def estado():
    """{red: (fallos seguidos al final, último error)} mirando las últimas publicaciones del registro."""
    filas = []
    try:
        filas = [json.loads(l) for l in open(os.path.join(HERE, "log.jsonl"))][-12:]
    except Exception:
        pass
    out = {}
    for red in REDES:
        n, err = 0, ""
        for e in reversed(filas):
            v = [str(x) for k, x in (e.get("publicado") or {}).items() if k.startswith(red) and "story" not in k and "borrador" not in k]
            if not v:
                continue                                    # ese reel no iba a esta red
            if all(x.startswith("error") for x in v):
                n += 1; err = err or v[0][:400]
            else:
                break
        out[red] = (n, err)
    return out


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    plan = "--plan" in sys.argv
    E = estado()
    if plan:
        print(E); return
    gh("label", "create", "alerta-redes", "--color", "B60205", "--description", "Una red ha dejado de publicar", "--force")
    _, out, _ = gh("issue", "list", "--label", "alerta-redes", "--state", "open", "--json", "number,title")
    abiertas = {i["title"]: i["number"] for i in (json.loads(out) if out else [])}
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    for red, (n, err) in E.items():
        titulo = f"⚠️ {REDES[red]} no está publicando"
        if n >= 2 and titulo not in abiertas:
            cuerpo = (f"Las últimas **{n} publicaciones** en {REDES[red]} han fallado. Las demás redes siguen saliendo.\n\n"
                      f"**Error:**\n```\n{err}\n```\n\n**Cómo arreglarlo**\n{ARREGLO[red]}\n\n"
                      "Esta incidencia se cierra sola cuando la red vuelva a publicar.")
            args = ["issue", "create", "--title", titulo, "--body", cuerpo, "--label", "alerta-redes"]
            if owner:
                args += ["--assignee", owner]
            rc, o, e = gh(*args)
            if rc and owner:                                # si no se puede asignar, sin asignar
                rc, o, e = gh(*args[:-2])
            print("aviso abierto:", titulo, o or e, flush=True)
            url = os.environ.get("SLACK_WEBHOOK_URL")
            if url:
                try:
                    import requests
                    requests.post(url, json={"text": f"{titulo}: {n} publicaciones seguidas fallidas. {o}"}, timeout=20)
                except Exception as ex:
                    print("Slack no disponible:", str(ex)[:100])
        elif n == 0 and titulo in abiertas:
            gh("issue", "close", str(abiertas[titulo]), "--comment", f"✅ {REDES[red]} ha vuelto a publicar. Cierro el aviso.")
            print("aviso cerrado:", titulo, flush=True)
    print("alertas:", {k: v[0] for k, v in E.items()}, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                                   # un fallo del aviso nunca rompe la publicación
        print("alerta omitida:", str(e)[:200])

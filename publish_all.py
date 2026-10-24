"""Publica un reel a la vez en Instagram, TikTok y YouTube Shorts (cada destino es independiente: un fallo nunca
bloquea a los demás).

  Instagram   directo por la API de Meta (IG_TOKEN), con portada propia; si no hay IG_TOKEN, por Zernio
  TikTok      Zernio, con portada propia y aviso de contenido creado con IA
  YouTube     Zernio, como Short (vertical < 3 min), categoría Educación y contenido sintético declarado

Interruptores (Settings > Secrets and variables > Actions > Variables): INSTAGRAM, TIKTOK, YOUTUBE = "true"/"false".
"""
import os, threading
from concurrent.futures import ThreadPoolExecutor


def on(name):
    return os.environ.get(name, "true").lower() == "true"


def publish(reel, caption, meta):
    """Devuelve {destino: id de la publicación o 'error: ...'}."""
    if not os.environ.get("ZERNIO_API_KEY") and not os.environ.get("IG_TOKEN"):
        return {"publicar": "error: faltan los secretos ZERNIO_API_KEY e IG_TOKEN"}
    import publish_zernio as Z
    urls, lock, jobs, res = {}, threading.Lock(), {}, {}

    def url(path):                       # cada archivo se sube una sola vez aunque lo pidan dos destinos a la vez
        with lock:
            if path not in urls:
                urls[path] = Z.upload(path)
            return urls[path]

    def portada():
        try:
            return url(meta["cover"]) if meta.get("cover") else None
        except Exception as e:
            print("portada sin subir:", str(e)[:150], flush=True)
            return None
    video = Z.ligero(reel)
    if on("INSTAGRAM"):
        if os.environ.get("IG_TOKEN"):
            import publish_ig as IG

            def ig_reel():
                cu = portada()
                try:
                    m = IG.publish_reel(video, caption, thumb_ms=meta.get("thumb_ms"), cover_url=cu)
                except Exception as e:
                    if not cu:
                        raise
                    print("Instagram no acepta la portada; uso el fotograma:", str(e)[:150], flush=True)
                    m = IG.publish_reel(video, caption, thumb_ms=meta.get("thumb_ms"))
                return f"ig:{m['id']}"
            jobs["instagram_reel"] = ig_reel
        else:
            jobs["instagram_reel"] = lambda: Z.instagram_reel(url(video), caption, meta.get("thumb_ms"))
    if on("TIKTOK"):
        jobs["tiktok_video"] = lambda: Z.tiktok_video(url(video), caption, meta.get("thumb_ms"), cover_url=portada())
    if on("YOUTUBE"):
        jobs["youtube_short"] = lambda: Z.youtube_short(url(video), caption, meta.get("titulo") or meta.get("hook", ""))
    with ThreadPoolExecutor(max(1, len(jobs))) as ex:
        futs = {k: ex.submit(f) for k, f in jobs.items()}
        for k, f in futs.items():
            try:
                res[k] = str(f.result(timeout=1500))
            except Exception as e:
                res[k] = f"error: {str(e)[:200]}"
                print(f"publicación {k} fallida:", str(e)[:300], flush=True)
    return res

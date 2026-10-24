"""TikTok, YouTube Shorts (e Instagram, si no hay IG_TOKEN) a través de Zernio (https://docs.zernio.com).

Env: ZERNIO_API_KEY. Seguridad: solo se publica en cuentas cuyo usuario o nombre coincide con ZERNIO_MATCH (por defecto
"arquitecturaconfidencial"): aunque el mismo Zernio tenga conectadas las cuentas de UDA o de otro proyecto, nunca se
publica en la equivocada. Para fijarlas a mano: ZERNIO_IG_ACCOUNT / ZERNIO_TT_ACCOUNT / ZERNIO_YT_ACCOUNT (ids).
"""
import os, re, subprocess, time, unicodedata
import requests

API = "https://zernio.com/api/v1"
_ACC = {}
PLATFORMS = {"instagram": "ZERNIO_IG_ACCOUNT", "tiktok": "ZERNIO_TT_ACCOUNT", "youtube": "ZERNIO_YT_ACCOUNT"}
MATCH_DEFECTO = "arquitecturaconfidencial"


def _h():
    return {"Authorization": f"Bearer {os.environ['ZERNIO_API_KEY']}"}


def _check(r, what):
    if r.status_code >= 400:
        raise RuntimeError(f"Zernio {what} error {r.status_code}: {r.text[:500]}")
    return r.json() if r.content else {}


def _norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def _names(a):
    keys = ("username", "handle", "displayName", "name", "platformUsername", "accountName", "profileName", "pageName",
            "channelTitle", "title")
    out = [a.get(k) for k in keys if a.get(k)]
    for k in ("metadata", "profile", "platformData"):
        if isinstance(a.get(k), dict):
            out += [a[k].get(x) for x in keys if a[k].get(x)]
    return [str(x) for x in out]


def accounts(verbose=False):
    """{plataforma: id} solo de las cuentas de AC (coinciden con ZERNIO_MATCH)."""
    if _ACC:
        return (_ACC, {}) if verbose else _ACC
    ids = {p: os.environ.get(env) for p, env in PLATFORMS.items()}
    match = _norm(os.environ.get("ZERNIO_MATCH") or MATCH_DEFECTO)
    seen = {}
    if not all(ids.values()):
        data = _check(requests.get(f"{API}/accounts", headers=_h(), timeout=60), "accounts")
        items = data.get("accounts", data if isinstance(data, list) else data.get("data", []))
        for a in items:
            p = (a.get("platform") or "").lower()
            if p not in ids:
                continue
            names = _names(a)
            seen.setdefault(p, []).append(names[0] if names else "?")
            if not ids[p] and any(match in _norm(n) for n in names):
                ids[p] = a.get("_id") or a.get("id")
    _ACC.update({k: v for k, v in ids.items() if v})
    print("Zernio cuentas de AC:", {k: bool(ids.get(k)) for k in PLATFORMS}, "· conectadas:", seen, flush=True)
    return (_ACC, seen) if verbose else _ACC


def _acc(platform):
    acc = accounts().get(platform)
    if not acc:
        raise RuntimeError(f"no hay cuenta de {platform} de AC conectada en Zernio (debe llamarse como "
                           f"'{os.environ.get('ZERNIO_MATCH') or MATCH_DEFECTO}' o fija su id en {PLATFORMS[platform]})")
    return acc


def upload(path):
    """Sube un archivo a Zernio y devuelve su URL pública."""
    ct = {"mp4": "video/mp4", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}[path.rsplit(".", 1)[-1].lower()]
    for attempt in range(3):
        try:
            pre = _check(requests.post(f"{API}/media/presign", headers=_h(), json={
                "filename": os.path.basename(path), "contentType": ct, "size": os.path.getsize(path)}, timeout=60), "presign")
            with open(path, "rb") as f:
                up = requests.put(pre["uploadUrl"], data=f, headers={"Content-Type": ct}, timeout=600)
            if up.status_code >= 400:
                raise RuntimeError(f"Zernio subida {up.status_code}: {up.text[:300]}")
            return pre["publicUrl"]
        except Exception as e:
            if attempt == 2:
                raise
            print("Zernio subida, reintento:", str(e)[:150], flush=True); time.sleep(10 * (attempt + 1))


def _post(body, what):
    for attempt in range(3):
        try:
            res = _check(requests.post(f"{API}/posts", headers=_h(), json=body, timeout=180), what)
            pid = (res.get("post") or res).get("_id") if isinstance(res, dict) else None
            print(f"Zernio {what}: creado {pid}", flush=True)
            return pid or "ok"
        except RuntimeError as e:
            if " 4" in str(e)[:25] and " 429" not in str(e)[:25]:      # error de datos: no sirve reintentar
                raise
            if attempt == 2:
                raise
            time.sleep(15 * (attempt + 1))


def ligero(video_path):
    """Los reels pesan ~10-20 MB. Si algo pasa de 40 MB, se recodifica a 720x1280 (lo aceptan las tres redes)."""
    if os.path.getsize(video_path) <= 40e6:
        return video_path
    out = video_path.replace(".mp4", "_ligero.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_path, "-vf", "scale=720:1280",
                    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "25", "-preset", "veryfast",
                    "-crf", "23", "-maxrate", "2500k", "-bufsize", "5000k", "-g", "50",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", "-use_editlist", "0", out], check=True)
    return out


def _sin_bio(caption):
    """TikTok y YouTube: el enlace de la bio no sirve igual; se nombra la web tal cual."""
    return caption.replace(" (link en la bio)", "").replace("(link en la bio)", "")


# ------------------------------------------------------------------ Instagram (solo si no hay IG_TOKEN)
def instagram_reel(video_url, caption, thumb_ms=1200):
    return _post({"content": caption[:2200], "mediaItems": [{"type": "video", "url": video_url}], "publishNow": True,
                  "platforms": [{"platform": "instagram", "accountId": _acc("instagram"),
                                 "platformSpecificData": {"shareToFeed": True, "thumbOffset": int(thumb_ms or 1000)}}]},
                 "instagram reel")


# ------------------------------------------------------------------ TikTok
def tiktok_video(video_url, caption, cover_ms=1200, cover_url=None, ai=True):
    """ai=True: aviso de contenido creado con IA (todas las imágenes lo son)."""
    ts = {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": True,
          "allow_stitch": True, "content_preview_confirmed": True, "express_consent_given": True,
          "video_cover_timestamp_ms": int(cover_ms or 1000)}
    if cover_url:
        ts["video_cover_image_url"] = cover_url
    if ai:
        ts["video_made_with_ai"] = True
    body = {"content": _sin_bio(caption)[:2150], "mediaItems": [{"type": "video", "url": video_url}], "publishNow": True,
            "platforms": [{"platform": "tiktok", "accountId": _acc("tiktok")}], "tiktokSettings": ts}
    try:
        return _post(body, "tiktok vídeo")
    except RuntimeError as e:
        if not cover_url or " 4" not in str(e)[:25]:
            raise
        print("TikTok no acepta la portada propia; uso el fotograma:", str(e)[:150], flush=True)
        ts.pop("video_cover_image_url", None)
        return _post(body, "tiktok vídeo")


# ------------------------------------------------------------------ YouTube Shorts
def youtube_short(video_url, caption, title, first_comment=None):
    """Vídeo vertical de menos de 3 min: YouTube lo clasifica como Short (sin portada propia: la API no lo permite).
    Categoría 27 (Educación); contenido sintético declarado (imágenes de IA)."""
    tags = [t.lstrip("#") for t in re.findall(r"#\w+", caption)][:12]
    titulo = re.sub(r"\s+", " ", title).strip()[:90] + " #shorts"
    psd = {"title": titulo[:100], "visibility": "public", "madeForKids": False, "categoryId": "27",
           "containsSyntheticMedia": True}
    if first_comment:
        psd["firstComment"] = first_comment[:1000]
    body = {"content": _sin_bio(caption)[:4900], "mediaItems": [{"type": "video", "url": video_url}], "publishNow": True,
            "tags": tags, "platforms": [{"platform": "youtube", "accountId": _acc("youtube"), "platformSpecificData": psd}]}
    return _post(body, "youtube short")


# ------------------------------------------------------------------ analíticas
def analytics(post_id):
    r = requests.get(f"{API}/analytics", headers=_h(), params={"postId": post_id}, timeout=60)
    if r.status_code == 202:
        return None
    return _check(r, "analytics")

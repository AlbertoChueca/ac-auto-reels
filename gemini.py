"""Llamadas a Google Gemini (texto/JSON, con vídeo o imágenes opcionales). Una sola puerta para todos los agentes.

Env: GEMINI_API_KEY. Opcional: GEMINI_TEXT_MODEL (lista separada por comas) y GEMINI_VERIFY_MODEL.
Si un nombre de modelo deja de existir se prueba automáticamente con los que la clave tiene disponibles.
"""
import json, os, re, time
import requests

API = "https://generativelanguage.googleapis.com/v1beta/models"
TEXT_MODELS = [m for m in os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.8-flash,gemini-3.5-flash,gemini-3-flash").split(",") if m]
VERIFY_MODELS = [m for m in os.environ.get("GEMINI_VERIFY_MODEL", "").split(",") if m]
_AVAIL = []


def key():
    return os.environ["GEMINI_API_KEY"]


def available():
    """Modelos que esta clave puede usar con generateContent."""
    if not _AVAIL:
        try:
            r = requests.get(f"{API}?pageSize=200", headers={"x-goog-api-key": key()}, timeout=60)
            _AVAIL.extend(m["name"].split("/")[-1] for m in r.json().get("models", [])
                          if "generateContent" in m.get("supportedGenerationMethods", []))
        except Exception:
            pass
    return _AVAIL


def _text_only(m):
    return not any(x in m for x in ("image", "tts", "live", "audio", "lite", "embedding", "native"))


def _rank(n):
    v = re.findall(r"(\d+(?:\.\d+)?)", n)
    return (-float(v[0]) if v else 0, "preview" in n)


def post(model, body, tries=4):
    for k in range(tries):
        r = requests.post(f"{API}/{model}:generateContent", headers={"x-goog-api-key": key(), "Content-Type": "application/json"},
                          json=body, timeout=240)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(15 * (k + 1)); continue
        if r.status_code >= 400:
            raise RuntimeError(f"Gemini {model} {r.status_code}: {r.text[:400]}")
        return r.json()
    raise RuntimeError(f"Gemini {model}: demasiados reintentos")


def ask(parts, temperature=0.6, careful=False):
    """parts: lista de partes Gemini (o un str). Devuelve el JSON de la respuesta ya parseado.
    careful=True (verificador): prueba primero los modelos 'pro' más nuevos, con temperatura baja."""
    if isinstance(parts, str):
        parts = [{"text": parts}]
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": temperature}}
    names = list(TEXT_MODELS)
    if careful:
        pros = sorted([m for m in available() if "pro" in m and _text_only(m)], key=_rank)
        names = VERIFY_MODELS + pros[:2] + names
    names += sorted([m for m in available() if "flash" in m and _text_only(m)], key=_rank)
    last = None
    for model in dict.fromkeys(names):
        try:
            j = post(model, body)
            txt = j["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(re.sub(r"^```(json)?|```$", "", txt.strip()))
        except Exception as e:
            last = e
            if not any(c in str(e) for c in (" 404", " 400", " 403", "JSONDecodeError", "Expecting")):
                break
    raise last or RuntimeError("Gemini: ningún modelo disponible")


IMAGE_MODELS = [m for m in os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image,gemini-2.5-flash-image").split(",") if m]


def image(prompt, aspect="9:16", refs=()):
    """Genera una imagen (PIL) con Gemini. refs: lista de PIL de referencia (opcional)."""
    import base64, io
    from PIL import Image
    parts = [{"text": prompt}]
    for im in refs:
        b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=85)
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}})
    last = None
    for model in dict.fromkeys(IMAGE_MODELS + [m for m in available() if "image" in m and "imagen" not in m]):
        try:
            j = post(model, {"contents": [{"parts": parts}],
                             "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": aspect}}})
            for part in j["candidates"][0]["content"]["parts"]:
                d = part.get("inlineData") or part.get("inline_data")
                if d:
                    print("modelo de imagen:", model, flush=True)
                    return Image.open(io.BytesIO(base64.b64decode(d["data"]))).convert("RGB")
            last = RuntimeError(f"{model}: sin imagen en la respuesta")
        except Exception as e:
            last = e
    raise last or RuntimeError("ningún modelo de imagen disponible")

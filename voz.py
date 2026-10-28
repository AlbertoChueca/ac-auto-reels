"""Voz de los reels de AC: castellano de España, con interpretación (altibajos, énfasis, pausas), nada de locutor plano.

Motor principal: Gemini TTS. Cada frase se graba con su propia dirección de actor (la escribe el director de voz:
«sube, sorpresa», «baja, en confianza», «remata con energía»...) y todas las frases a la vez, en paralelo: rápido y con
el mismo timbre (misma voz de Gemini). Cada toma se comprueba (duración razonable para su texto) y se repite si falla.
Reserva: Google Cloud TTS Chirp 3 HD es-ES (si la clave tiene la API activada). Sin ninguna: el reel no sale.

    import voz
    clips = voz.grabar(["¿Sabes qué mira primero el tribunal?", ...], ["excited, rising", ...])
"""
import base64, os, re, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests

SR = 24000
API = "https://generativelanguage.googleapis.com/v1beta"
VOZ = os.environ.get("GEMINI_VOICE", "Puck")                   # masculina, joven y con energía (cámbiala en Variables)
MODELOS = [m for m in os.environ.get("GEMINI_TTS_MODEL", "").split(",") if m] + [
    "gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-3.1-flash-tts", "gemini-2.5-pro-preview-tts",
    "gemini-2.5-flash-preview-tts"]
# Indicaciones en inglés y cortas: así el modelo no las confunde con el texto en español.
PERFIL = ("Voice: a young man from Madrid, Spain (late twenties), an architect who finished his master's thesis not long "
          "ago, talking to architecture students like an older classmate. Clear CASTILIAN Spanish from Spain: "
          "distinción ('z' and 'c' before e/i sound like English 'th'), crisp final 's', Spanish intonation — never "
          "Latin American, never neutral. Real human delivery: varied pitch with clear ups and downs, energy changes, "
          "emphasis on key words, micro-pauses, a smile in the voice. Never flat, never monotone, never an announcer or "
          "a robot. Say the text exactly once.")
ENGINE = None
_MODELO = []
_LANG = ["es-ES"]


def _resample(a, sr):
    if sr == SR:
        return a.astype(np.float32)
    n = int(len(a) * SR / sr)
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)


def _modelos(key):
    if _MODELO:
        return _MODELO
    disp = []
    try:
        r = requests.get(f"{API}/models", params={"key": key, "pageSize": 200}, timeout=30)
        disp = [m["name"].split("/")[-1] for m in r.json().get("models", []) if "tts" in m["name"]]
    except Exception:
        pass
    orden = [m for m in MODELOS if not disp or m in disp] + sorted(m for m in disp if m not in MODELOS)
    _MODELO.extend(dict.fromkeys(orden))
    return _MODELO


def _gemini(prompt, key):
    last = None
    for model in _modelos(key):
        for intento in range(3):
            try:
                cfg = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOZ}}}
                if _LANG[0]:
                    cfg["languageCode"] = _LANG[0]
                r = requests.post(f"{API}/models/{model}:generateContent", headers={"x-goog-api-key": key}, timeout=120,
                                  json={"contents": [{"parts": [{"text": prompt}]}],
                                        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": cfg}})
                if r.status_code == 400 and "language" in r.text.lower() and _LANG[0]:
                    _LANG[0] = None; continue
                if r.status_code in (429, 500, 502, 503, 504):
                    last = RuntimeError(f"{model} {r.status_code}"); time.sleep(5 * (intento + 1)); continue
                if r.status_code != 200:
                    last = RuntimeError(f"{model} {r.status_code}: {r.text[:200]}"); break
                cands = r.json().get("candidates") or []
                partes = ((cands[0].get("content") or {}).get("parts") or []) if cands else []
                if not partes:                                # a veces no devuelve audio: otro intento / otro modelo
                    last = RuntimeError(f"{model}: sin audio ({(cands[0].get('finishReason') if cands else 'vacío')})")
                    if intento == 0:
                        continue
                    break
                for p in partes:
                    d = p.get("inlineData") or p.get("inline_data")
                    if d:
                        rate = int((re.findall(r"rate=(\d+)", d.get("mimeType") or d.get("mime_type") or "") or [24000])[0])
                        pcm = np.frombuffer(base64.b64decode(d["data"]), dtype="<i2").astype(np.float32) / 32768
                        if model in _MODELO and _MODELO[0] != model:          # el que funciona, primero
                            _MODELO.remove(model); _MODELO.insert(0, model)
                        return _resample(pcm, rate)
                last = RuntimeError(f"{model}: respuesta sin audio"); break
            except requests.exceptions.RequestException as e:
                last = e; time.sleep(3)
    raise last or RuntimeError("no hay modelo de voz de Gemini disponible")


def _chirp(texto, key):
    """Reserva: Google Cloud TTS Chirp 3 HD (voz de España). Menos interpretación, pero fiable."""
    import io, wave
    voz = os.environ.get("GOOGLE_TTS_VOICE", "es-ES-Chirp3-HD-Puck")
    body = {"input": {"text": texto}, "voice": {"languageCode": "es-ES", "name": voz},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": SR, "speakingRate": 1.07}}
    for intento in range(3):
        r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize", params={"key": key}, json=body,
                          timeout=60)
        if r.status_code in (429, 500, 503):
            time.sleep(3 * (intento + 1)); continue
        if r.status_code != 200:
            raise RuntimeError(f"Google TTS {r.status_code}: {r.text[:200]}")
        with wave.open(io.BytesIO(base64.b64decode(r.json()["audioContent"]))) as w:
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
            return _resample(pcm, w.getframerate())
    raise RuntimeError("Google TTS no responde")


# ------------------------------------------------------------------ texto hablado y control de tomas
def hablado(t):
    """Lo que se dice: web, siglas y símbolos como se pronuncian en España."""
    t = re.sub(r"https?://", "", t)
    t = re.sub(r"arquitecturaconfidencial\.com", "arquitectura confidencial punto com", t, flags=re.I)
    rep = [(r"\bTFM\b", "te efe eme"), (r"\bTFG\b", "te efe ge"), (r"\bPFC\b", "pe efe ce"), (r"\bIA\b", "IA"),
           (r"\bCYPE\b", "cipe"), (r"\bCAD\b", "CAD"), (r"\bBIM\b", "BIM"), (r"\bLOD\b", "lod"),
           (r"1:(\d+)", r"uno a \1"), (r"(\d+) %", r"\1 por ciento"), (r"·", ","), (r"\s+&\s+", " y "), (r"«|»|\"", "")]
    for a, b in rep:
        t = re.sub(a, b, t)
    return re.sub(r"\s+", " ", t).strip()


def _palabras(t):
    return len(re.findall(r"[\wáéíóúñü]+", t, re.I))


def _recorta(a, umbral=0.012):
    """Quita silencios al principio y al final (deja 60 ms y 120 ms de aire)."""
    if not len(a):
        return a
    env = np.convolve(np.abs(a), np.ones(240) / 240, "same")
    idx = np.where(env > umbral)[0]
    if not len(idx):
        return a
    i0 = max(0, idx[0] - int(0.06 * SR)); i1 = min(len(a), idx[-1] + int(0.12 * SR))
    return a[i0:i1]


def _pule(a):
    """Nivel uniforme, compresión suave y un poco de presencia: suena a voz grabada, no a máquina."""
    a = a - np.mean(a)
    pico = np.percentile(np.abs(a), 99.5) or 1.0
    a = a / pico * 0.6
    a = np.tanh(a * 1.4) / np.tanh(1.4)                              # compresión suave
    hp = a - np.convolve(a, np.ones(24) / 24, "same")                 # realce ligero de 1-4 kHz
    a = a + 0.12 * hp
    return (a / (np.max(np.abs(a)) or 1) * 0.89).astype(np.float32)


def _ok(a, texto):
    """La toma vale si su duración es razonable para el texto (ni ha leído indicaciones ni ha cortado la frase)."""
    seg = len(a) / SR
    esperado = _palabras(texto) / 2.9 + 0.4                           # ~2,9 palabras por segundo
    return 0.45 * esperado < seg < 1.9 * esperado + 0.8


def _linea_gemini(texto, direccion, key):
    """Hasta 6 tomas: con dirección, más simple, y solo el texto (sin conectores tipo «Truco:»). Vale la primera con
    duración natural; si ninguna, la más cercana a lo esperado (si es razonable)."""
    limpio = re.sub(r"^(truco|ojo|y esto es clave|clave)\s*:\s*", "", texto, flags=re.I)
    prompts = [f"{PERFIL}\nPerformance for this line: {direccion}.\nSpeak only the Spanish text after the colon, word "
               f"for word: {texto}",
               f"In Castilian Spanish from Madrid (distinción, no seseo), {direccion}, sounding like a real person: {texto}",
               f"{PERFIL}\nSpeak only this Spanish text, naturally: {limpio}",
               f"Castilian Spanish from Spain, natural and expressive: {limpio}",
               limpio, texto]
    tomas = []
    esperado = _palabras(texto) / 2.9 + 0.4
    for pr in prompts:
        try:
            a = _recorta(_gemini(pr, key))
        except Exception as e:
            print("voz: toma fallida:", str(e)[:150], flush=True); continue
        if _ok(a, texto):
            return a
        tomas.append(a)
        print(f"voz: repito «{texto[:40]}» ({len(a) / SR:.1f} s)", flush=True)
    buenas = [t for t in tomas if 0.35 * esperado < len(t) / SR < 2.6 * esperado + 1]
    if buenas:
        return min(buenas, key=lambda t: abs(np.log((len(t) / SR) / esperado)))
    raise RuntimeError(f"sin toma válida para: {texto[:60]}")


def grabar(textos, direcciones=None):
    """Lista de clips (float32, 24 kHz), uno por texto, ya pulidos. Todas las frases a la vez."""
    global ENGINE
    textos = [hablado(t) for t in textos]
    direcciones = list(direcciones or ["natural, engaging"] * len(textos))
    key = os.environ.get("GEMINI_API_KEY")
    if os.environ.get("VOZ") == "mock" or not key:                    # prueba local sin red: tono sintético
        ENGINE = "mock"
        return [_pule(0.2 * np.sin(np.linspace(0, 2 * np.pi * 180 * (_palabras(t) / 2.9 + 0.4),
                                               int(SR * (_palabras(t) / 2.9 + 0.4))))) for t in textos]
    if os.environ.get("VOZ") != "chirp":
        try:
            with ThreadPoolExecutor(min(6, len(textos))) as ex:
                clips = list(ex.map(lambda td: _linea_gemini(td[0], td[1], key), zip(textos, direcciones)))
            ENGINE = f"gemini:{VOZ}"
            return [_pule(c) for c in clips]
        except Exception as e:
            print("voz: Gemini TTS no disponible, uso Chirp 3 HD:", str(e)[:200], flush=True)
    gkey = os.environ.get("GOOGLE_TTS_KEY") or key
    with ThreadPoolExecutor(4) as ex:
        clips = list(ex.map(lambda t: _recorta(_chirp(t, gkey)), textos))
    ENGINE = "chirp"
    return [_pule(c) for c in clips]

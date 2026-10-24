"""Datos de la marca en un solo sitio (AC · ArquitecturaConfidencial).

Enfoque acordado: asesoría y acompañamiento para el TFM/TFG/PFC de arquitectura. Nunca se dice ni se insinúa en redes
que «hacemos el TFM» ni nada sobre ocultarlo al tutor: TikTok, Instagram y YouTube limitan esas cuentas y quema la marca.
"""
import os

WEB = os.environ.get("APP_WEB", "arquitecturaconfidencial.com")
HANDLE = os.environ.get("IG_HANDLE", "@arquitecturaconfidencial")
NOMBRE = "AC · ArquitecturaConfidencial"
FIRMA = "Asesoría para tu TFM de arquitectura"
CTA = "Auditoría gratuita de tu TFM"
# Línea suave al final de TODAS las descripciones (contenido útil + recordatorio discreto)
CTA_SUAVE = f"¿Vas justo con el TFM? Pide una auditoría gratuita de tu proyecto en {WEB} (link en la bio)."
# Cierre de los reels de AC (20 % del calendario)
CTA_AC = (f"En AC acompañamos a estudiantes de arquitectura en su TFM, TFG y PFC: planificación, revisión técnica y "
          f"apoyo en las fases que se atascan.\n\n👉 Pide tu auditoría gratuita en {WEB} (link en la bio).")
PROHIBIDO = ("te hacemos el tfm", "hacemos tu tfm", "nadie sabrá", "nadie lo sabr", "tu tutor no", "sin que se ent",
             "te lo hacemos", "compra tu tfm", "100% confidencial", "confidencial")


def limpio(texto):
    """True si el texto no contiene ninguna promesa prohibida (se comprueba antes de publicar)."""
    t = (texto or "").lower()
    return not any(p in t for p in PROHIBIDO if p != "confidencial") and \
        "confidencial" not in t.replace("arquitecturaconfidencial", "").replace("arquitectura confidencial", "")

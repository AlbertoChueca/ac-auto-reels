# AC · ArquitecturaConfidencial – Publicación automática

Clon del sistema de UDA adaptado a **estudiantes de arquitectura** (TFG, TFM, PFC). Publica sola **2 reels al día** en
**Instagram** (directo por la API de Meta), **TikTok** y **YouTube Shorts** (vía Zernio), y un bot contesta los
comentarios y publica la solución de los tests al día siguiente.

| Hora (España) | Qué |
|---|---|
| 14:00 | Reel (`mediodia`) |
| 20:30 | Reel (`noche`) |

## Calendario (14 reels a la semana)
| | 14:00 | 20:30 |
|---|---|---|
| Lunes | Test | Galería |
| Martes | Tips | V/F |
| Miércoles | Render sin/con postpro | Test |
| Jueves | Encuesta | **Tips de AC** |
| Viernes | Test | Del boceto al render |
| Sábado | Galería | V/F |
| Domingo | Así se construye | **Tips de AC** |

- **Interacción** (test, V/F, encuesta): el reel acaba en la pregunta y **nunca enseña la solución**. El bot la publica en
  comentarios 12-24 h después (en TikTok la fija arriba) y responde a cada uno si ha acertado.
- **Inspiración y aprendizaje**: galerías de referentes para el TFM, tips, render sin y con postproducción, del boceto
  al render y así se construye.
- **AC (2 a la semana)**: tips de TFM (tribunal, organización, entrega) que cierran con la auditoría gratuita.
  Además, **todas** las descripciones acaban con una línea discreta de la auditoría gratuita.

**Enfoque de marca (obligatorio):** asesoría y acompañamiento. Nunca se dice ni se insinúa que «hacemos el TFM» ni nada
sobre ocultarlo al tutor (`marca.limpio()` bloquea esas frases en descripciones, banco y respuestas del bot).

**Estética:** tinta casi negra, papel de croquis y amarillo rotulador; tipografía TeX Gyre Adventor. Imágenes creadas
con IA (Gemini), revisadas una a una, y vídeo revisado por otro agente con **nota mínima 8**. Si no llega, prueba otra
temática del mismo grupo; si nada llega, ese hueco no se publica.

## Puesta en marcha (una vez)
1. **Cuentas**: Instagram profesional de AC vinculada a una página de Facebook, TikTok y canal de YouTube.
2. **Settings → Secrets and variables → Actions → Secrets**:
   - `GEMINI_API_KEY` (imágenes, revisión, bot). Puede ser la misma que la de UDA.
   - `IG_TOKEN`: token de **página** de Facebook (empieza por `EAA`) de la página vinculada a la cuenta de Instagram de
     AC, con `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`,
     `instagram_manage_insights` e `instagram_manage_comments` (para el bot). El código comprueba que es la cuenta de AC.
   - `ZERNIO_API_KEY`: en Zernio conecta **TikTok y YouTube de AC**. Solo se publica en cuentas cuyo nombre contiene
     «arquitecturaconfidencial» (así nunca se publica en las de UDA aunque estén en el mismo Zernio). Si tu cuenta se
     llama distinto, pon la variable `ZERNIO_MATCH` o los ids en `ZERNIO_TT_ACCOUNT` / `ZERNIO_YT_ACCOUNT`.
3. **Variables**: `IG_HANDLE` con el usuario real de Instagram (por defecto `@arquitectura_confidencial`).
4. **Actions → Comprobar conexiones → Run workflow**: todo en verde.
5. **Actions → Reels diarios → Run workflow** con «Solo generar el vídeo» marcado (prueba varias temáticas) y descarga
   el vídeo en *Artifacts*.
6. **Variables → `ACTIVO` = `true`**. Hasta entonces no se publica nada programado.

## Variables
| Variable | Por defecto | Qué hace |
|---|---|---|
| `ACTIVO` | (vacía) | `true` enciende reels y bot |
| `IG_HANDLE` | `@arquitectura_confidencial` | Cuenta de Instagram esperada |
| `ZERNIO_MATCH` | `arquitecturaconfidencial` | Nombre que deben tener las cuentas en Zernio (TikTok y YouTube: arquitecturaconfidencial) |
| `INSTAGRAM`, `TIKTOK`, `YOUTUBE` | `true` | Interruptores por red |
| `COMUNIDAD` | `true` | `false` apaga el bot |
| `PUBLISH_MAX_WAIT_MIN` | `90` | Minutos máximos de espera para publicar a la hora exacta |

## Archivos
- `visual.py`: motor (imágenes, montaje, portada, revisión y descripción). `tematicas.py`: calendario.
- `fuentes/visual.json`: banco de contenido. En test y V/F la opción correcta va primera (se baraja al montar).
  `ampliar_banco.py` lo amplía solo cuando se gasta; cada pregunta nueva la resuelve a ciegas otro modelo y solo entra si
  coincide.
- `publish_all.py`, `publish_ig.py`, `publish_zernio.py`: publicación. `comunidad.py`: bot de comentarios.
- `log.jsonl` (qué se publicó, con la solución de cada test), `used.json` (piezas usadas), `comunidad_estado.md`.

Repositorio público = minutos de GitHub Actions sin límite. Los secretos no se ven nunca.

# AC · ArquitecturaConfidencial – Publicación automática

Clon del sistema de UDA adaptado a **estudiantes de arquitectura** (TFG, TFM, PFC). Publica sola **2 reels al día** en
**Instagram** (directo por la API de Meta), **TikTok** y **YouTube Shorts** (vía Zernio), y un bot contesta los
comentarios y publica la solución de los tests al día siguiente.

| Hora (España) | Qué |
|---|---|
| 14:00 | Reel (`mediodia`) |
| 20:30 | Reel (`noche`) |

## Calendario (14 reels a la semana: 80 % útil, 20 % venta)
| | 14:00 | 20:30 |
|---|---|---|
| Lunes | Tips TFM | Referentes |
| Martes | IA para arquitectura | Test |
| Miércoles | Tips Proyectos | **Documentación (venta)** |
| Jueves | Tips TFM | Verdadero o falso |
| Viernes | Referentes | **Auditoría gratuita (venta)** |
| Sábado | IA para arquitectura | Tips Proyectos |
| Domingo | Tips TFM | **Documentación (venta)** |

Cuando hay datos reales (12+ reels medidos), el estratega cambia los huecos útiles hacia lo que más se guarda, comparte
y comenta. Los de venta no se tocan.

- **Todos** los reels llevan voz en off (castellano de España, con altibajos), subtítulos al ritmo de la voz y
  **arquitecturaconfidencial.com visible en todos los fotogramas** y en el cierre.
- **Tests y V/F**: el reel acaba en la pregunta y nunca enseña la solución. El bot la publica 12-24 h después.
- **Documentación (venta)**: planos REALES del equipo (assets/portfolio), recortados para que no salga ningún nombre,
  logo, cartela, calle ni fecha, con la etiqueta «Trabajo real». Nunca se menciona UDA.
- **Referentes**: obras reales verificadas (obra · autor, ciudad y año); las imágenes son conceptuales (IA) y se dice.

## Los 9 agentes (agentes.py y reel.py)
0. **Cazatendencias** (1 vez al día): busca en Google lo que funciona AHORA en reels, TikToks y Shorts del nicho (formatos, ganchos, temas calientes de la época del curso, ejemplos con fuentes) -> tendencias.json.
1. **Estratega** (1 vez al día): cruza los resultados reales con las tendencias -> playbook.json.
2. **Guionista**: guion hablado desde la pieza del banco, sin añadir datos.
3. **Gancho**: 5 ganchos, elige el mejor para parar el scroll.
4. **Verificador**: rigor técnico y reglas de AC; corrige o vuelve al banco.
5. **Director de voz**: dirección por frase (sube, baja, pausa, remata).
6. **Directora de arte**: prompts de imagen de serie + revisión de cada imagen.
7. **Revisor de vídeo**: ve y escucha el reel; nota mínima **8** (si no, rehace solo lo que falla).
8. **Editor**: descripción, hashtags y título de YouTube, siempre con la web.

Velocidad: 3-4 y 5-6-8 trabajan a la vez; imágenes y voz se generan en paralelo; ~3-5 min por reel.

**Enfoque de marca (obligatorio):** asesoría y acompañamiento. Nunca «hacemos el TFM» ni nada sobre ocultarlo
(`marca.limpio()` lo bloquea en guion, descripción, banco y respuestas del bot).

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
| `GEMINI_VOICE` | `Puck` | Voz de Gemini (Puck, Fenrir, Orus, Charon...) |
| `PUBLISH_MAX_WAIT_MIN` | `90` | Minutos máximos de espera para publicar a la hora exacta |

## Archivos
- `reel.py`: motor (imágenes, montaje, portada, revisión). `agentes.py`: los agentes. `voz.py`: voz. `tematicas.py`: calendario.
- `assets/portfolio/`: planos reales anonimizados por tipo (planimetria, construccion, instalaciones, estructuras).
- `fuentes/banco.json`: banco de contenido. En test y V/F la opción correcta va primera (se baraja al montar).
  `ampliar_banco.py` lo amplía solo cuando se gasta; cada pregunta nueva la resuelve a ciegas otro modelo y solo entra si
  coincide.
- `publish_all.py`, `publish_ig.py`, `publish_zernio.py`: publicación. `comunidad.py`: bot de comentarios.
- `log.jsonl` (qué se publicó, con la solución de cada test), `used.json` (piezas usadas), `comunidad_estado.md`.

Repositorio público = minutos de GitHub Actions sin límite. Los secretos no se ven nunca.

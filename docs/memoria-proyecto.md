# Memoria del proyecto: Pitranscriptor

Última consolidación: 25 de noviembre de 2026. Este documento resume las decisiones de la conversación y enlaza los archivos del repositorio; no es una transcripción literal. Las indicaciones posteriores del usuario prevalecen sobre esta memoria.

## Identidad y estado

- **Nombre:** Pitranscriptor. **Autor y marca:** sudo_pita.
- **Repositorio público:** https://github.com/Pyyta/Pitranscriptor. Rama inicial `main`; remoto `origin`.
- **Ubicación inicial del proyecto:** `C:\Users\danyp\Documents\ChatGPT\New project`. La ubicación puede cambiar si se clona o se usa otro entorno; el repositorio es la referencia portable.
- **Estado actual:** fase 1 preparada con cuatro grabaciones locales autorizadas y referencias revisadas por el usuario. El núcleo local transcribe desde la línea de comandos, divide en fragmentos de hasta siete palabras, guarda proyectos y exporta SRT y WebVTT. La fase 2 compara modelos de reconocimiento y la interfaz e instaladores están en desarrollo. Véase [desarrollo](desarrollo.md).
- **Alcance autorizado:** inicialmente el usuario pidió planificar sin programar; el 25 de noviembre de 2026 pidió empezar la primera fase de creación y mantener commits y push de cada progreso relevante. Esta instrucción autoriza la implementación de la preparación técnica.
- El repositorio es público: esta memoria, el código y su historial pueden ser vistos por terceros. No registrar datos privados, contraseñas, tokens, videos o audios personales.

## Contexto y objetivo

El usuario necesita una aplicación de escritorio sencilla para subtitular reels y videos de hasta cinco minutos. Su mayor prioridad es la precisión al transcribir español mezclado con inglés y vocabulario de tecnología, permitiendo después corregir palabras y personalizar subtítulos dinámicos con una experiencia de edición inspirada en Canva. No se pidió copiar su marca ni su interfaz exacta.

Prioridades de la primera versión indicadas por el usuario: **transcripción precisa, edición de texto y apariencia en el video, y cambio de estilos**. El producto completo también incluye línea de tiempo, proyectos persistentes, efectos, exportación y distribución mediante instaladores. El usuario acepta que el reconocimiento demore, incluso uno o dos minutos, a cambio de precisión; no se ha fijado una garantía de tiempo.

## Decisiones e instrucciones del usuario

1. Windows 10 o posterior y Linux, con especial atención a Linux; máxima compatibilidad de componentes posible. Equipos de referencia: CPU AMD Ryzen, NVIDIA RTX 3050 y AMD Radeon Vega 8. Investigar el kernel Linux si resulta necesario; no hay obligación de modificarlo.
2. Herramientas gratuitas y preferiblemente de código abierto. El proyecto será redistribuido. Inicialmente se solicitó `git clone`, pero después el usuario cambió de opinión y pidió **instaladores**. Conservar también el repositorio para desarrollo y distribución de código.
3. Trabajo local sin conexión y opción conectada para intentar mejorar resultados. El proveedor, sus límites y el permiso para enviar audio a terceros no quedaron definidos. No suponer que estar conectado mejora la transcripción; informar y obtener el consentimiento del usuario de la aplicación antes de enviar audio fuera del equipo.
4. Videos habituales verticales y horizontales, duración máxima de cinco minutos; uno a la vez. Audios de calidad variable. Importación y salida sujetas a los códecs efectivamente disponibles.
5. Mezcla español-inglés como función principal, además de videos en inglés. Reconocer términos del [vocabulario inicial](vocabulario.md), ofrecer alternativas cuando sea posible e intentar eliminar muletillas como «eee». Identificar frases por colores de hablante; la identificación automática exacta no está garantizada y requiere validación.
6. **Corrección posterior del usuario:** objetivo configurable de aproximadamente cuatro palabras, priorizar pausas y terminar frases cuando sea posible; el límite anterior de cinco deja de ser rígido. **Máximo absoluto: siete palabras por fragmento**; dividir frases más largas. Resaltado por palabra configurable y selección de distintos efectos.
7. Edición imprescindible de palabras y fragmentos, preferentemente sobre el video. Tamaño y posición de un fragmento deben cambiarse sin alterar los demás. Personalizar tipografía, color, negrita, contorno, sombra, fondo, opacidad, alineación, posición y animación; guardar presets por usuario. Posición inferior por defecto, ajustable. No añadir emojis.
8. Línea de tiempo con forma de onda, zoom, velocidades de reproducción, mover, recortar, dividir, unir, añadir, borrar y duplicar fragmentos, editar tiempos de palabra y deshacer/rehacer. Vista previa y guardado/reapertura de proyectos.
9. Exportar video con subtítulos integrados y archivos independientes; elección de calidad, resolución y cuadros por segundo. Resolución máxima igual a la del video de entrada; conservar audio y cuadros por segundo cuando sea posible. MP4 y, preferiblemente, MOV; elegir carpeta/nombre y proteger contra sobrescritura accidental. No se requiere exportación parcial. Los subtítulos integrados requieren recodificación; la calidad visual y los estilos de SRT/VTT no equivalen necesariamente al video.
10. Interfaz en español e inglés, con estética de computación de los 90 sin neón excesivo. Mostrar «Creado por sudo_pita» y las redes indicadas abajo.
11. Todo debe versionarse en Git y GitHub mediante commits claros y específicos, cada uno seguido de su push. Si hay impedimentos, explicar el estado real. No publicar secretos ni archivos personales.

## Requisitos funcionales (RF)

| ID | Requisito |
| --- | --- |
| RF-01 | Importar un video compatible de hasta cinco minutos, vertical u horizontal; un video por proyecto de trabajo. |
| RF-02 | Transcribir voz en español, inglés y mezcla de ambos, usando pistas del vocabulario tecnológico sin sustituciones ciegas. |
| RF-03 | Permitir transcripción sin conexión con el modelo instalado y prever opción conectada viable y gratuita. |
| RF-04 | Mostrar progreso de transcripción; permitir revisar dudas y alternativas cuando el motor las ofrezca. |
| RF-05 | Detectar y tratar muletillas de forma corregible; distinguir hablantes por colores y permitir corregirlos. |
| RF-06 | Generar marcas temporales por palabra y fragmentos de objetivo configurable, normalmente cuatro palabras y máximo siete. |
| RF-07 | Editar palabras y fragmentos; reajustar sus tiempos y permitir dividir, unir, añadir, borrar y duplicar. |
| RF-08 | Mostrar vista previa con edición visual de posición y tamaño, sin afectar otros fragmentos salvo acción global explícita. |
| RF-09 | Aplicar estilos, efectos y resaltado por palabra configurables; guardar y reutilizar presets personales. |
| RF-10 | Mostrar línea de tiempo con forma de onda, zoom y velocidades de reproducción, y ofrecer deshacer/rehacer. |
| RF-11 | Guardar y abrir proyectos, incluidas referencias al video, texto, tiempos, estilos y ajustes. |
| RF-12 | Exportar video subtitulado y archivos SRT/VTT; elegir formato disponible, calidad, resolución, fps, carpeta y nombre. |
| RF-13 | Advertir antes de sobrescribir y comunicar fallos, límites y códecs no disponibles. |
| RF-14 | Ofrecer interfaz en español e inglés y mostrar créditos y enlaces sociales del autor. |
| RF-15 | Proporcionar instalador de Windows y una distribución instalable o equivalente para Linux, tras definir formatos y probarlos. |

## Requisitos no funcionales (RNF)

| ID | Requisito |
| --- | --- |
| RNF-01 | Compatibilidad amplia en Windows 10+ y Linux; verificar sistemas, CPU y GPU reales antes de afirmar soporte. |
| RNF-02 | Priorizar precisión sobre velocidad y evaluar específicamente mezcla español-inglés y términos técnicos. No garantizar transcripción perfecta. |
| RNF-03 | Funcionar localmente sin internet con los modelos y dependencias ya instalados; contemplar CPU y aceleración compatible sin exigir GPU. |
| RNF-04 | Interfaz sencilla, legible y retro; no bloquearla durante procesos largos y comunicar su progreso. |
| RNF-05 | Utilizar herramientas gratuitas y preferiblemente abiertas; revisar licencias y derechos de redistribución de cada componente, modelo y fuente. |
| RNF-06 | Mantener privacidad: no enviar audio sin aviso y consentimiento; no subir datos sensibles al repositorio público. |
| RNF-07 | Mantener resolución de exportación dentro de la original y preservar orientación, fps y audio cuando sea posible; informar conversiones. |
| RNF-08 | Ser reproducible y mantenible: pruebas relevantes, documentación actualizada, commits claros y push por commit. |
| RNF-09 | Gestionar errores y datos ausentes sin perder trabajo; guardar proyectos de manera segura y no modificar el video original. |

## Arquitectura propuesta, no definitiva

Python/PySide6 para escritorio, FFmpeg/ffprobe para medios y faster-whisper con modelos multilingües para investigación inicial. La fase 1 fija versiones de evaluación en `pyproject.toml` y `uv.lock`; su importación no demuestra precisión ni integración del producto. Evaluar precisión y coste de CPU/GPU con muestras reales antes de seleccionar modelos. Vega 8 no estaba entre las GPU AMD de los binarios ROCm de CTranslate2 consultados al planificar; tratar CPU como alternativa y verificar documentación y hardware al implementar. Separar proveedores de transcripción, dominio, editor, persistencia y exportación. Véase [arquitectura.md](arquitectura.md).

## Redes proporcionadas por el usuario

- Instagram: https://www.instagram.com/sudo_pita/
- TikTok: https://www.tiktok.com/@sudo_pita
- YouTube: https://www.youtube.com/@sudo_pita
- Facebook: https://www.facebook.com/profile.php?id=61589854056244

## Archivos y continuidad

- [README](../README.md): resumen, enlaces sociales y estado general.
- [Requisitos](requisitos.md): comportamiento y restricciones del producto.
- [Arquitectura](arquitectura.md): componentes, alternativas técnicas y fuentes.
- [Plan y pruebas](plan.md): fases y criterios de aceptación.
- [Vocabulario](vocabulario.md): lista íntegra de términos entregados por el usuario.
- [AGENTS.md](../AGENTS.md): instrucciones de trabajo para futuras sesiones sobre el repositorio.

## Avances de fase 1 — 25 de noviembre de 2026

- Usuario autoriza iniciar la implementación, elige **GPL-3.0** (registrada como GPL-3.0-only) y **grabaciones propias** para las pruebas. Se conserva la planificación original como historial; la licencia ya no está pendiente.
- Base instalable `src/pitranscriptor`, comandos de versión/diagnóstico, Python 3.12.16 aislado, uv 0.13.10, dependencias directas y transitivas bloqueadas. Qt Essentials y reconocimiento son extras; no se descargan modelos.
- Verificado localmente en Windows 11 x86-64 con Ryzen 7 7445HS: dos pruebas de CLI aprobadas, Ruff aprobado, etiqueta Qt renderizada offscreen, importación de faster-whisper y tipos CPU `float32`, `int8`, `int8_float32` informados por CTranslate2. Dos construcciones consecutivas producen los mismos hashes de wheel y sdist.
- El equipo informa Radeon 740M y RTX 3050 Laptop; no se ejecutó reconocimiento ni cómputo GPU. `ffmpeg` y `ffprobe` no están en PATH. No se probaron Windows 10, Linux gráfico, Vega 8 ni precisión.
- CI configurado para Windows y Ubuntu 22.04/24.04; configurar un job no equivale a haberlo aprobado. [Desarrollo](desarrollo.md) documenta comandos y límites; [licencias](licencias.md) registra revisión inicial y obligaciones pendientes antes de distribuir.
- Primera ejecución de CI del commit `29abc05`: Windows aprobado; Ubuntu 22.04/24.04 completan pruebas base y construcción pero fallan al importar Qt por falta de `libEGL.so.1`. Se agregan bibliotecas nativas de Qt al entorno de CI y a las instrucciones Linux; repetir la ejecución para verificar la corrección.
- La [ejecución del ajuste `d56e2ee`](https://github.com/Pyyta/Pitranscriptor/actions/runs/45683162824) aprueba los tres jobs (Windows, Ubuntu 22.04 y Ubuntu 24.04), incluyendo Qt offscreen y tipos de CPU. Esto verifica la base en runners, no reconocimiento ni sesiones gráficas reales.
- Instalación y arranque del wheel comprobados en un entorno limpio local; paquetes inspeccionados sin medios ni directorios privados y con LICENSE/NOTICE. La comprobación se integra al script de construcción repetible.
- Nueve guiones públicos cubren el vocabulario completo, mezcla español-inglés, inglés, muletillas, dos voces y silencio. Plantilla con permisos/revisión en `false` y validador local de JSON, rutas, formato WAV, duración y truncamiento. No hay grabaciones ni referencias reales: no se atribuyen resultados de precisión a estos guiones. Véase [preparación de grabaciones](pruebas-reconocimiento.md).
- Validación local tras añadir el corpus: 25 pruebas aprobadas y 1 omitida porque Windows no permite crear enlaces simbólicos en este entorno; el caso queda habilitado en Linux. Ruff y compilación repetible aprobados. Las pruebas usan WAV sintéticos temporales, no voces ni datos personales.
- A petición del usuario se crean/verifican las carpetas locales de originales, audio del corpus, guiones, resultados, modelos y exportaciones. Se conservó el manifiesto existente y se prepararon nueve guiones `.txt` locales sin sobrescribir archivos. Todas esas rutas están ignoradas por Git; solo se publica su documentación. Siguiente paso: grabar el guion Linux y dejar el original en `data/local/originals/` para preparar y revisar la primera muestra.

El siguiente trabajo es preparar las muestras propias autorizadas y validar reconocimiento español-inglés, vocabulario y hardware disponible; después implementar el núcleo de edición y exportación según el plan. Siguen abiertos proveedor conectado, modelos predeterminados, formatos finales de instalación Linux y la revisión completa de binarios a redistribuir.

## Incorporación de las primeras grabaciones — 25 de noviembre de 2026

- El usuario entrega la primera grabación y autoriza usar sus grabaciones técnicas de una carpeta externa para pruebas locales. Rutas, nombres, inventario y hashes de esos medios permanecen solo en archivos ignorados; no se autoriza publicar los audios ni enviarlos a servicios.
- Se inventarían 38 WAV adicionales, uno de más de cinco minutos. Se preparan cuatro copias PCM16 mono a 16 kHz (primera muestra y tres técnicas), comprobando que los hashes de los originales no cambian. El archivo largo se excluye, sin recortarlo ni modificarlo.
- Nuevo comando `prepare-audio`, con prevención de sobrescritura y limpieza de copias fallidas. Al probar reconocimiento real se descubre que PyAV 19.0.2 es incompatible con faster-whisper 1.2.1; se fija PyAV 18.1.1 y se añade una prueba de decodificación con el motor, habilitada en CI con los extras.
- Modelo de investigación Whisper small multilingüe, revisión exacta en [licencias](licencias.md), cargado localmente en CPU int8. Se generan borradores con y sin pistas de vocabulario, con tiempos por palabra. No se sube audio; la inferencia usa archivos locales y el modo offline del cliente de modelos. No equivale a una prueba de aislamiento de red del sistema ni a evaluar GPU.
- El usuario confirma que el texto de referencia coincide palabra por palabra con su primera grabación. Se registra permiso/revisión y se valida el subconjunto local `reviewed.json` con una muestra. Los otros casos no se marcan como revisados; faltan referencias para cobertura representativa.
- Pruebas locales tras añadir preparación y regresión de decodificación: 32 aprobadas y una omitida por enlaces simbólicos no disponibles en este Windows; Ruff aprobado. No se usan voces privadas en las pruebas versionadas.
- [CI de `23d4512`](https://github.com/Pyyta/Pitranscriptor/actions/runs/45696024466) aprobado en Windows y Ubuntu 22.04/24.04, incluidas las pruebas opcionales de conversión y decodificación con faster-whisper.
- Primer ensayo puntuado tras la confirmación del usuario: una muestra de 39 palabras, modelo small en CPU int8, sin pistas y con los 16 términos esperados. WER 25,64 % frente a 0 % bajo normalización explícita, 8/16 frente a 16/16 términos; alrededor de seis segundos por condición. Alcance y límites en [pruebas de reconocimiento](pruebas-reconocimiento.md): no generalizar el resultado de una muestra guionada ni dar por seleccionado el modelo definitivo.
- Módulo de métricas WER/CER y cobertura de términos con pruebas de silencios, inserciones, frases completas y normalización; 39 pruebas locales aprobadas y una omitida por enlaces simbólicos, Ruff aprobado. Informes completos, textos de referencia e hipótesis y audios permanecen fuera de Git.
- El usuario aporta cuatro correcciones de fragmentos en dos referencias adicionales y confirma que son todos los cambios de las tres muestras, incluida la tercera sin cambios. Se aplican solo a las referencias locales, conservando los borradores originales del motor y copias previas. Las cuatro referencias quedan revisadas y el corpus validado suma 322,716 segundos y 951 palabras. Los demás casos previstos se conservan pendientes; no se modifica el vocabulario global con reemplazos automáticos.
- La línea base sin pistas del modelo small registra 20 errores de palabras sobre 951 (WER ponderado 2,10 %) en este conjunto. Tres referencias partieron de borradores de ese mismo modelo corregidos y confirmados por el usuario: el resultado depende de esa revisión y no mide generalización ni selecciona el modelo definitivo. Detalles agregados en [pruebas de reconocimiento](pruebas-reconocimiento.md); transcripciones, correcciones e informes completos permanecen locales.

## Núcleo de subtítulos

- El usuario pide continuar todas las tareas autorizadas sin solicitar decisiones rutinarias. El núcleo usa el modelo instalado mediante faster-whisper en CPU, mantiene el límite de siete palabras y guarda tiempos, estilos independientes y referencia al medio en un JSON portable. La copia local de la primera grabación generó doce fragmentos y se exportó en SRT y WebVTT. El medio y las exportaciones se mantienen en local.
- Editor de escritorio disponible con video, forma de onda, estilos por fragmento, presets, operaciones de edición, tiempos por palabra, deshacer y rehacer. Se comprobó reproducción vertical, selección, estilo independiente y recuperación de cambios en Windows. Las etiquetas del editor se ofrecen en español e inglés. La asignación de hablantes es manual y la salida de texto seguirá el estándar correspondiente.

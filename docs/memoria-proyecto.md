# Memoria del proyecto: Pitranscriptor

Última consolidación: 25 de noviembre de 2026. Este documento resume las decisiones de la conversación y enlaza los archivos del repositorio; no es una transcripción literal. Las indicaciones posteriores del usuario prevalecen sobre esta memoria.

## Identidad y estado

- **Nombre:** Pitranscriptor. **Autor y marca:** sudo_pita.
- **Repositorio público:** https://github.com/Pyyta/Pitranscriptor. Rama inicial `main`; remoto `origin`.
- **Ubicación inicial del proyecto:** `C:\Users\danyp\Documents\ChatGPT\New project`. La ubicación puede cambiar si se clona o se usa otro entorno; el repositorio es la referencia portable.
- **Estado al redactar:** requisitos y planificación documentados. Commit inicial `bfdd8ce` (`docs: define Pitranscriptor requirements and architecture`) publicado. No hay aplicación, instaladores, modelos integrados ni compatibilidad probada.
- **Alcance autorizado hasta ahora:** el usuario pidió explícitamente planificar, crear el repositorio e idear el proyecto, tras haber pedido no programar todavía. No debe interpretarse que ya se implementó el producto. Nuevas peticiones explícitas del usuario pueden autorizar implementación.
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

Python/PySide6 para escritorio, FFmpeg/ffprobe para medios y faster-whisper con modelos multilingües para investigación inicial. Estas tecnologías son candidatas, no garantías ni implementación existente. Evaluar precisión y coste de CPU/GPU con muestras reales antes de seleccionarlas. Vega 8 no estaba entre las GPU AMD de los binarios ROCm de CTranslate2 consultados al planificar; tratar CPU como alternativa y volver a verificar la documentación y el hardware en el momento de implementar. Separar proveedores de transcripción, dominio, editor, persistencia y exportación. Véase [arquitectura.md](arquitectura.md).

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

El siguiente trabajo de desarrollo propuesto es validar el reconocimiento con muestras autorizadas de español-inglés, el vocabulario y hardware disponible; después implementar iterativamente el núcleo de edición y exportación según el plan. No se han seleccionado proveedor conectado, licencia del proyecto, formatos definitivos de instalación en Linux ni versiones finales de modelos/dependencias. Registrar nuevas decisiones y resultados verificables aquí o en el documento especializado correspondiente.

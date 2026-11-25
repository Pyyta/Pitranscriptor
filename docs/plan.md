# Plan de desarrollo y validación

## Etapas

1. **Preparación:** definir licencia, matriz mínima de sistemas, versiones de dependencias, estructura del repositorio y método reproducible de compilación. Preparar un pequeño conjunto de audios de prueba con permiso de uso y transcripciones revisadas.
2. **Prueba de precisión:** comparar motores/modelos multilingües locales con español e inglés mezclados y vocabulario tecnológico, en CPU y NVIDIA disponible. Medir errores de términos, errores de transcripción, tiempo y memoria. Probar pistas de vocabulario frente a una línea base para detectar términos inventados. Evaluar opción conectada gratuita y viable por separado.
3. **Núcleo de subtítulos:** extracción de audio, marcas por palabra, fragmentación, límite de siete palabras, edición de texto, persistencia y SRT/VTT. Asegurar que no se pierdan palabras entre fragmentos.
4. **Editor:** importar video, vista previa, línea de tiempo, forma de onda, cambios por fragmento, división/unión, deshacer/rehacer y corrección de tiempos. Probar sincronía y preservación al guardar/reabrir.
5. **Estilos:** presets propios, formato por fragmento, resaltado por palabra y animaciones; comparar imágenes de vista previa y exportación.
6. **Exportación:** MP4/MOV según códecs, perfiles, dimensiones, audio, avance y manejo de sobrescritura. Probar videos verticales y horizontales y archivos de hasta cinco minutos.
7. **Hablantes y robustez:** evaluación de diarización, corrección manual, modo sin conexión, errores, cancelación y accesibilidad.
8. **Distribución:** instalador Windows y distribución Linux, dependencias y modelos, revisión de licencias, CI y pruebas de instalación limpia en los sistemas objetivo. Documentar lo realmente compatible.

## Estado de la fase 1

- [x] Licencia GPL-3.0-only elegida por el usuario.
- [x] Estructura Python instalable, versiones y dependencias bloqueadas.
- [x] Matriz inicial de Windows y Linux y comprobaciones CI.
- [x] Construcción repetible y prueba del wheel en entorno limpio.
- [x] Guiones de evaluación, manifiesto local y validación de audios y referencias.
- [x] Incorporar un conjunto inicial de cuatro grabaciones propias con permiso y referencias corregidas/confirmadas por el usuario.

La fase 1 dispone de la preparación técnica y un conjunto inicial validado de cuatro referencias revisadas. La ampliación de condiciones e idiomas y la comparación de modelos corresponden a fase 2. Evidencia y decisiones en la [memoria](memoria-proyecto.md); procedimiento en [pruebas de reconocimiento](pruebas-reconocimiento.md).

La primera ronda de fase 2 compara tres modelos en CPU y dos en RTX 3050. Faltan referencias independientes y cobertura de más voces, inglés completo y ruido real. Las fases 3 a 6 tienen un prototipo integrado con transcripción, edición de fragmentos, estilos, proyectos y exportación de video y texto. En fase 7 se incorporaron revisión de posibles muletillas y hablantes manuales. La diarización y el modo conectado siguen en evaluación. En fase 8 hay compilaciones de prueba para Windows y Ubuntu. Quedan la verificación de escritorio en más sistemas y la revisión de redistribución antes de publicar binarios.

## Pruebas de aceptación

- Transcribir muestras español/inglés con las palabras del vocabulario, comparándolas contra texto revisado; registrar resultados sin prometer reconocimiento perfecto.
- Probar audios con silencio, música moderada, muletillas y dos hablantes; verificar que el usuario pueda corregir el resultado y los colores.
- Comprobar cuatro palabras como objetivo, hasta siete cuando sea apropiado, ninguna pérdida de palabras y ningún fragmento que supere siete.
- Corregir una palabra; cambiar tamaño y posición de un solo fragmento; guardar, cerrar y reabrir sin alterar otros fragmentos.
- Verificar resaltado sincronizado, división/unión, edición temporal, deshacer/rehacer y concordancia entre vista previa y exportación.
- Abrir y exportar muestras habituales, verificar duración, orientación, resolución, cuadros por segundo y audio, además de SRT/VTT legibles.
- Probar sin conexión con modelo instalado, modelo ausente y reanudación; validar cancelación, falta de espacio y archivo de origen movido.
- Ejecutar pruebas reales en Windows 10/11 y Linux, CPU Ryzen, NVIDIA RTX 3050 y equipo con Vega 8 cuando estén disponibles. Registrar qué se probó realmente y los límites encontrados.

## Git y GitHub

Usar commits específicos y claros, agrupando cambios relacionados. Subir cada commit al repositorio remoto cuando se disponga de acceso y red. No incluir videos personales, audios, modelos pesados, secretos, cachés ni archivos temporales en Git. La visibilidad y la licencia deben quedar claras antes de distribuir.

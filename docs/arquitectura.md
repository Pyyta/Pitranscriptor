# Arquitectura propuesta

Estas son decisiones iniciales, no compatibilidades ya comprobadas. Se definirán versiones exactas tras prototipos y pruebas en Windows y Linux.

La fase 1 incorpora una base Python de preparación con versiones de evaluación fijadas en `pyproject.toml`/`uv.lock`, extras independientes para Qt Essentials y reconocimiento, y scripts de construcción. Véase [desarrollo](desarrollo.md) para comandos, matriz y límites reales. Los componentes del editor y de exportación descritos abajo siguen planificados.

## Tecnología candidata

- **Interfaz:** Python y PySide6/Qt, con reproducción de video y componentes propios para vista previa y línea de tiempo. Diseñar la escena de subtítulos compartida entre previsualización y exportación; verificar fidelidad entre ambas.
- **Audio y video:** FFmpeg/ffprobe para inspección, extracción, representación y exportación. Seleccionar códecs por capacidades reales y verificar licencias de la compilación distribuida.
- **Reconocimiento local:** evaluar faster-whisper con modelos Whisper multilingües y marcas de tiempo por palabra. Comparar modelos y cuantizaciones con audios representativos antes de fijar el predeterminado. El vocabulario puede orientar, pero no garantiza la corrección ni proporciona alternativas fiables por sí solo.
- **Hablantes:** evaluar diarización opcional, coste de hardware y condiciones de acceso de modelos. La corrección manual debe existir incluso si falla la identificación automática.
- **En línea:** interfaz de proveedor separada. No se ha elegido un servicio gratuito sostenible ni se enviará audio automáticamente. También se puede utilizar internet solo para descargar modelos sin subir audio; esto no mejora por sí mismo el reconocimiento.
- **Empaquetado:** investigar instalador Windows y formatos Linux (por ejemplo AppImage y/o paquetes nativos) según pruebas. Instalar la aplicación y facilitar descarga o inclusión de modelos conforme a tamaño y licencias; no exigir clonar el repositorio a usuarios finales.

## Hardware

CPU como ruta funcional básica en equipos compatibles; aceleración NVIDIA cuando se detecten GPU, controlador y bibliotecas apropiadas. RTX 3050 debe probarse con su VRAM real y un modelo que quepa. CPU Ryzen debe probarse directamente. Vega 8 no figura entre las GPU AMD soportadas por los binarios ROCm de CTranslate2 documentados: no prometer aceleración y recurrir a CPU. No existe garantía de que todos los equipos puedan procesar cinco minutos dentro de un plazo concreto. No hay motivo previsto para modificar el kernel Linux; el soporte depende de librerías, arquitectura, controladores y pruebas.

## Componentes

1. **Interfaz y traducciones:** navegación, ajustes, crédito y accesibilidad.
2. **Medios:** metadatos, reproducción, forma de onda y gestión de archivos.
3. **Trabajos:** tareas en segundo plano, progreso por etapas, cancelación y errores.
4. **Transcripción:** proveedores locales y opcionales conectados, selección de modelo, pistas de vocabulario y marcas de tiempo.
5. **Fragmentación:** pausas, puntuación, legibilidad, objetivo configurable y límite rígido de siete palabras.
6. **Editor:** documento, selección, operaciones reversibles, línea de tiempo y vista previa.
7. **Render y exportación:** composición compartida, SRT/VTT y generación de video.
8. **Persistencia:** proyecto versionado, presets y preferencias locales; rutas de medios recuperables.

## Modelo de proyecto propuesto

Archivo de proyecto con versión de esquema; video referenciado, metadatos y duración; hablantes y colores; palabras con texto y tiempos; fragmentos con referencia a palabras y estilo individual; estilo base, animación, presets y ajustes. La edición de texto debe resolver cambios de cantidad de palabras sin inventar precisión temporal: conservar, reajustar o pedir corrección de los tiempos afectados. Guardado atómico y migraciones de esquema.

## Árbol previsto

```text
Pitranscriptor/
├── README.md
├── docs/                 # requisitos, arquitectura y plan
├── src/pitranscriptor/   # interfaz, dominio, transcripción y exportación
├── tests/                # pruebas representativas
├── resources/            # traducciones, tema, recursos con licencia
├── packaging/            # construcción de instaladores
└── scripts/              # tareas de desarrollo
```

`src/pitranscriptor`, `tests` y `scripts` ya existen en fase 1; `resources` y `packaging` se crearán cuando se necesiten. El resto del árbol describe la intención y puede cambiar con los prototipos.

## Referencias primarias

- [faster-whisper: marcas de tiempo, VAD y uso](https://github.com/SYSTRAN/faster-whisper)
- [CTranslate2: soporte de hardware](https://opennmt.net/CTranslate2/hardware_support.html)
- [Whisper: modelos y requisitos aproximados](https://github.com/openai/whisper/blob/main/README.md)
- [PySide: licencias](https://doc.qt.io/qtforpython-6/licenses.html) y [despliegue](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html)
- [FFmpeg: licencia y distribución](https://ffmpeg.org/legal.html)

# Entorno de desarrollo y validación

## Base de la fase 1

Python **3.12.16** (`.python-version`) y uv **0.13.10**. Se limita temporalmente el paquete a Python 3.12 para reducir variables al evaluar bibliotecas nativas; no exige cambiar el Python del sistema. La primera instalación descarga el intérprete si falta, herramientas y paquetes, nunca modelos de reconocimiento. Los usuarios finales recibirán instaladores en una fase posterior.

El núcleo de preparación usa solo la biblioteca estándar. Extras separados:

| Grupo | Dependencias directas fijadas | Propósito actual |
| --- | --- | --- |
| `dev` | pytest 9.2.0, Ruff 0.17.6, Hatchling 1.33.0 | Pruebas, revisión y construcción Python |
| `desktop` | PySide6-Essentials y PySide6-Addons 6.12.0 | Editor Qt Widgets y reproducción Qt Multimedia |
| `research` | faster-whisper 1.2.1, CTranslate2 4.9.1, PyAV 18.1.1 | Preparar y decodificar audio para evaluar el motor local |

`uv.lock` fija también versiones transitivas y hashes. No editarlo a mano. `uv lock` lo actualiza después de un cambio deliberado y `uv sync --locked` rechaza un archivo desactualizado. El editor usa el extra `desktop` para reproducción y `research` para audio y reconocimiento.

PyAV se fija por compatibilidad: faster-whisper 1.2.1 pasa `metadata_errors` a `av.open`, argumento retirado en PyAV 19. Se verificó el fallo y se eligió 18.1.1 con wheels para Windows/Linux. [Incidencia del motor](https://github.com/SYSTRAN/faster-whisper/issues/1589). Las pruebas opcionales ahora decodifican WAV con el motor además de importar bibliotecas; no requieren modelos.

## Preparar y ejecutar

Instalar [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.10; una opción con Python existente es `python -m pip install uv==0.13.10`. No hace falta activar el entorno:

```console
uv sync --locked
uv run --frozen pitranscriptor --version
uv run --frozen pitranscriptor doctor --json
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest
```

El diagnóstico informa presencia de paquetes y de `ffmpeg`/`ffprobe` en PATH; no certifica funcionamiento, no carga modelos, no transmite audio ni selecciona GPU.

Para las comprobaciones opcionales:

En Ubuntu, instalar primero las bibliotecas nativas de Qt (también necesarias en runners sin escritorio):

```console
sudo apt-get update
sudo apt-get install --no-install-recommends -y libegl1 libopengl0 libgl1 libxkbcommon0
```

Después, en Windows o Linux:

```console
uv sync --locked --all-extras
uv run --frozen --all-extras python scripts/check_runtime.py
```

La prueba renderiza una etiqueta Qt sin ventana visible, importa faster-whisper y consulta tipos de CPU en CTranslate2. No realiza reconocimiento ni prueba GPU, códecs, reproducción o una sesión X11/Wayland. No descarga pesos. Para trabajar sin red, preparar antes intérprete y dependencias; `uv run --offline --frozen` evita consultas de uv, pero el reconocimiento offline todavía debe probarse en fase 2.

## Construir de forma repetible

Con el grupo `dev` sincronizado:

```console
uv run --frozen python scripts/verify_build.py
uv build --no-build-isolation
```

El primer comando construye dos veces con `SOURCE_DATE_EPOCH` fijo y compara SHA256 de wheel y sdist. Comprueba también avisos de licencia y ausencia de medios y directorios privados en ambos paquetes. Usa Hatchling y sus dependencias del entorno bloqueado, sin resolver herramientas nuevas. El segundo deja los paquetes en `dist/` (ignorado). Son paquetes Python de desarrollo, no instaladores. No publica en PyPI ni GitHub Releases. La igualdad se comprueba dentro del mismo entorno; no implica igualdad entre plataformas o futuros instaladores.

Para preparar audios propios, seguir [las instrucciones del corpus](pruebas-reconocimiento.md) y usar `pitranscriptor validate-corpus`. El validador funciona sin los extras; los datos reales se guardan en `data/local/`.

`pitranscriptor prepare-audio ORIGEN DESTINO.wav` utiliza el extra `research` para crear una copia PCM16 mono a 16 kHz. Rechaza sobrescribir, usar el original como salida, archivos sin una única pista o de más de cinco minutos. Elimina copias incompletas si falla y verifica que el hash del original no cambió.

Con un modelo multilingüe CTranslate2 ya instalado en `models/faster-whisper-small`, el núcleo se puede ejecutar desde la raíz del repositorio:

```console
uv run --frozen --extra research pitranscriptor transcribe video.mp4 outputs/video.pitranscriptor --model models/faster-whisper-small --language es
uv run --frozen pitranscriptor export-subtitles outputs/video.pitranscriptor outputs/video.srt
uv run --frozen pitranscriptor export-subtitles outputs/video.pitranscriptor outputs/video.vtt
```

Los tiempos por palabra son estimaciones del modelo. Si la cantidad de palabras cambia al editar un fragmento, se conservan los tiempos del fragmento y se retiran las marcas individuales para evitar atribuir precisión a palabras nuevas. La decodificación considera el desfase inicial de la primera pista de audio frente al video. El material con discontinuidades complejas requiere comprobación manual de sincronía.

Para abrir el editor, ejecutar `uv sync --locked --all-extras` y luego `uv run --frozen --all-extras pitranscriptor-desktop`. Elegir el video y seleccionar una carpeta de modelo instalado mediante **Modelo…**. Los fragmentos se pueden editar desde la lista, mover arrastrando en la vista previa pausada y guardar como proyecto. La línea de tiempo muestra forma de onda y admite búsqueda, zoom y velocidades de reproducción. Se puede cambiar el idioma desde el menú para el próximo inicio.

**Archivo → Descargar modelo Small** instala el modelo multilingüe en el directorio de datos de la aplicación. Con el modelo completo, la transcripción usa archivos locales. CPU es el modo inicial y **NVIDIA CUDA** se puede elegir cuando el proceso tiene acceso a las bibliotecas compatibles. La prueba local en Windows usó CUDA Runtime 12.9.79, cuBLAS 12.9.2.10 y cuDNN 9.28.1.4 en un directorio aislado con sus carpetas `bin` en `PATH`. Los demás equipos pueden usar CPU sin esos componentes.

**Archivo → Exportar video** aplica en MP4 o MOV la misma composición de la vista previa. La exportación H.264 permite ajustar calidad, altura máxima y cuadros por segundo. Conservar el valor original mantiene los tiempos de los cuadros cuando el archivo proporciona marcas temporales. La resolución queda limitada a la del original y se redondea a dimensiones pares para H.264. La primera pista AAC se copia. Para otras pistas se usa AAC con un máximo de dos canales y la aplicación indica la conversión al terminar. Se comprobó rotación de metadatos, orientación vertical, recodificación de PCM, copia AAC y cancelación con clips de prueba. Para fuentes HDR, códecs alternativos y archivos con varias pistas, quedan pendientes pruebas de conservación de características.

## Construir un instalador de prueba

En Windows o Linux x86-64, ejecutar desde la raíz del proyecto:

```console
uv sync --locked --all-extras --group package
uv run --frozen --all-extras --group package python scripts/build_desktop.py
```

En Windows, `dist/desktop/Pitranscriptor-Setup.exe` instala en una carpeta nueva del usuario y añade un acceso al menú Inicio al usar la interfaz. La compilación de prueba carece de firma digital. En Linux, extraer `dist/desktop/Pitranscriptor-linux-x86_64.tar.gz` y ejecutar `sh install-linux.sh` desde el directorio extraído. Para una instalación de prueba en otra carpeta, pasarla como argumento. Las compilaciones de CI se realizan en Windows y Ubuntu 22.04. Los binarios quedan en el entorno de compilación y los modelos se descargan desde la aplicación.

## Matriz inicial, objetivos y evidencia

| Plataforma x86-64 | Ruta prevista | Validación |
| --- | --- | --- |
| Windows 11 | Python 3.12, CPU; NVIDIA opcional después | Equipo local disponible; resultados en la memoria |
| Windows 10 | Python 3.12, CPU | Pendiente de equipo real; no cubierto por `windows-latest` |
| Ubuntu 22.04 y 24.04 | Python 3.12, CPU | Jobs configurados en CI; estado real en GitHub Actions |
| Otras distribuciones Linux | CPU, dependencias nativas por verificar | Pendiente; no se afirma soporte universal |
| X11 y Wayland | Interfaz Qt | Pendiente de pruebas gráficas reales |

Los wheels Qt seleccionados para x86-64 Linux indican `manylinux_2_34`: glibc 2.34 es un piso de ese componente, no un certificado de funcionamiento de todas las dependencias. Ubuntu 22.04/24.04 son objetivos iniciales. Windows 10 continúa como requisito; verificar versión mínima y dependencias del instalador antes de anunciar compatibilidad. Los binarios de CPU de [CTranslate2](https://opennmt.net/CTranslate2/hardware_support.html) requieren al menos SSE 4.1 en x86-64. No se declara aceleración Vega 8 ni NVIDIA solo por detectar una tarjeta.

CI (`.github/workflows/ci.yml`) comprueba formato, pruebas, diagnóstico, compilación repetible, instalación del wheel en entorno limpio y smoke test opcional. No usa grabaciones privadas, modelos ni credenciales de proveedores. Una ejecución verde valida esa base en el runner, no todo el producto.

## Resultados

Los resultados verificados y limitaciones se mantienen en la [memoria](memoria-proyecto.md); las ejecuciones de CI quedan en [GitHub Actions](https://github.com/Pyyta/Pitranscriptor/actions).

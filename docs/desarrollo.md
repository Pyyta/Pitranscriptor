# Entorno de desarrollo y validación

## Base de la fase 1

Python **3.12.16** (`.python-version`) y uv **0.13.10**. Se limita temporalmente el paquete a Python 3.12 para reducir variables al evaluar bibliotecas nativas; no exige cambiar el Python del sistema. La primera instalación descarga el intérprete si falta, herramientas y paquetes, nunca modelos de reconocimiento. Los usuarios finales recibirán instaladores en una fase posterior.

El núcleo de preparación usa solo la biblioteca estándar. Extras separados:

| Grupo | Dependencias directas fijadas | Propósito actual |
| --- | --- | --- |
| `dev` | pytest 9.2.0, Ruff 0.17.6, Hatchling 1.33.0 | Pruebas, revisión y construcción Python |
| `desktop` | PySide6-Essentials 6.12.0 | Evaluar Qt Widgets sin instalar módulos no utilizados |
| `research` | faster-whisper 1.2.1, CTranslate2 4.9.1 | Preparar la evaluación del motor local |

`uv.lock` fija también versiones transitivas y hashes. No editarlo a mano. `uv lock` lo actualiza después de un cambio deliberado; `uv sync --locked` rechaza un archivo desactualizado. El extra `desktop` no contiene aún QtMultimedia; se revisará antes de implementar reproducción. No se ha seleccionado un modelo predeterminado.

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

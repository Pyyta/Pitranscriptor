# Licencia y revisión de redistribución

Decisión del autor del 25 de noviembre de 2026: código propio bajo **GPL-3.0-only**. El texto completo está en [LICENSE](../LICENSE) y el aviso del proyecto en [NOTICE](../NOTICE). Sustituye el estado anterior de licencia pendiente. Audio, modelos y componentes externos conservan sus licencias.

## Componentes evaluados

| Componente | Fuente primaria y condiciones | Decisión de esta fase |
| --- | --- | --- |
| Python | [PSF y avisos de terceros](https://docs.python.org/3/license.html) | Intérprete de desarrollo; revisar avisos de la distribución concreta al empaquetar |
| Qt / PySide6 | [LGPL/GPL y componentes](https://doc.qt.io/qtforpython-6/licenses.html) | Extra de evaluación; revisar módulos y binarios exactos antes de distribuir |
| faster-whisper | [MIT](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE) | Extra de investigación; conservar licencia y copyright |
| CTranslate2 | [MIT y bibliotecas nativas](https://github.com/OpenNMT/CTranslate2/blob/master/LICENSE) | Evaluar CPU; revisar bibliotecas incluidas en los wheels seleccionados |
| Whisper | [MIT para código y pesos publicados por OpenAI](https://github.com/openai/whisper#license) | No se incluyen pesos; comprobar también la ficha de cada conversión elegida |
| Conversión Whisper small de investigación | [Ficha MIT de Systran](https://huggingface.co/Systran/faster-whisper-small) | Descargada solo en `models/` local, revisión `536b0662742c02347bc0e980a01041f333bce120`; se conserva su ficha y procedencia. No se redistribuye ni se selecciona como modelo definitivo |
| PyAV (transitivo) | [BSD y enlace a FFmpeg](https://github.com/PyAV-Org/PyAV) | La licencia del wrapper no cubre por sí sola las bibliotecas enlazadas |
| FFmpeg / ffprobe | [LGPL o GPL según configuración, más terceros](https://ffmpeg.org/legal.html) | Ejecutables externos no incluidos; conservar fuentes, flags y avisos de la compilación elegida |
| uv | [MIT/Apache-2.0 y terceros](https://github.com/astral-sh/uv) | Herramienta de desarrollo; no incorporada al producto final |
| Hatchling, pytest, Ruff y transitivas | Metadatos de las versiones fijadas en `uv.lock` y sus licencias | Herramientas de desarrollo; no incluirlas por defecto en instaladores |
| Tipografías y recursos visuales | Depende del archivo y procedencia | No se agrega ninguna fuente ni recurso de terceros |

Esta es una revisión inicial, no una autorización completa de futuros instaladores. `uv.lock` fija las dependencias transitivas; antes de distribuir se inventariarán **todos** los paquetes efectivos, bibliotecas nativas, códecs y modelos, con textos, avisos y fuentes de sus versiones. Revisar especialmente FFmpeg incluido en PyAV, no solo un posible `ffmpeg.exe`. No redistribuir combinaciones marcadas `nonfree`. La licencia del proyecto no resuelve por sí sola derechos sobre códecs o medios.

## Grabaciones de pruebas

El usuario eligió grabaciones propias. Audios y transcripciones revisadas permanecerán en `data/local/`, ignorado por Git. Registrar permiso de cada muestra y de todas las voces; un audio propio puede contener música o voces ajenas con otros derechos. El permiso para pruebas locales no autoriza publicarlo ni enviarlo a proveedores. Los guiones públicos son texto original del proyecto bajo GPL-3.0-only.

# Preparación de grabaciones propias

El usuario eligió grabaciones propias en lugar de un corpus público. Ya hay copias locales autorizadas y primeros borradores experimentales de reconocimiento, fuera del repositorio. La primera referencia fue confirmada palabra por palabra por el usuario. Los textos de [la plantilla](../data/templates/corpus.example.json) siguen siendo **guiones originales** y no se consideran revisados automáticamente al grabarlos.

## Carpetas locales preparadas

En el equipo de desarrollo ya se crearon estas rutas dentro del repositorio:

| Ruta | Uso |
| --- | --- |
| `data/local/originals/` | Grabaciones originales, conservando su formato |
| `data/local/corpus/audio/` | Copias WAV preparadas para la evaluación |
| `data/local/corpus/guiones/` | Copias de los nueve guiones en archivos `.txt` para leer al grabar |
| `reports/local/` | Mediciones y resultados privados |
| `models/` | Modelos locales cuando se seleccionen y descarguen |
| `outputs/` | Exportaciones locales cuando se implemente esa función |

El manifiesto local está en `data/local/corpus/manifest.json`; se conserva sin sobrescribirlo. Estas carpetas están ignoradas por Git y no se incluyen en el repositorio remoto. Git no recrea carpetas locales vacías al clonar; en otro equipo deben prepararse de nuevo.

Las cuatro grabaciones están preparadas y sus referencias fueron revisadas por el usuario, con cuatro correcciones en dos muestras adicionales y confirmación de que no hay más cambios. El subconjunto local `data/local/corpus/reviewed.json` contiene las cuatro muestras; `manifest.json` conserva también los casos aún pendientes. Los borradores originales del motor se conservan sin aplicarles las correcciones de referencia. No hace falta grabar más antes de aprovechar este conjunto inicial.

## Preparar una copia sin modificar el original

Con el extra `research` instalado, sustituir los nombres del ejemplo por los archivos reales:

```console
uv run --frozen --extra research pitranscriptor prepare-audio data/local/originals/mi-grabacion.wav data/local/corpus/audio/mi-muestra.wav
```

La salida será WAV PCM de 16 bits, mono y 16000 Hz. El comando no sobrescribe, no recorta audios de más de cinco minutos y verifica el hash del original. PyAV usa sus bibliotecas FFmpeg; esta preparación no requiere un `ffmpeg` externo en PATH. No aplica eliminación de ruido, silencios ni muletillas.

## Preparar el conjunto local

1. Crear `data/local/corpus/` y copiar allí la plantilla como `manifest.json`. Copiar el archivo no concede permisos ni confirma revisión: sus dos declaraciones empiezan en `false`.
2. Grabar los nueve casos en `data/local/corpus/audio/` con los nombres de la plantilla. Para dos voces, contar con permiso de ambas; si no está disponible, quitar ese caso del manifiesto y anotar que falta esa cobertura.
3. Usar WAV PCM de 16 bits, mono, 16000 Hz, hasta 300 segundos por archivo. Mantener originales de mayor calidad fuera de Git si hace falta convertirlos. No basta con cambiar la extensión a `.wav`.
4. Escuchar cada grabación y corregir `reference_text` para que refleje **exactamente lo dicho**, conservando cambios de idioma y muletillas. Después marcar `reference_reviewed: true`. En el caso de silencio, grabar unos segundos sin voz y dejar el texto vacío.
5. Confirmar `permission_for_local_evaluation: true` solo cuando exista permiso para probar localmente todas las voces y sonidos de esa muestra. Esto no concede publicación ni envío a terceros.
6. Ejecutar el validador:

```console
uv run --frozen pitranscriptor validate-corpus data/local/corpus/manifest.json
```

El código de salida es 0 si valida y 1 si hay errores. Comprueba versión de manifiesto, identificadores, declaraciones, referencias, etiquetas, rutas contenidas en su carpeta (también enlaces simbólicos), WAV, formato, duración y datos truncados. No modifica archivos, no carga modelos y no verifica por sí mismo que un permiso sea auténtico o que la transcripción sea correcta.

El validador acepta conjuntos parciales para poder preparar una muestra a la vez. Un conjunto válido de un solo audio **no** equivale a cubrir todos los requisitos. Los guiones Linux, IA, gráficos, datos y redes incluyen todos los términos del [vocabulario inicial](vocabulario.md); hay casos adicionales de inglés, muletillas, dos voces y silencio. Opcionalmente añadir un caso con música moderada propia o autorizada (`music`), documentando su procedencia localmente.

## Contrato del manifiesto, versión 1

- `schema_version`: entero 1; `samples`: lista no vacía.
- `id`: único, hasta 64 caracteres de letras minúsculas, números, `-` y `_`.
- `audio`: ruta relativa `.wav`, con `/`; sin rutas absolutas ni `..`; archivos únicos dentro de la carpeta del manifiesto.
- `reference_text`: texto revisado; vacío solo si `tags` contiene `silence`, que requiere ausencia de palabras.
- `tags`: una o más de `mixed`, `english`, `tech`, `clean`, `fillers`, `two-speakers`, `silence`, `music`.
- `terms`: lista opcional de términos esperados, sin sustitución automática.
- `permission_for_local_evaluation`, `reference_reviewed`: booleanos que deben ser `true` para validar.

## Evaluación prevista en fase 2

Comparar modelos multilingües en CPU, y NVIDIA solo si se puede verificar, con y sin pistas del vocabulario. Registrar modelo y revisión exactos, cuantización, equipo, configuración, tiempo, memoria y errores de términos junto con WER y CER. Conservar resultados sin normalizar y una política de normalización documentada; evaluar silencio por palabras inventadas (WER no está definida con referencia vacía). No eliminar muletillas antes de medir reconocimiento.

Los resultados privados y cualquier detalle de voces quedan en `reports/local/`. Publicar solo resúmenes revisados que no expongan audio, transcripciones personales o datos identificables. Hay cuatro referencias reales revisadas; aún faltan otras voces, inglés completo, silencio y más referencias para una evaluación representativa.

## Primer ensayo con referencia confirmada

El 25 de noviembre de 2026 se procesó una muestra de 20,957 segundos y 39 palabras con referencia confirmada por el usuario. Modelo de investigación: `Systran/faster-whisper-small`, revisión `536b0662742c02347bc0e980a01041f333bce120`; faster-whisper 1.2.1, CTranslate2 4.9.1 y PyAV 18.1.1; CPU Ryzen 7 7445HS, int8, 8 hilos. Configuración: español, transcribir sin traducir, beam 5, temperatura 0, VAD y tiempos por palabra, sin condicionar el texto al segmento anterior.

| Condición | WER | CER con espacios | Términos exactos | Tiempo de transcripción |
| --- | --- | --- | --- | --- |
| Sin pistas | 25,64 % | 6,09 % | 8/16 | 6,11 s |
| Con los 16 términos del guion como pista | 0 % | 0 % | 16/16 | 6,27 s |

Los tiempos excluyen descarga y carga inicial del modelo. Solo se midió una ejecución por condición, no una distribución de rendimiento. El 0 % corresponde a esta muestra guionada y a la normalización descrita abajo; **no demuestra precisión perfecta**, no evalúa generalización a nuevas grabaciones y no mide calidad de puntuación, tiempos o diarización. Las pistas incluían términos esperados de ese guion, por lo que falta probarlas frente a audios nuevos para detectar omisiones o palabras inventadas. Aún no se compararon otros modelos o GPU.

### Política de métricas

El módulo `pitranscriptor.evaluation` implementa Levenshtein, WER y CER: sustituciones + inserciones + eliminaciones, dividido por unidades de referencia. WER usa palabras; CER incluye los espacios de la cadena normalizada. Política `nfc-casefold-punctuation-to-space-v1`: normalización Unicode NFC, comparación sin mayúsculas/minúsculas, puntuación reemplazada por espacios y espacios colapsados; se conservan acentos. Se conservan también los textos originales en los informes privados.

Las tasas pueden superar el 100 % por inserciones. Con referencia vacía, la tasa es `null` y se informa el número de errores sin inventar un porcentaje. Los términos se cotejan por palabras/frases completas, sin contar subcadenas, y deben existir en la referencia revisada. Esto mide presencia exacta, no todas las ocurrencias ni variantes fonéticas.

Los borradores, textos, marcas por palabra, hashes y mediciones detalladas permanecen en `reports/local/`.

## Línea base ampliada tras revisión del usuario

Con las correcciones y la confirmación de revisión de las tres muestras adicionales, el conjunto validado contiene cuatro audios, 322,716 segundos y 951 palabras de referencia. Se puntúan los borradores originales sin pistas del mismo modelo small en CPU, conservando la política anterior:

| Muestra | Errores de palabras | Palabras de referencia | WER |
| --- | --- | --- | --- |
| Guion inicial | 10 | 39 | 25,64 % |
| Técnica A | 0 | 274 | 0 % |
| Técnica B | 3 | 285 | 1,05 % |
| Técnica C | 7 | 353 | 1,98 % |
| Conjunto ponderado por palabras | 20 | 951 | 2,10 % |

El conjunto se calcula sumando errores y palabras de referencia, no promediando porcentajes por archivo. Las tres referencias adicionales se originaron en borradores de este mismo motor y fueron revisadas/corregidas por el usuario; ese origen debe conservarse al interpretar los resultados. No equivalen a una transcripción independiente hecha desde cero. Esta línea base no valida otros modelos, voces, idiomas ni equipos y no convierte los errores corregidos en reglas automáticas del reconocedor.

## Comparación de modelos en las cuatro referencias

Se ejecutó `scripts/benchmark.py` con 322,716 s de audio y 951 palabras revisadas en Windows 11. Se mantuvo la misma configuración de reconocimiento de los ensayos anteriores. En la condición con pistas se pasó la lista completa de `docs/vocabulario.md`, igual para las cuatro muestras. La cobertura cuenta 20 pares de muestra y término de esa lista presentes en las referencias.

| Modelo y dispositivo | Pistas | WER | CER | Términos | Inferencia total | Memoria RAM pico |
| --- | --- | --- | --- | --- | --- | --- |
| Small, CPU | No | 2,10 % | 0,46 % | 12/20 | 94,2 s | 693 MiB |
| Small, CPU | Sí | 2,94 % | 1,00 % | 18/20 | 123,5 s | 692 MiB |
| Medium, CPU | No | 8,10 % | 4,36 % | 12/20 | 238,3 s | 1740 MiB |
| Medium, CPU | Sí | 5,47 % | 2,50 % | 19/20 | 323,3 s | 1740 MiB |
| Large-v3-turbo, CPU | No | 5,15 % | 1,91 % | 14/20 | 158,8 s | 1878 MiB |
| Large-v3-turbo, CPU | Sí | 5,47 % | 2,29 % | 18/20 | 151,9 s | 1878 MiB |
| Small, RTX 3050 Laptop | No | 4,52 % | 1,73 % | 12/20 | 53,9 s | 931 MiB |
| Large-v3-turbo, RTX 3050 Laptop | No | 5,57 % | 2,00 % | 12/20 | 54,5 s | 1980 MiB |

CPU usa `int8_float32` con ocho hilos y CUDA usa `int8_float16`. Se midió la memoria residente del proceso. Los tiempos son observaciones de una ejecución por condición con carga variable del equipo. En estas cuatro muestras, la comprobación literal no detectó términos del vocabulario fuera de la referencia. Esa métrica solo cubre la lista y estas grabaciones. La RTX 3050 de 4 GiB completó ambos ensayos después de cargar cuBLAS 12 y cuDNN 9 en un entorno local. La ruta CPU sirve como configuración inicial y las pistas quedan como opción. Las tres referencias derivadas de Small favorecen su similitud con el texto revisado y hacen provisional esta elección.

Revisiones probadas de [Medium](https://huggingface.co/Systran/faster-whisper-medium/tree/08e178d48790749d25932bbc082711ddcfdfbc4f) y [Large-v3-turbo](https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo/tree/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf). Los archivos `comparison-*.json` quedan en `reports/local/`.

## Prueba del modo mixto

En un clip sintético creado localmente con dos voces de Windows, el modo español omitió el pasaje en inglés y acumuló 20 errores sobre 33 palabras. El modo mixto dividió el audio por pausas, detectó el idioma en cada tramo y conservó ambos pasajes, con 2 errores sobre 33 palabras. El clip de inglés completo tuvo un error sobre 19 palabras en modo inglés. El modo mixto produjo cero fragmentos en una prueba de silencio. Esta prueba comprueba el cambio entre tramos separados por pausas. Queda por medir el cambio de idioma dentro de una misma frase con habla natural.

En la muestra natural inicial de 39 palabras, el modo mixto sin pistas produjo 14 errores y recuperó 6 de 16 términos. El modo español sin pistas dio 10 errores y 8 términos en esa muestra. El editor mantiene español como modo inicial y ofrece mixto para grabaciones que cambian de idioma entre tramos.

## Evaluación documental de una opción conectada

El 25 de noviembre de 2026 se revisaron dos servicios que publican opciones de transcripción multilingüe. Groq documenta una cuota gratuita y marcas temporales, pero sus condiciones de servicio exigen ser mayor de edad. Cloudflare Workers AI publica una cuota gratuita compartida y un modelo que acepta pistas y devuelve segmentos. Su integración requiere una cuenta y comprobar con una llamada autorizada la granularidad de los tiempos que entrega. [Transcripción de Groq](https://console.groq.com/docs/speech-to-text), [condiciones de Groq](https://console.groq.com/docs/legal/services-agreement), [cuota de Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/) y [modelo de Cloudflare](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/).

La evaluación se limitó a la documentación pública. La aplicación conserva como ruta disponible el reconocimiento local. Para considerar una integración, deben verificarse elegibilidad, consentimiento previo al envío, marcas por palabra, límites y precisión frente a la opción local.

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

La primera grabación ya está preparada y su referencia fue confirmada por el usuario. El subconjunto local `data/local/corpus/reviewed.json` contiene solo esa muestra; `manifest.json` conserva también los casos aún pendientes. Las otras tres copias técnicas seleccionadas siguen pendientes de referencias revisadas. No hace falta grabar más antes de aprovechar estas muestras.

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

Los resultados privados y cualquier detalle de voces quedan en `reports/local/`. Publicar solo resúmenes revisados que no expongan audio, transcripciones personales o datos identificables. Hay una referencia real revisada; aún faltan otras voces, inglés completo, silencio y más referencias para una evaluación representativa.

# Requisitos del producto

## Alcance

- Escritorio: Windows 10 o posterior y Linux; interfaz disponible en español e inglés. Probar tanto Wayland como X11 cuando el entorno lo permita.
- Un video a la vez, de hasta 5 minutos, vertical u horizontal. Admitir MP4, MOV, MKV, WebM y otros formatos habituales en la medida en que sus códecs estén disponibles; informar claramente cuando no se pueda abrir uno.
- Flujo: seleccionar video → transcribir → revisar y editar → exportar. Progreso y posibilidad de cancelar tareas largas sin bloquear la interfaz.
- Diseño inspirado en computación de los años 90, sobrio y legible, sin exceso de neón. Mostrar «Creado por sudo_pita» y los enlaces sociales documentados en el README.

## Transcripción

- Priorizar precisión en español con vocabulario inglés y cambiar a inglés cuando corresponda, sin traducir automáticamente. Usar el vocabulario inicial como pista y no como sustitución obligatoria; comprobar que no genere términos inventados.
- Modelos locales descargables y reutilizables sin conexión tras su instalación. Ofrecer un modo conectado solo si existe una integración gratuita viable: no presumir que la conexión mejora la precisión ni que un servicio gratuito no tiene límites. Antes de enviar audio a terceros, informar y solicitar consentimiento; la configuración concreta está pendiente.
- Detectar silencios y sugerir eliminación de muletillas, sin borrar palabras reales. Permitir corrección manual y deshacer.
- Ofrecer alternativas de palabras cuando un motor pueda producirlas o una estrategia validada las genere; no presentar conjeturas como certezas. Permitir revisar palabras dudosas.
- Identificar hablantes por colores cuando sea posible; permitir corrección manual. La asignación automática, especialmente con voces superpuestas, requiere validación y no está garantizada.
- Tiempos por palabra para animaciones y edición. Los tiempos automáticos y el reconocimiento están sujetos a revisión por el usuario.

## Fragmentación y aspecto

- Objetivo predeterminado: alrededor de 4 palabras. Ajustable, priorizando pausas y frases completas; se pueden mostrar 5, 6 o 7 si mejora la lectura, con máximo absoluto de **7 palabras** por fragmento. Si una frase es más larga, dividirla sin superar ese máximo.
- Por defecto, subtítulos en la parte inferior, con posición ajustable y referencias de zona segura. Soportar fuentes instaladas, tamaño, color, negrita, contorno, sombra, fondo, opacidad y alineación.
- Efectos seleccionables: entrada y salida, aparición por palabra y resaltado de la palabra pronunciada. El resaltado es configurable.
- Presets personales reutilizables. Se puede modificar el texto, fuente, tamaño, color, posición, duración y animación de un fragmento sin cambiar los demás; cambios globales mediante acción explícita. Sin emojis automáticos.

## Editor

- Vista previa sobre el video, edición de texto y de palabras indispensable, y controles visuales de posición y tamaño por fragmento. Lista de fragmentos como apoyo para corrección precisa.
- Línea de tiempo con forma de onda, zoom y velocidades de reproducción; mover y recortar, dividir, unir, añadir, borrar y duplicar fragmentos; ajustar tiempos de palabras. Deshacer y rehacer.
- Guardar y reabrir proyectos conservando estilos, tiempos, palabras, fragmentos y referencia al video; gestionar archivo de origen movido o ausente. No modificar el video original.

## Exportación

- Por defecto, pista de subtítulos seleccionable en MKV (SRT), con MP4 y MOV (`mov_text`) como opciones. Conservar texto y tiempos y copiar video y audio si el contenedor lo admite. Ofrecer subtítulos renderizados en MP4/MOV para conservar los estilos de la vista previa y exportación independiente a SRT/VTT.
- Calidad original/alta/media/baja y ajustes manuales de resolución y cuadros por segundo; nunca ampliar por encima de la resolución de entrada. Mantener dimensiones, orientación y cuadros por segundo de origen por defecto cuando sea posible.
- Conservar el audio original cuando el contenedor y códec lo permitan. En modo renderizado, informar cuando se convierta el audio. Si el modo de pista no admite un códec original, informar y permitir elegir otro contenedor. Renderizar subtítulos sobre la imagen exige recodificar el video.
- Elegir nombre y carpeta; avisar antes de sobrescribir. No se necesita exportación parcial.

## Decisiones aún abiertas

- Modo conectado: proveedor gratuito, límites, consentimiento y tratamiento de audio.
- Instalador Linux: formatos concretos y distribuciones objetivo a partir de pruebas reales. Windows: instalador y compatibilidad de versiones por comprobar.
- Modelos redistribuibles, fuentes y condiciones de sus dependencias. Licencia del código propio resuelta en fase 1: GPL-3.0-only por elección del usuario.
- Asignación automática de colores por hablante: se contempla con corrección manual y queda sujeta a pruebas.

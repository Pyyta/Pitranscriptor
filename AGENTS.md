# Guía para trabajar en Pitranscriptor

Antes de cambiar el proyecto, leer [docs/memoria-proyecto.md](docs/memoria-proyecto.md), [docs/requisitos.md](docs/requisitos.md), [docs/arquitectura.md](docs/arquitectura.md) y [docs/plan.md](docs/plan.md). Para transcripción y pruebas de reconocimiento, consultar también [docs/vocabulario.md](docs/vocabulario.md).

- El objetivo y los requisitos acordados son los descritos en la memoria; las instrucciones posteriores del usuario prevalecen sobre decisiones anteriores.
- La planificación inicial no autoriza por sí sola a afirmar que las funciones existen. Verificar el estado real antes de describir funcionalidades, instaladores o compatibilidad.
- Conservar el flujo de trabajo solicitado: commits claros, específicos y agrupados por cambio, seguidos de su correspondiente push a GitHub. Si un push falla, informarlo y no darlo por completado. No subir credenciales, medios privados ni modelos pesados.
- Proteger los requisitos principales: transcripción de español mezclado con inglés y términos técnicos, edición del texto, estilos y controles independientes por fragmento, y máximo absoluto de siete palabras. El límite anterior de cinco fue reemplazado por la instrucción posterior del usuario.
- Mantener soporte planificado para Windows 10+ y Linux; no prometer aceleración gráfica o precisión no verificadas. La ruta por CPU debe considerarse al evaluar compatibilidad.
- La aplicación es para redistribución: evaluar licencias y condiciones de modelos, tipografías, códecs y componentes antes de distribuirlos. La licencia propia del proyecto aún no se ha elegido.
- Documentar cambios relevantes y decisiones nuevas; mantener actualizados el estado y las preguntas abiertas de la memoria sin eliminar el historial de decisiones importantes. Evitar duplicar documentos completos.

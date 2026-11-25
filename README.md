# Pitranscriptor

Aplicación de escritorio en desarrollo para crear y editar subtítulos dinámicos en videos cortos. Creada por **sudo_pita**.

> Estado: editor de escritorio en desarrollo. Permite transcribir con un modelo local, editar fragmentos y estilos sobre el video, guardar proyectos y exportar MP4, MOV, SRT y WebVTT. Los instaladores están pendientes.

Pitranscriptor está pensada para Windows 10 o superior y Linux, con soporte para videos verticales y horizontales de hasta cinco minutos. Su prioridad es transcribir español e inglés, especialmente cuando se mezclan términos tecnológicos, y permitir corregir cada palabra y personalizar cada fragmento.

## Documentación

- [Memoria del proyecto y requisitos RF/RNF](docs/memoria-proyecto.md)
- [Requisitos y comportamiento](docs/requisitos.md)
- [Arquitectura y decisiones técnicas](docs/arquitectura.md)
- [Plan de trabajo y pruebas](docs/plan.md)
- [Vocabulario tecnológico inicial](docs/vocabulario.md)
- [Entorno, comandos y matriz de validación](docs/desarrollo.md)
- [Licencia y revisión de componentes](docs/licencias.md)
- [Preparar grabaciones propias de evaluación](docs/pruebas-reconocimiento.md)

## Desarrollo

Con Python y [uv](https://docs.astral.sh/uv/) 0.13.10 instalados, desde el repositorio:

```console
uv sync --locked
uv run --frozen pitranscriptor doctor
uv run --frozen pytest
```

`uv` utiliza la versión de Python indicada en `.python-version` y crea `.venv`. La primera instalación requiere internet. Consulta [desarrollo](docs/desarrollo.md) para dependencias opcionales y compilación. Estos comandos son para desarrollo; todavía no abren un editor de video.

## Autor

- [Instagram](https://www.instagram.com/sudo_pita/)
- [TikTok](https://www.tiktok.com/@sudo_pita)
- [YouTube](https://www.youtube.com/@sudo_pita)
- [Facebook](https://www.facebook.com/profile.php?id=61589854056244)

Código propio bajo [GNU GPL versión 3 exclusivamente (GPL-3.0-only)](LICENSE), elegida por el autor. Los componentes de terceros conservan sus condiciones. Las instrucciones de instalación para usuarios finales se añadirán cuando existan instaladores probados.

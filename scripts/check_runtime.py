"""Smoke test local de las dependencias opcionales, sin audio ni modelos."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> None:
    import ctranslate2
    import faster_whisper
    from PySide6.QtWidgets import QApplication, QLabel

    app = QApplication([])
    label = QLabel("Pitranscriptor · Creado por sudo_pita")
    label.resize(400, 100)
    label.show()
    app.processEvents()
    assert not label.grab().isNull(), "Qt no pudo renderizar la etiqueta"
    label.close()
    print("Qt: renderizado offscreen correcto (no valida reproducción multimedia)")
    print(f"faster-whisper: importado ({faster_whisper.__version__})")
    types = ctranslate2.get_supported_compute_types("cpu")
    if not types:
        raise RuntimeError("CTranslate2 no informó tipos de cómputo de CPU")
    print(f"CTranslate2: tipos de CPU disponibles: {', '.join(sorted(types))}")
    print("No se descargaron modelos ni se probó inferencia o aceleración GPU.")


if __name__ == "__main__":
    main()

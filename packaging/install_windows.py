"""Instalador local de Pitranscriptor para Windows sin permisos de administrador."""

import argparse
import ctypes
import os
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def install(target: Path) -> None:
    target = target.resolve()
    if target.exists():
        raise FileExistsError(f"Ya existe la carpeta {target}. Elige otra ubicación.")
    target.parent.mkdir(parents=True, exist_ok=True)
    bundle = Path(__file__).resolve().with_name("Pitranscriptor.zip")
    with tempfile.TemporaryDirectory(prefix="pitranscriptor-", dir=target.parent) as directory:
        stage = Path(directory) / "app"
        with ZipFile(bundle) as archive:
            for entry in archive.infolist():
                if not (stage / entry.filename).resolve().is_relative_to(stage):
                    raise ValueError("La distribución contiene una ruta inválida")
            archive.extractall(stage)
        if not (stage / "Pitranscriptor.exe").is_file():
            raise ValueError("Falta el ejecutable en la distribución")
        stage.rename(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, help="Instalación sin interfaz en una carpeta nueva")
    args = parser.parse_args()
    if args.target:
        install(args.target)
        return 0

    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("Instalar Pitranscriptor")
    root.resizable(False, False)
    frame = tk.Frame(root, padx=20, pady=16)
    frame.pack()
    tk.Label(frame, text="Carpeta de instalación / Installation folder").grid(
        row=0, columnspan=2, sticky="w"
    )
    default = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Pitranscriptor"
    location = tk.StringVar(value=str(default))
    tk.Entry(frame, textvariable=location, width=70).grid(row=1, column=0, pady=8)

    def browse():
        directory = filedialog.askdirectory(title="Selecciona la carpeta principal")
        if directory:
            location.set(str(Path(directory) / "Pitranscriptor"))

    def apply():
        try:
            path = Path(location.get()).expanduser()
            install(path)
            start_menu = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs"
            if start_menu.is_dir():
                shortcut = start_menu / "Pitranscriptor.url"
                if not shortcut.exists():
                    shortcut.write_text(
                        f"[InternetShortcut]\nURL={path.resolve().joinpath('Pitranscriptor.exe').as_uri()}\n",
                        encoding="utf-8",
                    )
            messagebox.showinfo("Pitranscriptor", f"Instalado en\n{path}")
            root.destroy()
        except (OSError, ValueError) as error:
            messagebox.showerror("Pitranscriptor", str(error))

    tk.Button(frame, text="Examinar / Browse", command=browse).grid(row=1, column=1, padx=6)
    tk.Button(frame, text="Instalar / Install", command=apply).grid(
        row=2, column=0, sticky="e", pady=8
    )
    root.mainloop()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        if sys.stderr is not None:
            print(error, file=sys.stderr)
        elif len(sys.argv) == 1:
            ctypes.windll.user32.MessageBoxW(None, str(error), "Pitranscriptor", 16)
        raise SystemExit(1) from error

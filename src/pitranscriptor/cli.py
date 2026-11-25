"""Herramientas de preparación; la interfaz de edición se implementará después."""

import argparse
import json

from pitranscriptor import __version__
from pitranscriptor.diagnostics import environment_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pitranscriptor",
        description="Pitranscriptor · Creado por sudo_pita · Fase de preparación",
    )
    parser.add_argument("--version", action="version", version=f"Pitranscriptor {__version__}")
    commands = parser.add_subparsers(dest="command")
    doctor = commands.add_parser("doctor", help="Inspeccionar dependencias locales sin usar la red")
    doctor.add_argument("--json", action="store_true", help="Imprimir el diagnóstico como JSON")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = environment_report()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"Pitranscriptor {report['version']} · Creado por sudo_pita")
            print(f"Sistema: {report['system']} ({report['architecture']})")
            print(f"Python: {report['python']} · Base de desarrollo: {report['python_baseline']}")
            for name, installed in report["packages"].items():
                print(f"{name}: {installed or 'no instalado (opcional en fase 1)'}")
            for name, found in report["executables_on_path"].items():
                print(f"{name}: {'en PATH' if found else 'no encontrado en PATH'}")
            print(report["note"])
        return 0
    parser.print_help()
    return 0

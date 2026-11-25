"""Herramientas de preparación; la interfaz de edición se implementará después."""

import argparse
import json
import sys
from pathlib import Path

from pitranscriptor import __version__
from pitranscriptor.audio import prepare_audio
from pitranscriptor.corpus import validate_corpus
from pitranscriptor.diagnostics import environment_report
from pitranscriptor.project import load_project, save_project, write_text
from pitranscriptor.subtitles import render_subtitles
from pitranscriptor.transcription import transcribe_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pitranscriptor",
        description="Pitranscriptor · Creado por sudo_pita · Fase de preparación",
    )
    parser.add_argument("--version", action="version", version=f"Pitranscriptor {__version__}")
    commands = parser.add_subparsers(dest="command")
    doctor = commands.add_parser("doctor", help="Inspeccionar dependencias locales sin usar la red")
    doctor.add_argument("--json", action="store_true", help="Imprimir el diagnóstico como JSON")
    corpus = commands.add_parser(
        "validate-corpus", help="Validar grabaciones propias y referencias"
    )
    corpus.add_argument("manifest", type=Path, help="Ruta del manifiesto local JSON")
    prepare = commands.add_parser("prepare-audio", help="Crear una copia WAV para evaluación local")
    prepare.add_argument("source", type=Path, help="Archivo original local")
    prepare.add_argument("destination", type=Path, help="Copia WAV nueva, sin sobrescribir")
    transcribe = commands.add_parser("transcribe", help="Crear un proyecto con un modelo local")
    transcribe.add_argument("source", type=Path)
    transcribe.add_argument("destination", type=Path)
    transcribe.add_argument("--model", type=Path, required=True)
    transcribe.add_argument("--language", choices=("es", "en", "auto"), default="es")
    transcribe.add_argument("--prompt", type=Path, help="Archivo UTF-8 con pistas opcionales")
    transcribe.add_argument("--target", type=int, choices=range(1, 8), default=4)
    export = commands.add_parser("export-subtitles", help="Exportar el texto de un proyecto")
    export.add_argument("project", type=Path)
    export.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    if args.command in ("transcribe", "export-subtitles"):
        try:
            if args.destination.exists():
                raise FileExistsError("La salida ya existe")
            if args.command == "transcribe":
                project = transcribe_project(
                    args.source,
                    args.model,
                    language=None if args.language == "auto" else args.language,
                    vocabulary=args.prompt.read_text(encoding="utf-8") if args.prompt else None,
                    target=args.target,
                )
                save_project(args.destination, project)
                print(f"Proyecto creado con {len(project.cues)} fragmentos")
            else:
                suffix = args.destination.suffix.lower()
                if suffix not in {".srt", ".vtt"}:
                    raise ValueError("Elige una extensión .srt o .vtt")
                cues = load_project(args.project).cues
                write_text(args.destination, render_subtitles(cues, webvtt=suffix == ".vtt"))
                print(f"Exportados {len(cues)} fragmentos")
        except (OSError, ValueError, RuntimeError) as error:
            print(error, file=sys.stderr)
            return 1
        return 0
    if args.command == "prepare-audio":
        try:
            result = prepare_audio(args.source, args.destination)
        except (OSError, ValueError) as error:
            print(f"No se preparó el audio: {error}", file=sys.stderr)
            return 1
        print(f"Copia preparada: {result.duration_seconds:.3f} segundos, WAV PCM16 mono, 16000 Hz.")
        print(f"SHA256 original: {result.source_sha256}")
        print(f"SHA256 copia: {result.output_sha256}")
        return 0
    if args.command == "validate-corpus":
        report = validate_corpus(args.manifest)
        if not report.ok:
            for issue in report.issues:
                print(issue, file=sys.stderr)
            print("Corpus pendiente de corrección; no se ejecutó reconocimiento.", file=sys.stderr)
            return 1
        print(
            f"Corpus válido: {report.sample_count} muestras, "
            f"{report.duration_seconds:.2f} segundos."
        )
        print(f"Etiquetas: {', '.join(report.tags)}")
        print("Validación de archivos y declaraciones; la precisión todavía no se ha evaluado.")
        return 0
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

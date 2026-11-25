"""Validación local de muestras; no reconoce voz ni modifica los archivos."""

import json
import re
import wave
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

TAGS = frozenset(
    {"mixed", "english", "tech", "clean", "fillers", "two-speakers", "silence", "music"}
)
MAX_DURATION_SECONDS = 300


@dataclass(frozen=True)
class CorpusReport:
    sample_count: int
    duration_seconds: float
    tags: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def _audio_duration(path: Path, root: Path) -> float:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("el audio debe permanecer dentro de la carpeta del manifiesto")
    with wave.open(str(resolved), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise ValueError("se requiere WAV PCM de 16 bits, mono, 16000 Hz")
        duration = audio.getnframes() / audio.getframerate()
        if not 0 < duration <= MAX_DURATION_SECONDS:
            raise ValueError("la duración debe ser mayor que cero y de hasta 300 segundos")
        # Comprobar truncamiento leyendo en bloques pequeños, sin cargar todo el audio.
        frames = 0
        while block := audio.readframes(16000):
            if len(block) % 2:
                raise ValueError("datos PCM incompletos")
            frames += len(block) // 2
        if frames != audio.getnframes():
            raise ValueError("WAV truncado: faltan muestras declaradas en la cabecera")
    return duration


def validate_corpus(manifest: Path) -> CorpusReport:
    issues: list[str] = []
    tags_seen: set[str] = set()
    total_duration = 0.0
    try:
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError):
        return CorpusReport(0, 0, (), ("No se pudo leer un manifiesto JSON UTF-8 válido.",))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        return CorpusReport(0, 0, (), ("El manifiesto debe incluir schema_version: 1.",))
    if data["schema_version"] != 1:
        return CorpusReport(0, 0, (), ("Versión de manifiesto no compatible; se requiere 1.",))
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        return CorpusReport(0, 0, (), ("Se requiere al menos una muestra en samples.",))
    ids: set[str] = set()
    audios: set[Path] = set()
    root = manifest.resolve().parent
    for index, sample in enumerate(samples, start=1):
        label = f"Muestra {index}"
        if not isinstance(sample, dict):
            issues.append(f"{label}: debe ser un objeto JSON.")
            continue
        sample_id = sample.get("id")
        if not isinstance(sample_id, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9_-]{0,63}", sample_id
        ):
            issues.append(f"{label}: id inválido (usar letras minúsculas, números, - o _).")
        elif sample_id in ids:
            issues.append(f"{label}: id repetido.")
        else:
            ids.add(sample_id)
        if sample.get("permission_for_local_evaluation") is not True:
            issues.append(f"{label}: falta confirmar permiso para evaluación local.")
        if sample.get("reference_reviewed") is not True:
            issues.append(f"{label}: falta revisar la transcripción contra la grabación.")
        tags = sample.get("tags")
        if (
            not isinstance(tags, list)
            or not tags
            or any(not isinstance(tag, str) or tag not in TAGS for tag in tags)
        ):
            issues.append(f"{label}: tags debe contener etiquetas conocidas.")
            tags = []
        else:
            tags_seen.update(tags)
        reference = sample.get("reference_text")
        if not isinstance(reference, str) or (not reference.strip() and "silence" not in tags):
            issues.append(f"{label}: reference_text es obligatorio salvo en muestras de silencio.")
        if "silence" in tags and reference != "":
            issues.append(f"{label}: una muestra de silencio debe tener reference_text vacío.")
        terms = sample.get("terms", [])
        if not isinstance(terms, list) or any(
            not isinstance(term, str) or not term.strip() for term in terms
        ):
            issues.append(f"{label}: terms debe ser una lista de términos no vacíos.")
        audio = sample.get("audio")
        if not isinstance(audio, str) or not audio or "\\" in audio:
            issues.append(f"{label}: audio debe ser una ruta relativa con separadores /.")
            continue
        relative = Path(audio)
        if relative.is_absolute() or PureWindowsPath(audio).drive or ".." in relative.parts:
            issues.append(f"{label}: no se permiten rutas absolutas ni ascender con .. en audio.")
            continue
        if relative.suffix.lower() != ".wav":
            issues.append(f"{label}: audio debe ser un archivo .wav.")
            continue
        path = root / relative
        try:
            resolved = path.resolve()
            if resolved in audios:
                issues.append(f"{label}: archivo de audio repetido.")
            audios.add(resolved)
            total_duration += _audio_duration(path, root)
        except (OSError, ValueError, wave.Error, EOFError, RuntimeError) as error:
            # No imprimir rutas privadas ni textos de excepciones del sistema.
            reason = str(error) if type(error) is ValueError else "audio ausente o WAV no válido"
            issues.append(f"{label}: {reason}.")
    return CorpusReport(len(samples), total_duration, tuple(sorted(tags_seen)), tuple(issues))

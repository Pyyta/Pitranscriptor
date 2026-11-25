"""Documento de subtítulos versionado y escritura segura."""

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tempfile import NamedTemporaryFile

from pitranscriptor.subtitles import MAX_MEDIA_MS, Cue, Style, Word


@dataclass(frozen=True)
class Project:
    source: str
    duration_ms: int
    cues: tuple[Cue, ...] = ()

    def __post_init__(self):
        if not self.source or type(self.duration_ms) is not int:
            raise ValueError("La fuente y la duración son obligatorias")
        if not 0 < self.duration_ms <= MAX_MEDIA_MS:
            raise ValueError("La duración del medio debe ser de hasta cinco minutos")
        if any(cue.end_ms > self.duration_ms for cue in self.cues):
            raise ValueError("Un fragmento termina después del medio")
        if any(a.end_ms > b.start_ms for a, b in zip(self.cues, self.cues[1:], strict=False)):
            raise ValueError("Los fragmentos deben estar ordenados y no solaparse")

    def with_cues(self, cues) -> "Project":
        return replace(self, cues=tuple(sorted(cues, key=lambda cue: cue.start_ms)))


def edit_cue(cue: Cue, text: str, start_ms: int, end_ms: int) -> Cue:
    tokens = text.split()
    words = ()
    if len(tokens) == len(cue.words) and all(
        start_ms <= word.start_ms and word.end_ms <= end_ms for word in cue.words
    ):
        words = tuple(
            word if token == word.text else replace(word, text=token, probability=None)
            for word, token in zip(cue.words, tokens, strict=True)
        )
    return replace(cue, text=" ".join(tokens), start_ms=start_ms, end_ms=end_ms, words=words)


def write_text(path: Path, content: str, *, overwrite: bool = False) -> None:
    """Publicar un archivo completo y preservar los destinos existentes por defecto."""
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as temporary:
        temp_path = Path(temporary.name)
        try:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary.close()
            if overwrite:
                os.replace(temp_path, path)
            else:
                os.link(temp_path, path)
        finally:
            temporary.close()
            temp_path.unlink(missing_ok=True)


def save_project(path: Path, project: Project, *, overwrite: bool = False) -> None:
    source = Path(project.source)
    if path.resolve() == source.resolve():
        raise ValueError("El proyecto requiere una ruta diferente del medio")
    try:
        source_path = os.path.relpath(source, path.resolve().parent)
    except ValueError:  # Windows permite que el medio esté en otra unidad.
        source_path = str(source.resolve())
    data = {"schema_version": 1, **asdict(project), "source": source_path}
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", overwrite=overwrite)


def load_project(path: Path) -> Project:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ValueError("El archivo no es un proyecto de Pitranscriptor")
    if data["schema_version"] != 1:
        raise ValueError("La versión del proyecto no está admitida")
    try:
        cues = []
        for raw in data["cues"]:
            fields = dict(raw)
            fields["words"] = tuple(Word(**word) for word in fields.pop("words", ()))
            fields["style"] = Style(**fields.pop("style", {}))
            cues.append(Cue(**fields))
        source = (path.resolve().parent / data["source"]).resolve()
        return Project(str(source), data["duration_ms"], tuple(cues))
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("El proyecto contiene datos incompletos o inválidos") from error

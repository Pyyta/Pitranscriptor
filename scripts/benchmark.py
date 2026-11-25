"""Comparar modelos instalados contra un corpus local revisado."""

import argparse
import json
import os
import platform
import time
from importlib.metadata import version
from pathlib import Path

from pitranscriptor.audio import file_sha256
from pitranscriptor.corpus import validate_corpus
from pitranscriptor.evaluation import normalize_text, score_transcript


def peak_memory_mib() -> float:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        current_process = ctypes.windll.kernel32.GetCurrentProcess
        current_process.restype = wintypes.HANDLE
        get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        if not get_memory(current_process(), ctypes.byref(counters), counters.cb):
            raise OSError("No se pudo medir la memoria residente")
        return counters.PeakWorkingSetSize / 1024**2
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--prompt", action="store_true")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    report = validate_corpus(args.manifest)
    if not report.ok:
        parser.error("El corpus debe validar antes de puntuarlo")
    if args.output.exists():
        parser.error("El archivo de resultados ya existe")
    if args.threads < 1:
        parser.error("El número de hilos debe ser positivo")
    for name in ("config.json", "model.bin", "tokenizer.json"):
        if not (args.model / name).is_file():
            parser.error(f"Falta el archivo local del modelo {name}")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from faster_whisper import WhisperModel

    samples = json.loads(args.manifest.read_text(encoding="utf-8-sig"))["samples"]
    terms = args.vocabulary.read_text(encoding="utf-8").split("\n\n", 2)[-1].splitlines()
    terms = [term.strip() for term in terms if term.strip()]
    options = dict(
        language="es",
        task="transcribe",
        beam_size=5,
        temperature=0,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
        initial_prompt=", ".join(terms) if args.prompt else None,
    )
    start = time.perf_counter()
    model = WhisperModel(
        str(args.model.resolve()),
        device=args.device,
        compute_type="int8" if args.device == "cpu" else "int8_float16",
        cpu_threads=args.threads,
        local_files_only=True,
    )
    load_seconds = time.perf_counter() - start
    results = []
    for sample in samples:
        path = args.manifest.resolve().parent / sample["audio"]
        started = time.perf_counter()
        segments, info = model.transcribe(str(path), **options)
        transcript = " ".join(segment.text.strip() for segment in segments)
        elapsed = time.perf_counter() - started
        reference = sample["reference_text"]
        normalized_reference = f" {normalize_text(reference)} "
        expected = [term for term in terms if f" {normalize_text(term)} " in normalized_reference]
        score = score_transcript(reference, transcript, expected)
        normalized_hypothesis = f" {score['hypothesis_normalized']} "
        extra_terms = [
            term
            for term in terms
            if term not in expected and f" {normalize_text(term)} " in normalized_hypothesis
        ]
        results.append(
            {
                "id": sample["id"],
                "audio_sha256": file_sha256(path),
                "seconds": info.duration,
                "inference_seconds": elapsed,
                "text": transcript,
                "reference": reference,
                "extra_vocabulary_terms": extra_terms,
                **score,
            }
        )
        print(f"{sample['id']} · {elapsed:.1f} s · WER {score['wer']['rate']}", flush=True)

    data = {
        "model_sha256": file_sha256(args.model / "model.bin"),
        "device": args.device,
        "compute_type": model.model.compute_type,
        "threads": args.threads,
        "options": options,
        "model_load_seconds": load_seconds,
        "peak_rss_mib": peak_memory_mib(),
        "platform": platform.platform(),
        "packages": {name: version(name) for name in ("faster-whisper", "ctranslate2", "av")},
        "results": results,
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(data, output, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

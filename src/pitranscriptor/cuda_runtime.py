"""Carga las bibliotecas CUDA de Windows dentro del proceso que transcribe."""

import os
from pathlib import Path

DLLS = ("cublasLt64_12.dll", "cublas64_12.dll", "cudnn64_9.dll")
_handles = []


def prepare_cuda() -> None:
    if os.name == "nt":
        import ctypes

        roots = []
        if configured := os.environ.get("PITRANSCRIPTOR_CUDA_DIR"):
            roots.append(Path(configured))
        if local := os.environ.get("LOCALAPPDATA"):
            roots.append(Path(local) / "sudo_pita" / "Pitranscriptor" / "cuda")
        if toolkit := os.environ.get("CUDA_PATH"):
            roots.append(Path(toolkit) / "bin")
        folders = []
        for root in roots:
            for folder in (root, root / "bin", *sorted(root.glob("nvidia/*/bin"))):
                if folder.is_dir() and folder not in folders:
                    folders.append(folder.resolve())
        for folder in folders:
            _handles.append(os.add_dll_directory(str(folder)))
        if folders:
            os.environ["PATH"] = os.pathsep.join(
                [*(str(folder) for folder in folders), os.getenv("PATH", "")]
            )
        for filename in DLLS:
            candidate = next(
                (folder / filename for folder in folders if (folder / filename).is_file()), None
            )
            try:
                _handles.append(ctypes.WinDLL(str(candidate) if candidate else filename, winmode=0))
            except OSError as error:
                raise RuntimeError(
                    f"CUDA: no se pudo cargar {filename} o una de sus dependencias. "
                    "Selecciona CPU o instala las bibliotecas compatibles cuBLAS 12 y cuDNN 9."
                ) from error

    from ctranslate2 import get_cuda_device_count

    if not get_cuda_device_count():
        raise RuntimeError("CUDA: no se detectó una GPU NVIDIA disponible. Selecciona CPU.")

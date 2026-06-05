"""Read background-work state from ``~/.openjarvis/.state/``.

Pure-function reader used by the chat banner, completion-notification
dispatcher, and ``jarvis doctor``.  No side effects — safe to call
between every chat turn.
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from openjarvis.core import config

_MODEL_MARKER_STATES = ("downloading", "ready", "failed")


@dataclass(slots=True)
class BgStatus:
    """Snapshot of background-work state."""

    rust_extension: str = "pending"  # pending | ready | failed
    rust_error: str = ""
    models: Dict[str, str] = field(
        default_factory=dict
    )  # id -> pending|downloading|ready|failed

    def all_ready(self) -> bool:
        if self.rust_extension != "ready":
            return False
        if any(s != "ready" for s in self.models.values()):
            return False
        return True


def _safe_read(path: Path) -> Optional[str]:
    """Read a file, returning None if it disappears mid-read (race)."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return None


def _parse_model_marker_name(name: str) -> tuple[str, str] | None:
    for marker_state in _MODEL_MARKER_STATES:
        suffix = f".{marker_state}"
        if name.endswith(suffix):
            return name[: -len(suffix)], marker_state
    return None


def _windows_stream_marker_names(path: Path) -> list[str]:
    if os.name != "nt":
        return []

    class Win32FindStreamData(ctypes.Structure):
        _fields_ = [
            ("stream_size", ctypes.c_longlong),
            ("stream_name", ctypes.c_wchar * 296),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    find_first = kernel32.FindFirstStreamW
    find_first.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_int,
        ctypes.POINTER(Win32FindStreamData),
        ctypes.c_int,
    ]
    find_first.restype = ctypes.c_void_p

    find_next = kernel32.FindNextStreamW
    find_next.argtypes = [ctypes.c_void_p, ctypes.POINTER(Win32FindStreamData)]
    find_next.restype = ctypes.c_int

    find_close = kernel32.FindClose
    find_close.argtypes = [ctypes.c_void_p]
    find_close.restype = ctypes.c_int

    data = Win32FindStreamData()
    handle = find_first(str(path), 0, ctypes.byref(data), 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        return []

    names: list[str] = []
    try:
        while True:
            stream_name = data.stream_name
            if stream_name.startswith(":") and stream_name.endswith(":$DATA"):
                stream_id = stream_name[1:-6]
                if stream_id:
                    names.append(f"{path.name}:{stream_id}")
            if not find_next(handle, ctypes.byref(data)):
                break
    finally:
        find_close(handle)
    return names


def _iter_model_marker_names(models_dir: Path) -> list[str]:
    names: list[str] = []
    for file_path in models_dir.iterdir():
        names.append(file_path.name)
        names.extend(_windows_stream_marker_names(file_path))
    return names


def get_status(home: Optional[Path] = None) -> BgStatus:
    """Snapshot the background-work state from the state directory."""
    home = home or config.DEFAULT_CONFIG_DIR
    state_dir = home / ".state"
    models_dir = state_dir / "models"

    status = BgStatus()

    # Rust extension: ready supersedes failed; failed supersedes pending.
    if (state_dir / "extension-built").exists():
        status.rust_extension = "ready"
    elif (state_dir / "extension-failed").exists():
        contents = _safe_read(state_dir / "extension-failed")
        if contents is not None:
            status.rust_extension = "failed"
            status.rust_error = contents

    # Models: parse files in models_dir; .ready supersedes .downloading and .failed.
    if models_dir.is_dir():
        # First pass: capture every model id we see.
        seen: Dict[str, str] = {}
        for marker_name in _iter_model_marker_names(models_dir):
            parsed = _parse_model_marker_name(marker_name)
            if parsed is None:
                continue
            model_id, new_state = parsed
            current = seen.get(model_id, "")
            # Precedence: ready > failed > downloading
            if current == "ready":
                continue
            if new_state == "ready":
                seen[model_id] = "ready"
            elif new_state == "failed" and current != "ready":
                seen[model_id] = "failed"
            elif new_state == "downloading" and current == "":
                seen[model_id] = "downloading"
        status.models = seen

    return status

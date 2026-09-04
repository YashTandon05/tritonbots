"""Durable run metadata and checkpoints for training jobs.

This module deliberately has no policy or optimizer dependency.  A future
trainer supplies a serialisable mapping; this module makes writing, loading,
and compatibility validation reliable.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf

FORMAT_VERSION = 1


def write_resolved_config(run_dir: str | Path, config: DictConfig) -> Path:
    """Atomically persist the fully resolved configuration for a run."""
    destination = Path(run_dir) / "config.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(destination, OmegaConf.to_yaml(config, resolve=True))
    return destination


def save_checkpoint(run_dir: str | Path, state: dict[str, Any]) -> Path:
    """Atomically replace ``latest.pt`` with a versioned checkpoint."""
    destination = Path(run_dir) / "latest.pt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {"format_version": FORMAT_VERSION, **state}
    with tempfile.NamedTemporaryFile("wb", dir=destination.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        _torch().save(payload, temporary)
        with temporary.open("rb") as saved:
            os.fsync(saved.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_checkpoint(
    path: str | Path, *, expected_metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    checkpoint = Path(path)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint does not exist: {checkpoint}")
    state = _torch().load(checkpoint, map_location="cpu", weights_only=False)
    if not isinstance(state, dict) or state.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"unsupported checkpoint format: {checkpoint}")
    if expected_metadata is not None:
        actual = state.get("metadata")
        if actual != expected_metadata:
            raise ValueError("checkpoint metadata does not match this training configuration")
    return state


def _atomic_text(destination: Path, contents: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    ) as tmp:
        tmp.write(contents)
        tmp.flush()
        os.fsync(tmp.fileno())
        temporary = Path(tmp.name)
    os.replace(temporary, destination)


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "checkpoint support needs the optional train dependency (torch)"
        ) from exc
    return torch

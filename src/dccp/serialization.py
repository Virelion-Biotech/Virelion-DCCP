"""Portable JSON, finite numeric contracts, and atomic file replacement."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path


def strict_loads(raw):
    def invalid(value):
        raise ValueError(f"Nonstandard JSON number: {value}")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def real(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("JSON float exceeds finite range")
        return parsed

    return json.loads(raw, parse_constant=invalid, parse_float=real, object_pairs_hook=unique)


def read_json(path):
    return strict_loads(Path(path).read_text(encoding="utf-8"))


def atomic_write(path, encoded):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".dccp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json(path, payload):
    encoded = (json.dumps(payload, allow_nan=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    atomic_write(path, encoded)

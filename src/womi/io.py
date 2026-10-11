"""Bounded, pickle-free evidence I/O. This is not a model-execution sandbox."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

import numpy as np

MAX_BYTES = 128 * 1024**2
MAX_ELEMENTS = 32_000_000


class InvalidEvidence(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            result.update(block)
    return result.hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise InvalidEvidence("Duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    if Path(path).stat().st_size > 8 * 1024**2:
        raise InvalidEvidence("JSON exceeds metadata limit")
    with Path(path).open() as stream:
        return json.load(stream, object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(InvalidEvidence("Nonfinite JSON")))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def safe_file(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise InvalidEvidence("Expected a relative evidence path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(p in ("", ".", "..") for p in relative.split("/")):
        raise InvalidEvidence("Unsafe evidence path")
    root = Path(root).resolve()
    path = root
    for part in pure.parts:
        path = path / part
        if path.is_symlink():
            raise InvalidEvidence("Symlinks are not evidence files")
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise InvalidEvidence("Evidence file is absent or outside its root")
    return path


def verified_file(root, record):
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise InvalidEvidence("Expected path and sha256")
    path = safe_file(root, record["path"])
    if path.stat().st_size > MAX_BYTES:
        raise InvalidEvidence("Evidence file exceeds limit")
    if file_hash(path) != record["sha256"]:
        raise InvalidEvidence("Evidence hash mismatch")
    return path


def record(path, root):
    return {"path": str(Path(path).relative_to(root)), "sha256": file_hash(path)}


def load_arrays(path):
    """Inspect NPY headers before allocation, as zip member sizes alone are insufficient."""
    if Path(path).stat().st_size > MAX_BYTES:
        raise InvalidEvidence("Archive exceeds limit")
    result = {}
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not 1 <= len(members) <= 24 or sum(m.file_size for m in members) > MAX_BYTES:
            raise InvalidEvidence("Expanded archive exceeds limit")
        for member in members:
            name = member.filename
            if "/" in name or "\\" in name or not name.endswith(".npy") or name[:-4] in result:
                raise InvalidEvidence("Invalid or duplicate array member")
            raw = archive.read(member)
            stream = io.BytesIO(raw)
            version = np.lib.format.read_magic(stream)
            if version == (1, 0):
                shape, order, dtype = np.lib.format.read_array_header_1_0(stream)
            elif version == (2, 0):
                shape, order, dtype = np.lib.format.read_array_header_2_0(stream)
            else:
                raise InvalidEvidence("Unsupported NPY header version")
            count = 1
            for dim in shape:
                if not isinstance(dim, int) or dim <= 0:
                    raise InvalidEvidence("Invalid array dimensions")
                count *= dim
            if (not 1 <= len(shape) <= 5 or count > MAX_ELEMENTS or
                    dtype.kind not in "buif" or dtype.hasobject or
                    count * dtype.itemsize != len(raw) - stream.tell()):
                raise InvalidEvidence("Unsafe array header or payload length")
            result[name[:-4]] = np.load(io.BytesIO(raw), allow_pickle=False)
    return result


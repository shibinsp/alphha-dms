import hashlib
from typing import BinaryIO


def compute_file_hash(file: BinaryIO, algorithm: str = "sha256") -> str:
    """Compute hash of a file object."""
    hasher = hashlib.new(algorithm)
    for chunk in iter(lambda: file.read(8192), b""):
        hasher.update(chunk)
    file.seek(0)  # Reset file pointer
    return hasher.hexdigest()


def compute_string_hash(data: str, algorithm: str = "sha256") -> str:
    """Compute hash of a string."""
    hasher = hashlib.new(algorithm)
    hasher.update(data.encode("utf-8"))
    return hasher.hexdigest()


def compute_bytes_hash(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hash of bytes."""
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


# Aliases for backwards compatibility
hash_file = compute_file_hash
hash_string = compute_string_hash
hash_bytes = compute_bytes_hash

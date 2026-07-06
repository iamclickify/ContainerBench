import sys
from pathlib import Path
from typing import Union


def get_dir_size(path: Union[str, Path]) -> int:
    """Calculates the size of a directory in bytes."""
    path = Path(path)
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())


def format_bytes(size_bytes: int) -> str:
    """Formats raw bytes into a human-readable string."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

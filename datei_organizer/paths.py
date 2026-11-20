"""Path checks shared by scanning, sorting, and journal recovery."""
import os
import stat
from pathlib import Path


def history_dir():
    return Path(os.environ.get("DATEI_ORGANIZER_HISTORY", Path.home() / ".datei-organizer")).absolute()


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def safe_path(root, path):
    """Reject paths outside the root and links in any existing component."""
    if not path.is_relative_to(root) or ".." in path.parts or path == root:
        raise ValueError(f"Pfad außerhalb des Arbeitsordners: {path}")
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        try:
            if linked(current):
                raise ValueError(f"Verknüpfung übersprungen: {current}")
        except FileNotFoundError:
            break

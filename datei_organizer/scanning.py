"""Shared selection rules for analysis and sorting."""
from dataclasses import dataclass, fields
from datetime import date
from .log_service import log
import os
from pathlib import Path
import stat

from .paths import history_dir, linked, safe_path


@dataclass(frozen=True)
class Options:
    recursive: bool = False
    max_depth: int | None = None
    extensions: str = ""
    min_bytes: int | None = None
    max_bytes: int | None = None
    modified_from: str = ""
    modified_until: str = ""
    hidden: bool = False
    preserve_structure: bool = False
    conflict: str = "ask"
    theme: str = "bootstrap-dark"
    logging: bool = True

    @classmethod
    def load(cls, values):
        if not isinstance(values, dict):
            raise ValueError("Optionen müssen ein Objekt sein.")
        if set(values) - {f.name for f in fields(cls)}:
            raise ValueError("Unbekannte Einstellung.")
        options = cls(**values)
        for key in ("recursive", "hidden", "preserve_structure", "logging"):
            if type(getattr(options, key)) is not bool:
                raise ValueError(f"{key}: Ja/Nein erwartet")
        for key in ("max_depth", "min_bytes", "max_bytes"):
            value = getattr(options, key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{key}: nichtnegative Ganzzahl erwartet")
        for key in ("extensions", "modified_from", "modified_until", "theme", "conflict"):
            if not isinstance(getattr(options, key), str):
                raise ValueError(f"{key}: Text erwartet")
        if options.conflict not in ("ask", "rename", "skip"):
            raise ValueError("Konfliktstrategie: ask, rename oder skip")
        for value in (options.modified_from, options.modified_until):
            if value:
                date.fromisoformat(value)
        if options.modified_from and options.modified_until and date.fromisoformat(options.modified_from) > date.fromisoformat(options.modified_until):
            raise ValueError("Ungültiger Datumsbereich")
        if options.min_bytes is not None and options.max_bytes is not None and options.min_bytes > options.max_bytes:
            raise ValueError("Ungültiger Größenbereich")
        return options


def scan(folder, categories, options, cancelled, error, protected_paths=()):
    if linked(folder):
        raise ValueError(f"Verknüpfter Quellordner: {folder}")
    root = folder.resolve(strict=True)
    if root.is_relative_to(history_dir()):
        raise ValueError("Das Journalverzeichnis ist als Quelle ausgeschlossen.")
    if not root.is_dir():
        raise NotADirectoryError(root)
    excluded = {root / name for name in categories.values()} | {history_dir()}
    protected = {Path(path).absolute() for path in protected_paths}
    protected.update(Path.cwd() / name for name in ("Hauptlog.log", "Hauptlog.log.1", "Hauptlog.log.2", "Hauptlog.log.3"))
    extensions = {"." + part.strip().lower().lstrip(".") for part in options.extensions.split(",") if part.strip()}
    first = date.fromisoformat(options.modified_from) if options.modified_from else None
    last = date.fromisoformat(options.modified_until) if options.modified_until else None
    pending = [(root, 0)]
    while pending and not cancelled():
        directory, depth = pending.pop()
        try:
            if directory != root:
                safe_path(root, directory)
            with os.scandir(directory) as entries:
                for entry in entries:
                    if cancelled():
                        return
                    path = Path(entry.path)
                    if path in protected:
                        continue
                    try:
                        info = entry.stat(follow_symlinks=False)
                        attrs = getattr(info, "st_file_attributes", 0)
                        if entry.is_symlink() or attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                            continue
                        if not options.hidden and (entry.name.startswith(".") or attrs & stat.FILE_ATTRIBUTE_HIDDEN):
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            if options.recursive and path not in excluded and (options.max_depth is None or depth < options.max_depth):
                                pending.append((path, depth + 1))
                            continue
                        if not stat.S_ISREG(info.st_mode) or (extensions and path.suffix.lower() not in extensions):
                            continue
                        if options.min_bytes is not None and info.st_size < options.min_bytes:
                            continue
                        if options.max_bytes is not None and info.st_size > options.max_bytes:
                            continue
                        modified = date.fromtimestamp(info.st_mtime)
                        if (first and modified < first) or (last and modified > last):
                            continue
                        yield path
                    except OSError as exc:
                        log.warning("Datei nicht lesbar: %s (%s)", path, exc)
                        error(path, exc)
        except (ValueError, OSError) as exc:
            log.warning("Ordner nicht lesbar: %s (%s)", directory, exc)
            error(directory, exc)


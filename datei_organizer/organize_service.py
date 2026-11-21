from .log_service import log
import shutil
import sqlite3
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from .scanning import Options, scan
from .paths import safe_path, history_dir
from .journal import Journal

class FilePaths(TypedDict):
    source: Path
    destination: Path
    status: str


def summary(result):
    counts = {key: 0 for key in ("moved", "skipped", "failed", "cancelled")}
    for entry in result.values():
        status = entry["status"]
        if status in counts:
            counts[status] += 1
    return (f"Verschoben: {counts['moved']} · Übersprungen: {counts['skipped']} · "
            f"Fehlgeschlagen: {counts['failed']} · Abgebrochen: {counts['cancelled']}")


class OrganizeService:
    def determine_category(self, file_path, categories):
        return categories.get(file_path.suffix.lower())

    def preview_sorting(self, folder, categories, options=None, *, protected_paths=(), cancelled=lambda: False, progress=lambda *args: None):
        """Return relative source keys so repeated basenames remain distinct."""
        options = options or Options()
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        scan_root = folder
        folder = folder.resolve()
        plan = {}
        targets = set()

        scan_errors = 0

        def scan_error(path, error):
            nonlocal scan_errors
            scan_errors += 1
            plan[str(path.relative_to(folder))] = dict(source=path, destination=path, status="failed", error=str(error))

        for source in scan(scan_root, categories, options, cancelled, scan_error, protected_paths):
            if source.is_relative_to(history_dir()):
                continue
            category = self.determine_category(source, categories)
            if category is None:
                continue
            relative = source.relative_to(folder)
            destination = folder / category / (relative if options.preserve_structure else source.name)
            safe_path(folder, destination.parent)
            occupied = destination.exists() or destination.is_symlink() or destination in targets
            plan[str(relative)] = dict(source=source, destination=destination, status="conflict" if occupied else "planned")
            targets.add(destination)
            progress(len(plan), 0, scan_errors)
        log.info("Vorschau für %s: %d Einträge, %d Lesefehler", folder, len(plan), scan_errors)
        return plan

    @staticmethod
    def _move_to_free_path(source, destination):
        destination.touch(exist_ok=False)
        try:
            shutil.move(source, destination)
        except OSError:
            destination.unlink(missing_ok=True)
            raise

    def organize_files(self, folder, preview_result, *, conflict="ask", decide=None,
                       cancelled=lambda: False, progress=lambda *args: None):
        """Execute the confirmed snapshot. Record every completed move before continuing."""
        folder = folder.resolve(strict=True)
        journal = Journal(folder)
        run = uuid4().hex
        results = {}
        errors = 0
        for key, entry in preview_result.items():
            source, destination = entry["source"], entry["destination"]
            row = results[key] = dict(entry)
            if cancelled():
                row["status"] = "cancelled"
                continue
            try:
                if entry["status"] == "failed":
                    raise OSError(entry.get("error", "Datei nicht lesbar"))
                safe_path(folder, source)
                safe_path(folder, destination.parent)
                if destination.is_relative_to(history_dir()):
                    raise ValueError("Journalverzeichnis ist als Ziel ausgeschlossen")
                if not source.is_file() or source.is_relative_to(history_dir()):
                    raise OSError(f"Quelldatei nicht verfügbar: {source}")
                destination.parent.mkdir(exist_ok=True, parents=True)
                number = 1
                while True:
                    if cancelled():
                        row["status"] = "cancelled"
                        break
                    candidate = destination if number == 1 else destination.with_name(
                        f"{destination.stem}_{number}{destination.suffix}")
                    if candidate.exists() or candidate.is_symlink():
                        if number == 1:
                            action = decide(source, destination) if conflict == "ask" and decide else conflict
                            log.info("Namenskonflikt %s: %s", destination, action)
                            if action != "rename":
                                row["status"] = "cancelled" if cancelled() else ("conflict" if action == "ask" else "skipped")
                                break
                        number += 1
                        continue
                    safe_path(folder, source)
                    safe_path(folder, candidate)
                    # A pending record survives interruption between the move and its confirmation.
                    record = journal.prepare(run, source, candidate)
                    try:
                        self._move_to_free_path(source, candidate)
                    except FileExistsError:
                        journal.mark(record, "void")
                        continue
                    except OSError:
                        journal.mark(record, "void")
                        raise
                    try:
                        journal.mark(record, "done")
                    except sqlite3.Error:
                        # The committed pending record can still be used by undo.
                        log.exception("Verschoben; Journalbestätigung ausstehend: %s", candidate)
                    row.update(destination=candidate, status="moved")
                    log.info("Datei %s nach %s verschoben", source, candidate)
                    break
            except (OSError, ValueError, sqlite3.Error) as exc:
                row.update(status="failed", error=str(exc))
                errors += 1
                log.exception("Sortieren fehlgeschlagen: %s", source)
            progress(len(results), len(preview_result), errors)
        log.info("Sortierung in %s: %s", folder, summary(results))
        return results

    def undo(self, folder, *, cancelled=lambda: False, progress=lambda *args: None):
        return Journal(folder).undo(self._move_to_free_path, cancelled, progress)

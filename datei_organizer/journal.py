"""Persistent move history. Pending records also cover interrupted moves."""
from .log_service import log
import hashlib
import sqlite3
from contextlib import closing

from .paths import history_dir, safe_path

def fingerprint(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f"Datei wurde während des Lesens geändert: {path}")
    return digest.hexdigest(), after.st_mtime_ns


class Journal:
    def __init__(self, root):
        self.root = root.resolve()
        self.path = history_dir() / "moves.sqlite3"

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("""CREATE TABLE IF NOT EXISTS moves
            (id INTEGER PRIMARY KEY, root TEXT, run TEXT, source TEXT,
             destination TEXT, digest TEXT, modified INTEGER, state TEXT)""")
        return db

    def prepare(self, run, source, destination):
        digest, modified = fingerprint(source)
        with closing(self.connect()) as db, db:
            row = db.execute("INSERT INTO moves VALUES(NULL,?,?,?,?,?,?,?)",
                             (str(self.root), run, str(source.relative_to(self.root)),
                              str(destination.relative_to(self.root)), digest, modified, "pending"))
            log.debug("Verschiebung im Journal vorbereitet: %s -> %s", source, destination)
            return row.lastrowid

    def mark(self, record, state):
        with closing(self.connect()) as db, db:
            db.execute("UPDATE moves SET state=? WHERE id=?", (state, record))

    def undo(self, move, cancelled, progress):
        """Undo the latest remaining run; retain unresolved entries for retry."""
        result = {}
        if not self.path.exists():
            return result
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("""SELECT id,source,destination,digest,modified FROM moves
                WHERE root=? AND state IN ('pending','done') AND run=(
                    SELECT run FROM moves WHERE root=? AND state IN ('pending','done')
                    ORDER BY id DESC LIMIT 1) ORDER BY id DESC""", (str(self.root), str(self.root))).fetchall()
            errors = 0
            for index, (record, original, current, digest, modified) in enumerate(rows, 1):
                source, destination = self.root / current, self.root / original
                if cancelled():
                    result[current] = dict(source=source, destination=destination, status="cancelled")
                    continue
                try:
                    safe_path(self.root, source)
                    safe_path(self.root, destination)
                    # A process can stop after restoring the file but before committing the journal.
                    if not source.exists() and destination.is_file() and fingerprint(destination) == (digest, modified):
                        db.execute("UPDATE moves SET state='undone' WHERE id=?", (record,))
                        result[current] = dict(source=source, destination=destination, status="skipped")
                        progress(index, len(rows), errors)
                        continue
                    if destination.exists() or fingerprint(source) != (digest, modified):
                        raise ValueError("Ursprung belegt oder verschobene Datei geändert")
                    if not destination.parent.is_dir():
                        raise ValueError("Ursprünglicher Ordner fehlt")
                    move(source, destination)
                    db.execute("UPDATE moves SET state='undone' WHERE id=?", (record,))
                    status = "moved"
                    log.info("Rücknahme %s -> %s", source, destination)
                except (ValueError, OSError) as exc:
                    log.warning("Rücknahme für %s ausgelassen: %s", source, exc)
                    errors += 1
                    progress(index, len(rows), errors)
                    status = "failed"
                    result[current] = dict(source=source, destination=destination, status=status, error=str(exc))
                    continue
                result[current] = dict(source=source, destination=destination, status=status)
                progress(index, len(rows), errors)
        return result


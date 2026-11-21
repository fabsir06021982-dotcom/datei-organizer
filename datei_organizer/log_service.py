"""Application logging is independent of the undo journal and of host loggers."""
import logging
from logging.handlers import RotatingFileHandler

log = logging.getLogger("datei_organizer")
log.addHandler(logging.NullHandler())

def configure_logging(enabled: bool) -> None:
    for handler in list(log.handlers):
        if isinstance(handler, RotatingFileHandler):
            log.removeHandler(handler)
            handler.close()
    log.disabled = not enabled
    if enabled:
        handler = RotatingFileHandler("Hauptlog.log", maxBytes=1_000_000, backupCount=3,
                                      encoding="utf-8", delay=True)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)

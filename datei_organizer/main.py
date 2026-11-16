
import logging
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler(filename="Hauptlog.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")

handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
stream_formatter = logging.Formatter("%(levelname)s - %(message)s")
stream_handler.setFormatter(stream_formatter)
logging.getLogger().addHandler(stream_handler)


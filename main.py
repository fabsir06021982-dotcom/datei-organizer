from pathlib import Path
import shutil
import os

ordner = Path("testdateien")
kategorien = {".txt": "texte", ".png": "bilder", ".jpg": "bilder", ".pdf": "dokumente"}

absoluter_pfad = ordner.resolve()

print(ordner.resolve())
for datei in ordner.iterdir():
    if datei.is_dir():
        continue
    for key in kategorien.keys():
        if datei.suffix == key:
            kategorien_value = kategorien.get(key)
            quelldatei = os.path.join(absoluter_pfad, datei.name)
            zielordner = absoluter_pfad / kategorien_value
            if not zielordner.is_dir():
                os.mkdir(zielordner)
            shutil.move(quelldatei, zielordner)
    

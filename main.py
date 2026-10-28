from pathlib import Path
import shutil

ordner = Path("testdateien")


if not ordner.is_dir():
    print("Ordner testdateien nicht vorhanden!")
    raise SystemExit


kategorien = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

absoluter_pfad = ordner.resolve()

def bestimme_kategorie(datei, kategorien):
    kategorie = kategorien.get(datei.suffix)
    if kategorie is None:
        return "sonstiges"
    return kategorie

for datei in ordner.iterdir():
    if datei.is_dir():
        continue
    
    fertiger_pfad = absoluter_pfad / bestimme_kategorie(datei, kategorien)

    fertiger_pfad.mkdir(exist_ok=True)
    ziel_datei = fertiger_pfad / datei.name

    if ziel_datei.exists():
        print(f"Datei existiert bereits: {ziel_datei}")
        continue

    quelldatei = absoluter_pfad / datei.name
    shutil.move(quelldatei, fertiger_pfad)






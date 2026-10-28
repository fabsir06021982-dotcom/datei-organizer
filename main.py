from pathlib import Path
import shutil

ordner = Path("testdateien")

kategorien = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}


def bestimme_kategorie(datei: Path, kategorien: dict[str, str]) -> str:
    kategorie = kategorien.get(datei.suffix)
    if kategorie is None:
        return "sonstiges"
    return kategorie

def organisiere_dateien(ordner: Path, kategorien: dict[str, str]) -> None:
    if not ordner.is_dir():
        print(f"Ordner {ordner} nicht vorhanden!")
        raise SystemExit
  
    # compute absolute path
    absoluter_pfad = ordner.resolve() 
    
    for datei in ordner.iterdir():
        if datei.is_dir():
            continue
   
        fertiger_pfad = absoluter_pfad / bestimme_kategorie(datei, kategorien)
        
        try:
            # create path, if not exits
            fertiger_pfad.mkdir(exist_ok=True)
            
        except OSError as fehler:
            print(f"Ordner konnte nicht erstellt werden: {fehler}")
            continue


        # create file path
        ziel_datei = fertiger_pfad / datei.name
        # check if file path exists
        if ziel_datei.exists():
            print(f"Datei existiert bereits: {ziel_datei}")
            continue
        # create source file path
        quelldatei = absoluter_pfad / datei.name

        try:
            # move source file path to file path
            shutil.move(quelldatei, fertiger_pfad)
        except OSError as fehler:
            print(f"Die Datei {quelldatei} konnte nicht nach {fertiger_pfad} verschoben werden. {fehler}")


if __name__ == "__main__":
    organisiere_dateien(ordner, kategorien)







from pathlib import Path, PureWindowsPath, PurePosixPath
import logging
import shutil
import json

logging.basicConfig(filename="Hauptlog.log", level=logging.INFO)

def lade_konfiguration(dateipfad: Path):
    try:
        with open(dateipfad, "r", encoding="utf-8") as file:
            d = json.load(file)
            if not isinstance(d, dict):
                raise ValueError("Config Datei enthält kein Dict")
            elif "ordner" not in d or "kategorien" not in d or not isinstance(d["ordner"], str) or not isinstance(d["kategorien"], dict):
                raise ValueError("Erforderliche Struktur oder Datentypen stimmen nicht")
            for key, value in d["kategorien"].items():
                if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
                    raise ValueError("JSON Datei enthält falsche Werte")  
                
                windows_pfad = PureWindowsPath(value)
                posix_pfad = PurePosixPath(value)
                if windows_pfad.is_absolute() or posix_pfad.is_absolute() or ".." in windows_pfad.parts or ".." in posix_pfad.parts or windows_pfad.drive != "" or "/" in value or "\\" in value:
                    raise ValueError("Pfadangabe enthalten")    
                                           
            if not d["kategorien"] or not d["ordner"].strip():
                raise ValueError("In der JSON fehlen bestimmte Werte")
                
            return d
    except FileNotFoundError as fehler:
        raise FileNotFoundError("Config Datei nicht gefunden") from fehler




def bestimme_kategorie(datei: Path, kategorien: dict[str, str]) -> str:
    kategorie = kategorien.get(datei.suffix)
    if kategorie is None:
        return "sonstiges"
    return kategorie

def organisiere_dateien(ordner: Path, kategorien: dict[str, str]) -> None:
    if not ordner.is_dir():
        raise FileNotFoundError("Arbeitsverzeichnis nicht gefunden")
  
    # compute absolute path
    absoluter_pfad = ordner.resolve() 
    
    for datei in ordner.iterdir():
        if datei.is_dir():
            continue
   
        fertiger_pfad = absoluter_pfad / bestimme_kategorie(datei, kategorien)
        fertiger_pfad = fertiger_pfad.resolve()


        if not fertiger_pfad.is_relative_to(absoluter_pfad):
            raise ValueError("Fertiger Pfad liegt nicht innerhalb von ordner Pfad")

        
        try:
            # create path, if not exits
            fertiger_pfad.mkdir(exist_ok=True)
            
        except OSError as fehler:
            logging.warning("Ordner konnte nicht erstellt werden: %s", fehler)
            continue


        # create file path
        ziel_datei = fertiger_pfad / datei.name
        # check if file path exists
        if ziel_datei.exists():
            logging.info("Datei existiert bereits: %s", {ziel_datei})
            continue
        # create source file path
        quelldatei = absoluter_pfad / datei.name

        try:
            # move source file path to file path
            shutil.move(quelldatei, fertiger_pfad)
        except OSError as fehler:
            logging.error("Die Datei %s konnte nicht nach %s verschoben werden: %s",
              quelldatei, fertiger_pfad, fehler)
        



if __name__ == "__main__":
    jsonconfig = Path("config.json")
   
    try:

        konfiguration = lade_konfiguration(jsonconfig)

    except FileNotFoundError as fehler:
        print(f"Datei nicht gefunden: {fehler}")
        raise SystemExit(1)
    except json.JSONDecodeError as fehler:
        print(f"JSON fehlerhaft: {fehler}")
        raise SystemExit(1)
    except ValueError as fehler:
        print(f"Werte in JSON nicht korrekt: {fehler}")
        raise SystemExit(1)


    kategorien = konfiguration["kategorien"]
    ordner = Path(konfiguration["ordner"])

    try:
        organisiere_dateien(ordner, kategorien)
    except FileNotFoundError as fehler:
        print(f"Arbeitsverzeichnis nicht gefunden: {fehler}")
        raise SystemExit(1)
    






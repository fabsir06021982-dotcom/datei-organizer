from pathlib import Path, PureWindowsPath, PurePosixPath
import logging
from logging.handlers import RotatingFileHandler
import shutil
import json

handler = RotatingFileHandler(
    filename = "Hauptlog.log",
    maxBytes = 1_000_000,
    backupCount= 3,
    encoding="utf-8"
)

handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
streamhandler = logging.StreamHandler()
streamhandler.setLevel(logging.WARNING)
formatterstream = logging.Formatter("%(levelname)s - %(message)s")
streamhandler.setFormatter(formatterstream)
logging.getLogger().addHandler(streamhandler)

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

def speichere_konfiguration(konfigurationspfad: Path, konfiguration: dict) -> None:
    with konfigurationspfad.open("w", encoding="utf-8") as datei:
        json.dump(konfiguration, datei, indent=4, ensure_ascii=False)


def bestimme_kategorie(datei: Path, kategorien: dict[str, str]) -> str | None:
    kategorie = kategorien.get(datei.suffix.lower())
    if kategorie is None:
        return None
    return kategorie

def organisiere_dateien(ordner: Path, kategorien: dict[str, str]) -> None:
    if not ordner.is_dir():
        raise FileNotFoundError("Arbeitsverzeichnis nicht gefunden")
  
    # compute absolute path
    absoluter_pfad = ordner.resolve() 
    
    for datei in ordner.iterdir():
        if datei.is_dir():
            continue
        
        richtige_kategorie = bestimme_kategorie(datei, kategorien)
        if richtige_kategorie is None:
            continue
        
        fertiger_pfad = absoluter_pfad / richtige_kategorie
        fertiger_pfad = fertiger_pfad.resolve()


        if not fertiger_pfad.is_relative_to(absoluter_pfad):
            raise ValueError("Fertiger Pfad liegt nicht innerhalb von ordner Pfad")

        if not fertiger_pfad.exists():
            try:
           
                # create path, if not exits
                fertiger_pfad.mkdir()
                logging.info("Der Ordner %s wurde erfolgreich erstellt", fertiger_pfad)
            except OSError as fehler:
                logging.warning("Ordner konnte nicht erstellt werden: %s", fehler)
                continue
        else:
                logging.info("Der Ordner %s ist bereits vorhanden", fertiger_pfad)

        # create file path
        ziel_datei = fertiger_pfad / datei.name
        # check if file path exists
        if ziel_datei.exists():
            logging.info("Datei existiert bereits: %s", ziel_datei)
            continue
        # create source file path
        quelldatei = absoluter_pfad / datei.name

        try:
            # move source file path to file path
            shutil.move(quelldatei, fertiger_pfad)
            logging.info("Datei %s wurde erfolgreich nach %s verschoben", quelldatei, fertiger_pfad)
        except OSError:
            logging.exception("Die Datei %s konnte nicht nach %s verschoben werden ",
              quelldatei, fertiger_pfad)
        
def analysiere_dateien(ordnerpfad: Path, kategorien: dict) -> dict:
    analysedict = {}
    ordner = Path(ordnerpfad)
    for pfad in ordner.rglob("*"):
        if pfad.is_file():
            dateiendung = pfad.suffix.lower()
            if dateiendung in analysedict:
                analysedict[dateiendung]["anzahl"] += 1
            else:               
                analysedict[dateiendung] = {"anzahl" : 1, "kategorie" : kategorien.get(dateiendung)}
    return analysedict

def prozent_dateien(analysedict: dict) -> dict:
    gesamtzahldateien = sum(eintrag["anzahl"] for eintrag in analysedict.values())
    prozentdict = {}
    for dateiendung in analysedict:
        anzahl = analysedict[dateiendung]["anzahl"]
        prozent = anzahl / gesamtzahldateien * 100
        prozentdict.update({dateiendung : prozent})
    return prozentdict

def zeige_analyse(analysedict, prozentdict):
    for item in analysedict:
        anz = analysedict[item]["anzahl"]
        pro = prozentdict[item]
        kat = analysedict[item]["kategorie"]  
        if item == "":
            item = "ohne Endung"
        if kat is None:
            kat = "nicht zugeordnet" 
        print(f"Dateiendung: {item}, Anzahl: {anz}, Prozent: {pro:.2f}%, Kategorie: {kat}")
  
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

    # try:
    #     organisiere_dateien(ordner, kategorien)
    # except FileNotFoundError as fehler:
    #     print(f"Arbeitsverzeichnis nicht gefunden: {fehler}")
    #     raise SystemExit(1)
    analyse = analysiere_dateien(ordner, kategorien)
    prozent = prozent_dateien(analyse)
    zeige_analyse(analyse, prozent)
    






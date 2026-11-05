import pytest
import logging
import shutil
import subprocess
import json
from unittest.mock import patch
from pathlib import Path
from datei_organizer.main import organisiere_dateien, bestimme_kategorie, lade_konfiguration

kategorien = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

def test_txt():
    result = bestimme_kategorie(Path("beispiel.txt"), kategorien)
    assert result == "texte"

def test_png():
    result = bestimme_kategorie(Path("bild.png"), kategorien)
    assert result == "bilder"

def test_unbekannt():
    result = bestimme_kategorie(Path("archiv.xyz"), kategorien)
    assert result == "sonstiges"

def test_datei_verschieben(quellordner):

    file_path = quellordner / "meine_testdatei.txt"

    file_path.write_text("Hallo Welt", encoding="utf-8")
    organisiere_dateien(quellordner, kategorien)
    ziel_ordner = quellordner / "texte"
    ziel_datei = ziel_ordner / "meine_testdatei.txt"
    assert ziel_datei.exists()
    assert not file_path.exists()

def test_datei_existiert_bereits(quellordner):
   
    file_path = quellordner / "meine_testdatei.txt"
    file_path.write_text("Neuer Inhalt", encoding="utf-8")
    zielordner = quellordner / "texte"
    zielordner.mkdir()
    zieldatei = zielordner / "meine_testdatei.txt"
    zieldatei.write_text("Alter Inhalt", encoding="utf-8")
    organisiere_dateien(quellordner, kategorien)
    assert file_path.exists()
    assert zieldatei.exists()
    assert file_path.read_text(encoding="utf-8") == "Neuer Inhalt"
    assert zieldatei.read_text(encoding="utf-8") == "Alter Inhalt"

def test_ordner_existiert_nicht(tmp_path):
    ordner = tmp_path/"testdateien"
    
    with pytest.raises(FileNotFoundError):
        organisiere_dateien(ordner, kategorien)

def test_unterordner_ueberspringen(quellordner):

    unterordner = quellordner / "unterordner"
    unterordner.mkdir()
    file_path = unterordner / "test.txt"
    file_path.write_text("testdatei", encoding="utf-8")

    organisiere_dateien(quellordner, kategorien)
    ziel_datei = quellordner / "texte" / "test.txt"
    assert not ziel_datei.exists()
    assert unterordner.exists()
    assert file_path.read_text(encoding="utf-8") == "testdatei"

@pytest.fixture
def quellordner(tmp_path):
    ordner = tmp_path / "testdateien"
    ordner.mkdir()
    return ordner

def test_verschieben_fehlschlag(quellordner, caplog):
    datei = quellordner / "fehler.txt"
    datei.write_text("fehler", encoding="utf-8")

    with patch("main.shutil.move", side_effect=OSError("Simulierter Fehler")):
        organisiere_dateien(quellordner, kategorien)

    
    assert "Simulierter Fehler" in caplog.text
    assert datei.exists()

def test_ordner_erstellen_fehlschlag(quellordner, caplog):
    datei = quellordner / "test.txt"
    datei.write_text("INHALT", encoding="utf-8")

    with patch("pathlib.Path.mkdir", side_effect=OSError("Ordnerfehler")):
        organisiere_dateien(quellordner, kategorien)
  
    assert "Ordnerfehler" in caplog.text
    assert datei.exists()

def test_konfiguration_laden(tmp_path):
    configdatei = tmp_path / "config.json"
  

    beispieldict = { "ordner" : "testdateien", "kategorien" : {".txt" : "texte", ".png" : "bilder", ".jpg" : "bilder", ".pdf" : "dokumente"}}
    s = json.dumps(beispieldict)

    configdatei.write_text(s, encoding="utf-8")

    konfiguration = lade_konfiguration(configdatei)
    kategorien = konfiguration["kategorien"]
    ordner = Path(konfiguration["ordner"])
    assert kategorien == {".txt" : "texte", ".png" : "bilder", ".jpg" : "bilder", ".pdf" : "dokumente"}
    assert ordner == Path("testdateien")

def test_konfiguration_fehlt(tmp_path):
    configdatei = tmp_path / "nicht_vorhanden.json"

    with pytest.raises(FileNotFoundError):
        lade_konfiguration(configdatei)

def test_konfiguration_ungueltig(tmp_path):
    configdatei = tmp_path / "ungueltig.json"
    configdatei.write_text(" ''''ungueltig", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        lade_konfiguration(configdatei)

def test_konfiguration_leeres_dict(tmp_path):
    configdatei = tmp_path / "config.json"
    beispieldict = { "ordner": "testdateien", "kategorien" : {}}

    s = json.dumps(beispieldict)
    configdatei.write_text(s, encoding="utf-8")

    with pytest.raises(ValueError):
        lade_konfiguration(configdatei)

def test_konfiguration_datentyp(tmp_path):
    configdatei = tmp_path / "config.json"
    beispiel = ["testdateien", "texte"]

    s = json.dumps(beispiel)
    configdatei.write_text(s, encoding="utf-8")

    with pytest.raises(ValueError):
        lade_konfiguration(configdatei)

def test_konfiguration_fehlende_kategorie(tmp_path):
    configdatei = tmp_path / "config.json"
    beispiel = {"ordner" : "testdateien"}

    s = json.dumps(beispiel)
    configdatei.write_text(s, encoding="utf-8")

    with pytest.raises(ValueError):
        lade_konfiguration(configdatei)

def test_konfiguration_falscherdatentyp(tmp_path):
    configdatei = tmp_path / "config.json"
    beispiel = {"ordner" : "testdateien", "kategorien" : {".txt" : 123}}

    s = json.dumps(beispiel)
    configdatei.write_text(s, encoding="utf-8")

    with pytest.raises(ValueError):
        lade_konfiguration(configdatei)

def test_konfiguration_leerevariablen(tmp_path):
    configdatei = tmp_path / "config.json"
    beispiel = {"ordner" : "testdateien", "kategorien" : {".txt" : ""}}

    s = json.dumps(beispiel)
    configdatei.write_text(s, encoding="utf-8")

    with pytest.raises(ValueError):
        lade_konfiguration(configdatei)

def test_symlink_ausserhalb_ordner(tmp_path):
    arbeitsverzeichnis = tmp_path / "arbeitsverzeichnis"
    externes_verzeichnis = tmp_path / "extern" 

    arbeitsverzeichnis.mkdir()
    externes_verzeichnis.mkdir()

    symlink = arbeitsverzeichnis / "bilder"
    symlink.symlink_to(externes_verzeichnis, target_is_directory=True)

    bild = arbeitsverzeichnis / "bild.png"
    bild.write_text("Testinhalt", encoding="utf-8")

    with pytest.raises(ValueError):
        organisiere_dateien(arbeitsverzeichnis, kategorien)

    assert bild.exists()
    assert not (externes_verzeichnis / "bild.png").exists()

def test_logging_info(caplog):
    logging.info("Testinformation")

    assert "Testinformation" in caplog.text
    assert caplog.records[0].levelname == "INFO"

def simuliere_verschieben_fehler(quelle, ziel):
    raise OSError("Testfehler beim verschieben")

def test_logging_verschieben_fehler(monkeypatch, caplog, tmp_path):
    monkeypatch.setattr(shutil,"move", simuliere_verschieben_fehler)
    ordner = tmp_path / "arbeitsverzeichnis"
    ordner.mkdir()
    bild = ordner / "bild.png"
    bild.write_text("Bsp", encoding="utf-8")

    organisiere_dateien(ordner, kategorien)

    assert "Testfehler beim verschieben" in caplog.text
    assert any(eintrag.levelname == "ERROR" for eintrag in caplog.records)
    assert bild.exists()

def test_cli_config_fehlt(tmp_path):
    ordner = tmp_path / "arbeitsverzeichnis"
    ordner.mkdir()
    main_datei = Path.cwd() / "main.py"

    ausgabe = subprocess.run(["python", str(main_datei)], cwd=ordner, capture_output=True, text=True)
    assert ausgabe.returncode == 1
    assert "Datei nicht gefunden" in ausgabe.stdout

def test_cli_config_ungueltig(tmp_path):
    ordner = tmp_path / "arbeitsverzeichnis"
    ordner.mkdir()
    configdatei = ordner / "config.json"
    configdatei.write_text("XYZ", encoding="utf-8")
    main_datei = Path.cwd() / "main.py"

    ausgabe = subprocess.run(["python", str(main_datei)], cwd=ordner, capture_output=True, text=True)
    assert ausgabe.returncode == 1
    assert "JSON fehlerhaft" in ausgabe.stdout

def test_cli_config_falsche_werte(tmp_path):
    arbeitsverzeichnis = tmp_path / "arbeitsverzeichnis"
    arbeitsverzeichnis.mkdir()
    configdatei = arbeitsverzeichnis / "config.json"
    beispielconfig = {"ordner": 123, "kategorien": {".txt": "texte"}}

    s = json.dumps(beispielconfig)
    configdatei.write_text(s, encoding="utf-8")

    main_datei = Path.cwd() / "main.py"
    ausgabe = subprocess.run(["python", str(main_datei)], cwd=arbeitsverzeichnis, capture_output=True, text=True)
    assert ausgabe.returncode == 1
    assert "Werte in JSON nicht korrekt" in ausgabe.stdout

def test_cli_arbeitsverzeichnis_fehlt(tmp_path):
    arbeitsverzeichnis = tmp_path / "arbeitsverzeichnis"
    arbeitsverzeichnis.mkdir()
    configdatei = arbeitsverzeichnis / "config.json"
    beispielconfig = {"ordner": "existiert_nicht", "kategorien": {".txt": "texte"}}

    s = json.dumps(beispielconfig)
    configdatei.write_text(s, encoding="utf-8")

    main_datei = Path.cwd() / "main.py"
    ausgabe = subprocess.run(["python", str(main_datei)], cwd=arbeitsverzeichnis, capture_output=True, text=True)
    assert ausgabe.returncode == 1
    assert "Arbeitsverzeichnis nicht gefunden" in ausgabe.stdout    

    




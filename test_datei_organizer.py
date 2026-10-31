import pytest

from pathlib import Path
from main import organisiere_dateien, bestimme_kategorie, kategorien



def test_txt():
    result = bestimme_kategorie(Path("beispiel.txt"), kategorien)
    assert result == "texte"

def test_png():
    result = bestimme_kategorie(Path("bild.png"), kategorien)
    assert result == "bilder"

def test_unbekannt():
    result = bestimme_kategorie(Path("archiv.xyz"), kategorien)
    assert result == "sonstiges"

def test_datei_verschieben(tmp_path):
    ordner = tmp_path / "testdateien"
    ordner.mkdir()
    file_path = ordner / "meine_testdatei.txt"

    file_path.write_text("Hallo Welt", encoding="utf-8")
    organisiere_dateien(ordner, kategorien)
    ziel_ordner = ordner / "texte"
    ziel_datei = ziel_ordner / "meine_testdatei.txt"
    assert ziel_datei.exists()
    assert not file_path.exists()

def test_datei_existiert_bereits(tmp_path):
    ordner = tmp_path /"testdateien"
    ordner.mkdir()
    file_path = ordner / "meine_testdatei.txt"
    file_path.write_text("Neuer Inhalt", encoding="utf-8")
    zielordner = ordner / "texte"
    zielordner.mkdir()
    zieldatei = zielordner / "meine_testdatei.txt"
    zieldatei.write_text("Alter Inhalt", encoding="utf-8")
    organisiere_dateien(ordner, kategorien)
    assert file_path.exists()
    assert zieldatei.exists()
    assert file_path.read_text(encoding="utf-8") == "Neuer Inhalt"
    assert zieldatei.read_text(encoding="utf-8") == "Alter Inhalt"

def test_ordner_existiert_nicht(tmp_path):
    ordner = tmp_path/"testdateien"
    
    with pytest.raises(SystemExit):
        organisiere_dateien(ordner, kategorien)

def test_unterordner_ueberspringen(tmp_path):
    ordner = tmp_path / "testdateien"
    ordner.mkdir()
    unterordner = ordner / "unterordner"
    unterordner.mkdir()
    file_path = unterordner / "test.txt"
    file_path.write_text("testdatei", encoding="utf-8")

    organisiere_dateien(ordner, kategorien)
    ziel_datei = ordner / "texte" / "test.txt"
    assert not ziel_datei.exists()
    assert unterordner.exists()
    assert file_path.read_text(encoding="utf-8") == "testdatei"





    


import pytest
from unittest.mock import patch
from pathlib import Path
from main import organisiere_dateien, bestimme_kategorie

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
    
    with pytest.raises(SystemExit):
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

def test_verschieben_fehlschlag(quellordner, capsys):
    datei = quellordner / "fehler.txt"
    datei.write_text("fehler", encoding="utf-8")

    with patch("main.shutil.move", side_effect=OSError("Simulierter Fehler")):
        organisiere_dateien(quellordner, kategorien)

    captured = capsys.readouterr()
    assert "Simulierter Fehler" in captured.out
    assert datei.exists()

def test_ordner_erstellen_fehlschlag(quellordner, capsys):
    datei = quellordner / "test.txt"
    datei.write_text("INHALT", encoding="utf-8")

    with patch("pathlib.Path.mkdir", side_effect=OSError("Ordnerfehler")):
        organisiere_dateien(quellordner, kategorien)
    captured = capsys.readouterr()
    assert "Ordnerfehler" in captured.out
    assert datei.exists()

    



    


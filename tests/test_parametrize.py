import pytest
import json
from pathlib import Path
from main import bestimme_kategorie, lade_konfiguration

kategorien = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

@pytest.mark.parametrize("input1, expected", [("beispiel.txt", "texte"), ("bild.png", "bilder"), ("archive.xyz", "sonstiges")])
def test_txt(input1: str, expected: str):
    pfad = Path(input1)
    
    result = bestimme_kategorie(pfad, kategorien)
    assert result == expected

@pytest.mark.parametrize("input1", [{"ordner" : 123, "kategorien" : {".txt" : "texte"}}, {"ordner" : "testdateien", "kategorien" : ["werte"]}, {"ordner" : "", "kategorien" : {".txt" : "texte"}}, {"ordner" : "testdateien", "kategorien" : {"" : "texte"}}, {"ordner": "testdateien", "kategorien": {".txt": "   "}},
{"ordner" : "testdateien", "kategorien" : {".txt" : "../bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "C:\bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "C:bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "/bilder"}},  {"ordner" : "testdateien", "kategorien" : {".txt" : "bilder/texte"}},
 {"ordner" : "testdateien", "kategorien" : {".txt" : r"bilder\texte"}} ])
def test_konfiguration_ungueltige_werte(tmp_path, input1):
    configdatei = tmp_path / "config.json"
    beispiel = input1

    s = json.dumps(beispiel)
    configdatei.write_text(s, encoding="utf-8")

    with pytest.raises(ValueError):
        lade_konfiguration(configdatei)
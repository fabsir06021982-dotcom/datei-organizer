import pytest
import json
from pathlib import Path
from datei_organizer.main import determine_category, load_configuration

categories = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

@pytest.mark.parametrize("input1, expected", [("beispiel.txt", "texte"), ("bild.png", "bilder"), ("archive.xyz", None)])
def test_txt(input1: str, expected: None | str):
    path = Path(input1)

    result = determine_category(path, categories)
    assert result == expected

@pytest.mark.parametrize("input1", [{"ordner" : 123, "kategorien" : {".txt" : "texte"}}, {"ordner" : "testdateien", "kategorien" : ["werte"]}, {"ordner" : "", "kategorien" : {".txt" : "texte"}}, {"ordner": "testdateien", "kategorien": {".txt": "   "}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "../bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "C:\bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "C:bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "/bilder"}},  {"ordner" : "testdateien", "kategorien" : {".txt" : "bilder/texte"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : r"bilder\texte"}} ])
def test_invalid_configuration_values(tmp_path, input1):
    configuration_path = tmp_path / "config.json"
    sample_data = input1

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    with pytest.raises(ValueError):
        load_configuration(configuration_path)

def test_configuration_allows_extensionless_files(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner": "testdateien", "kategorien": {"": "texte"}}
    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    configuration = load_configuration(Path(configuration_path))
    assert configuration["kategorien"] == {"": "texte"}


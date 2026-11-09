import pytest
import logging
import shutil
import subprocess
import json
from unittest.mock import patch
from pathlib import Path
from datei_organizer.main import organize_files, determine_category, load_configuration

categories = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

def test_txt():
    result = determine_category(Path("beispiel.txt"), categories)
    assert result == "texte"

def test_png():
    result = determine_category(Path("bild.png"), categories)
    assert result == "bilder"

def test_unknown_extension():
    result = determine_category(Path("archiv.xyz"), categories)
    assert result == "sonstiges"

def test_move_file(source_folder):

    file_path = source_folder / "meine_testdatei.txt"

    file_path.write_text("Hallo Welt", encoding="utf-8")
    organize_files(source_folder, categories)
    destination_folder = source_folder / "texte"
    destination_file = destination_folder / "meine_testdatei.txt"
    assert destination_file.exists()
    assert not file_path.exists()

def test_destination_file_exists(source_folder):

    file_path = source_folder / "meine_testdatei.txt"
    file_path.write_text("Neuer Inhalt", encoding="utf-8")
    destination_folder = source_folder / "texte"
    destination_folder.mkdir()
    destination_file = destination_folder / "meine_testdatei.txt"
    destination_file.write_text("Alter Inhalt", encoding="utf-8")
    organize_files(source_folder, categories)
    assert file_path.exists()
    assert destination_file.exists()
    assert file_path.read_text(encoding="utf-8") == "Neuer Inhalt"
    assert destination_file.read_text(encoding="utf-8") == "Alter Inhalt"

def test_folder_does_not_exist(tmp_path):
    folder = tmp_path/"testdateien"

    with pytest.raises(FileNotFoundError):
        organize_files(folder, categories)

def test_skip_subfolders(source_folder):

    subfolder = source_folder / "unterordner"
    subfolder.mkdir()
    file_path = subfolder / "test.txt"
    file_path.write_text("testdatei", encoding="utf-8")

    organize_files(source_folder, categories)
    destination_file = source_folder / "texte" / "test.txt"
    assert not destination_file.exists()
    assert subfolder.exists()
    assert file_path.read_text(encoding="utf-8") == "testdatei"

@pytest.fixture
def source_folder(tmp_path):
    folder = tmp_path / "testdateien"
    folder.mkdir()
    return folder

def test_move_failure(source_folder, caplog):
    file_path = source_folder / "fehler.txt"
    file_path.write_text("fehler", encoding="utf-8")

    with patch("main.shutil.move", side_effect=OSError("Simulierter Fehler")):
        organize_files(source_folder, categories)


    assert "Simulierter Fehler" in caplog.text
    assert file_path.exists()

def test_create_folder_failure(source_folder, caplog):
    file_path = source_folder / "test.txt"
    file_path.write_text("INHALT", encoding="utf-8")

    with patch("pathlib.Path.mkdir", side_effect=OSError("Ordnerfehler")):
        organize_files(source_folder, categories)

    assert "Ordnerfehler" in caplog.text
    assert file_path.exists()

def test_load_configuration(tmp_path):
    configuration_path = tmp_path / "config.json"


    sample_configuration = { "ordner" : "testdateien", "kategorien" : {".txt" : "texte", ".png" : "bilder", ".jpg" : "bilder", ".pdf" : "dokumente"}}
    configuration_json = json.dumps(sample_configuration)

    configuration_path.write_text(configuration_json, encoding="utf-8")

    configuration = load_configuration(configuration_path)
    categories = configuration["kategorien"]
    folder = Path(configuration["ordner"])
    assert categories == {".txt" : "texte", ".png" : "bilder", ".jpg" : "bilder", ".pdf" : "dokumente"}
    assert folder == Path("testdateien")

def test_missing_configuration(tmp_path):
    configuration_path = tmp_path / "nicht_vorhanden.json"

    with pytest.raises(FileNotFoundError):
        load_configuration(configuration_path)

def test_invalid_configuration(tmp_path):
    configuration_path = tmp_path / "ungueltig.json"
    configuration_path.write_text(" ''''ungueltig", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_configuration(configuration_path)

def test_empty_categories(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_configuration = { "ordner": "testdateien", "kategorien" : {}}

    configuration_json = json.dumps(sample_configuration)
    configuration_path.write_text(configuration_json, encoding="utf-8")
  
    configuration = load_configuration(configuration_path)

    assert configuration["kategorien"] == {}
    assert configuration["ordner"] == "testdateien"


def test_configuration_root_type(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = ["testdateien", "texte"]

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    with pytest.raises(ValueError):
        load_configuration(configuration_path)

def test_missing_categories_key(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner" : "testdateien"}

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    with pytest.raises(ValueError):
        load_configuration(configuration_path)

def test_invalid_category_type(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner" : "testdateien", "kategorien" : {".txt" : 123}}

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    with pytest.raises(ValueError):
        load_configuration(configuration_path)

def test_empty_category_name(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner" : "testdateien", "kategorien" : {".txt" : ""}}

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    with pytest.raises(ValueError):
        load_configuration(configuration_path)

def test_symlink_outside_folder(tmp_path):
    working_directory = tmp_path / "arbeitsverzeichnis"
    external_directory = tmp_path / "extern"

    working_directory.mkdir()
    external_directory.mkdir()

    symlink = working_directory / "bilder"
    symlink.symlink_to(external_directory, target_is_directory=True)

    image_file = working_directory / "bild.png"
    image_file.write_text("Testinhalt", encoding="utf-8")

    with pytest.raises(ValueError):
        organize_files(working_directory, categories)

    assert image_file.exists()
    assert not (external_directory / "bild.png").exists()

def test_logging_info(caplog):
    logging.info("Testinformation")

    assert "Testinformation" in caplog.text
    assert caplog.records[0].levelname == "INFO"

def simulate_move_error(source, destination):
    raise OSError("Testfehler beim verschieben")

def test_log_move_error(monkeypatch, caplog, tmp_path):
    monkeypatch.setattr(shutil,"move", simulate_move_error)
    folder = tmp_path / "arbeitsverzeichnis"
    folder.mkdir()
    image_file = folder / "bild.png"
    image_file.write_text("Bsp", encoding="utf-8")

    organize_files(folder, categories)

    assert "Testfehler beim verschieben" in caplog.text
    assert any(entry.levelname == "ERROR" for entry in caplog.records)
    assert image_file.exists()

def test_cli_missing_configuration(tmp_path):
    folder = tmp_path / "arbeitsverzeichnis"
    folder.mkdir()
    main_file = Path.cwd() / "main.py"

    output = subprocess.run(["python", str(main_file)], cwd=folder, capture_output=True, text=True)
    assert output.returncode == 1
    assert "Datei nicht gefunden" in output.stdout

def test_cli_invalid_json(tmp_path):
    folder = tmp_path / "arbeitsverzeichnis"
    folder.mkdir()
    configuration_path = folder / "config.json"
    configuration_path.write_text("XYZ", encoding="utf-8")
    main_file = Path.cwd() / "main.py"

    output = subprocess.run(["python", str(main_file)], cwd=folder, capture_output=True, text=True)
    assert output.returncode == 1
    assert "JSON fehlerhaft" in output.stdout

def test_cli_invalid_configuration_values(tmp_path):
    working_directory = tmp_path / "arbeitsverzeichnis"
    working_directory.mkdir()
    configuration_path = working_directory / "config.json"
    sample_configuration = {"ordner": 123, "kategorien": {".txt": "texte"}}

    configuration_json = json.dumps(sample_configuration)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    main_file = Path.cwd() / "main.py"
    output = subprocess.run(["python", str(main_file)], cwd=working_directory, capture_output=True, text=True)
    assert output.returncode == 1
    assert "Werte in JSON nicht korrekt" in output.stdout

def test_cli_missing_working_directory(tmp_path):
    working_directory = tmp_path / "arbeitsverzeichnis"
    working_directory.mkdir()
    configuration_path = working_directory / "config.json"
    sample_configuration = {"ordner": "existiert_nicht", "kategorien": {".txt": "texte"}}

    configuration_json = json.dumps(sample_configuration)
    configuration_path.write_text(configuration_json, encoding="utf-8")

    main_file = Path.cwd() / "main.py"
    output = subprocess.run(["python", str(main_file)], cwd=working_directory, capture_output=True, text=True)
    assert output.returncode == 1
    assert "Arbeitsverzeichnis nicht gefunden" in output.stdout

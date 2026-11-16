import pytest
from pathlib import Path
import shutil
import logging
import json
from unittest.mock import patch
from datei_organizer.organize_service import OrganizeService

categories = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}


@pytest.fixture
def configured_workspace(tmp_path, monkeypatch) -> Path:
    working_directory = tmp_path / "arbeitsverzeichnis"
    working_directory.mkdir()
    test_folder = working_directory / "testdateien"
    test_folder.mkdir()
    configuration_path = working_directory / "config.json"
    sample_config = {"ordner": "testdateien", "kategorien": {".txt": "texte"}}
    configuration_json = json.dumps(sample_config)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    monkeypatch.chdir(working_directory)
    return working_directory


def test_move_file(source_folder):

    file_path = source_folder / "meine_testdatei.txt"

    file_path.write_text("Hallo Welt", encoding="utf-8")
    organize_service = OrganizeService()
    organize_service.organize_files(source_folder, categories)
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
    organize_service = OrganizeService()
    organize_service.organize_files(source_folder, categories)
    assert file_path.exists()
    assert destination_file.exists()
    assert file_path.read_text(encoding="utf-8") == "Neuer Inhalt"
    assert destination_file.read_text(encoding="utf-8") == "Alter Inhalt"

def test_folder_does_not_exist(tmp_path):
    folder = tmp_path/"testdateien"

    with pytest.raises(FileNotFoundError):
        organize_service = OrganizeService()
        organize_service.organize_files(folder, categories)

def test_skip_subfolders(source_folder):

    subfolder = source_folder / "unterordner"
    subfolder.mkdir()
    file_path = subfolder / "test.txt"
    file_path.write_text("testdatei", encoding="utf-8")
    organize_service = OrganizeService()
    organize_service.organize_files(source_folder, categories)
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

    with patch("datei_organizer.organize_service.shutil.move", side_effect=OSError("Simulierter Fehler")):
        organize_service = OrganizeService()
        organize_service.organize_files(source_folder, categories)


    assert "Simulierter Fehler" in caplog.text
    assert file_path.exists()

def test_create_folder_failure(source_folder, caplog):
    file_path = source_folder / "test.txt"
    file_path.write_text("INHALT", encoding="utf-8")

    with patch("pathlib.Path.mkdir", side_effect=OSError("Ordnerfehler")):
        organize_service = OrganizeService()
        organize_service.organize_files(source_folder, categories)

    assert "Ordnerfehler" in caplog.text
    assert file_path.exists()



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
        organize_service = OrganizeService()
        organize_service.organize_files(working_directory, categories)

    assert image_file.exists()
    assert not (external_directory / "bild.png").exists()


def test_logging_info(caplog):
    caplog.set_level(logging.INFO)
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
    organize_service = OrganizeService()
    organize_service.organize_files(folder, categories)

    assert "Testfehler beim verschieben" in caplog.text
    assert any(entry.levelname == "ERROR" for entry in caplog.records)
    assert image_file.exists()


def test_organize_files_returns_successful_moves(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    test_file_path1 = test_folder / "example1.txt"
    test_file_path1.write_text("example1", encoding="utf-8")
    test_file_path2 = test_folder / "example2.jpg"
    test_file_path2.write_text("example2", encoding="utf-8")
    categories = {".txt" : "texte", ".jpg" : "bilder"}
    organize_service = OrganizeService()    
    test_result = organize_service.organize_files(test_folder, categories)
    test_destination_path1 = test_folder / "texte" / "example1.txt"
    test_destination_path2 = test_folder / "bilder" / "example2.jpg"
    assert len(test_result) == 2
    assert "example1.txt" in test_result
    assert test_result["example1.txt"]["source"] == test_file_path1
    assert test_result["example1.txt"]["destination"] == test_destination_path1
    assert "example2.jpg" in test_result
    assert test_result["example2.jpg"]["source"] == test_file_path2
    assert test_result["example2.jpg"]["destination"] == test_destination_path2
    assert not test_file_path1.exists()
    assert not test_file_path2.exists()
    assert test_destination_path1.exists()
    assert test_destination_path2.exists()


@pytest.mark.parametrize("input1, expected", [("beispiel.txt", "texte"), ("bild.png", "bilder"), ("archive.xyz", None)])
def test_expected_categories(input1: str, expected: None | str):
    path = Path(input1)
    organize_service = OrganizeService()
    result = organize_service.determine_category(path, categories)
    assert result == expected

def test_txt():
    organize_service = OrganizeService()
    result = organize_service.determine_category(Path("beispiel.txt"), categories)
    assert result == "texte"

def test_png():
    organize_service = OrganizeService()
    result = organize_service.determine_category(Path("bild.png"), categories)
    assert result == "bilder"

def test_unknown_extension():
    organize_service = OrganizeService()
    result = organize_service.determine_category(Path("archiv.xyz"), categories)
    assert result is None
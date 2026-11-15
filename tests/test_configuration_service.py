import pytest
import json
from pathlib import Path
from datei_organizer.configuration_service import ConfigurationService


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


def test_save_configuration(configured_workspace):
    sample_config_path = configured_workspace / "config.json"
    new_config = {"ordner" : "neuerordner", "kategorien" : {".xyz" : "archiv"}}
    config_service = ConfigurationService()
    config_service.save_configuration(sample_config_path, new_config)
    with open(sample_config_path, "r", encoding="utf-8") as conf_file:
        data = json.load(conf_file)
    assert data == new_config
    assert sample_config_path.exists()


def test_save_invalid_configuration_value(configured_workspace):
    sample_config_path = configured_workspace / "config.json"
    false_config = {"ordner" : Path("testdateien"), "kategorien" : {".xyz" : "archiv"}}
    original_content = sample_config_path.read_text(encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(TypeError):
        config_service.save_configuration(sample_config_path, false_config)
    assert sample_config_path.read_text(encoding="utf-8") == original_content


def test_save_invalid_destination_path(configured_workspace):
    folder_path = configured_workspace / "testdateien"
    sample_config_path = configured_workspace / "config.json"
    valid_config = {"ordner" : "neuerordner", "kategorien" : {".xyz" : "archiv"}}
    original_content = sample_config_path.read_text(encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(OSError):
        config_service.save_configuration(folder_path, valid_config)
    assert folder_path.is_dir()
    assert sample_config_path.read_text(encoding="utf-8") == original_content


def test_load_configuration(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_configuration = { "ordner" : "testdateien", "kategorien" : {".txt" : "texte", ".png" : "bilder", ".jpg" : "bilder", ".pdf" : "dokumente"}}
    configuration_json = json.dumps(sample_configuration)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    categories = configuration["kategorien"]
    folder = Path(configuration["ordner"])
    assert categories == {".txt" : "texte", ".png" : "bilder", ".jpg" : "bilder", ".pdf" : "dokumente"}
    assert folder == Path("testdateien")

def test_missing_configuration(tmp_path):
    configuration_path = tmp_path / "nicht_vorhanden.json"
    config_service = ConfigurationService()
    with pytest.raises(FileNotFoundError):
        config_service.load_configuration(configuration_path)

def test_invalid_configuration(tmp_path):
    configuration_path = tmp_path / "ungueltig.json"
    configuration_path.write_text(" ''''ungueltig", encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(json.JSONDecodeError):
        config_service.load_configuration(configuration_path)

def test_empty_categories(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_configuration = { "ordner": "testdateien", "kategorien" : {}}

    configuration_json = json.dumps(sample_configuration)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
  
    configuration = config_service.load_configuration(configuration_path)

    assert configuration["kategorien"] == {}
    assert configuration["ordner"] == "testdateien"


def test_configuration_root_type(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = ["testdateien", "texte"]

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(ValueError):
        config_service.load_configuration(configuration_path)

def test_missing_categories_key(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner" : "testdateien"}

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(ValueError):
        config_service.load_configuration(configuration_path)

def test_invalid_category_type(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner" : "testdateien", "kategorien" : {".txt" : 123}}

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(ValueError):
        config_service.load_configuration(configuration_path)

def test_empty_category_name(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner" : "testdateien", "kategorien" : {".txt" : ""}}

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(ValueError):
        config_service.load_configuration(configuration_path)


@pytest.mark.parametrize("input1", [{"ordner" : 123, "kategorien" : {".txt" : "texte"}}, {"ordner" : "testdateien", "kategorien" : ["werte"]}, {"ordner" : "", "kategorien" : {".txt" : "texte"}}, {"ordner": "testdateien", "kategorien": {".txt": "   "}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "../bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "C:\bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "C:bilder"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : "/bilder"}},  {"ordner" : "testdateien", "kategorien" : {".txt" : "bilder/texte"}}, {"ordner" : "testdateien", "kategorien" : {".txt" : r"bilder\texte"}} ])
def test_invalid_configuration_values(tmp_path, input1):
    configuration_path = tmp_path / "config.json"
    sample_data = input1

    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    with pytest.raises(ValueError):
        config_service.load_configuration(configuration_path)


def test_configuration_allows_extensionless_files(tmp_path):
    configuration_path = tmp_path / "config.json"
    sample_data = {"ordner": "testdateien", "kategorien": {"": "texte"}}
    configuration_json = json.dumps(sample_data)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(Path(configuration_path))
    assert configuration["kategorien"] == {"": "texte"}

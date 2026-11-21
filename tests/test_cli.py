
from pathlib import Path
import pytest
import subprocess
import sys
import json
from typer.testing import CliRunner
from datei_organizer.cli import app
from datei_organizer.configuration_service import ConfigurationService

runner = CliRunner()


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

def test_cli_analysis_declined_keeps_configuration_unchanged(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    txt_file_path = test_folder / "sample.txt"
    txt_file_path.write_text("das ist eine testdatei", encoding="utf-8")
    configuration_path = configured_workspace / "config.json"
    expected_configuration = {"ordner": "testdateien", "kategorien": {".txt": "texte"}}
    result = runner.invoke(app, ["analyse"], input="\nn\n")
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    assert result.exit_code == 0
    assert "Kategoriezuordnungen werden nicht bearbeitet. Ende." in result.output
    assert txt_file_path.exists()
    assert "Analyseergebnis" in result.output
    assert configuration == expected_configuration
    assert txt_file_path.read_text(encoding="utf-8") == "das ist eine testdatei"

def test_cli_analysis_saves_new_assignment(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    xyz_file_path = test_folder / "sample.xyz"
    xyz_file_path.touch()
    configuration_path = configured_workspace / "config.json"
    result = runner.invoke(app, ["analyse"], input="\ny\ny\nn\narchive\ny\n")
    assert result.exit_code == 0
    assert "Erfolgreich gespeichert" in result.output
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    assert configuration["kategorien"][".xyz"] == "archive"
    assert configuration["kategorien"][".txt"] == "texte"
    assert configuration["ordner"] == "testdateien"
    assert xyz_file_path.exists()

def test_cli_analysis_declined_save_keeps_configuration_unchanged(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    xyz_file_path = test_folder / "sample.xyz"
    xyz_file_path.touch()
    configuration_path = configured_workspace/ "config.json"
    result = runner.invoke(app, ["analyse"], input="\ny\ny\nn\narchive\nn\n")
    expected_configuration = {"ordner": "testdateien", "kategorien": {".txt": "texte"}}
    assert result.exit_code == 0
    assert "Neue Zuordnungen werden nicht gespeichert. Abbruch." in result.output
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    assert configuration == expected_configuration
    assert xyz_file_path.exists()

def test_cli_analysis_saves_removed_assignment(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    test_file_path = test_folder / "test.txt"
    test_file_path.write_text("Testdatei", encoding="utf-8")
    configuration_path = configured_workspace / "config.json"
    result = runner.invoke(app, ["analyse"], input="\ny\ny\ny\ny\n")
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    assert "Erfolgreich gespeichert" in result.output
    assert result.exit_code == 0
    assert configuration == {"ordner": "testdateien", "kategorien": {}}
    assert test_file_path.exists()

def test_cli_analysis_retries_invalid_category(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    xyz_file_path = test_folder / "test.xyz"
    xyz_file_path.write_text("Testdatei", encoding="utf-8")
    configuration_path = configured_workspace / "config.json"
    result = runner.invoke(app, ["analyse"], input="\ny\ny\nn\n../archive\narchive\ny\n")
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    assert "Erfolgreich gespeichert" in result.output
    assert result.exit_code == 0
    assert "Pfadangabe enthalten" in result.output
    assert configuration == {"ordner": "testdateien", "kategorien": {".txt": "texte", ".xyz": "archive"}}
    assert xyz_file_path.exists()

def test_cli_analysis_keeps_assignment_after_three_invalid_attempts(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    configuration_path = configured_workspace / "config.json"
    expected_configuration = {"ordner": "testdateien", "kategorien": {".txt": "texte"}}
    txt_file_path = test_folder / "test.txt"
    txt_file_path.write_text("Testdatei", encoding="utf-8")
    result = runner.invoke(app, ["analyse"], input="\ny\ny\nn\n../texte\nC:\\texte\n.\ny\n")
    config_service = ConfigurationService()
    configuration = config_service.load_configuration(configuration_path)
    assert "Keinen gültigen Ordnernamen eingegeben." in result.output
    assert "Pfadangabe enthalten" in result.output
    assert result.exit_code == 0
    assert configuration == expected_configuration
    assert txt_file_path.exists()


def test_cli_sorting_declined_keeps_files_unchanged(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    txt_file_path = test_folder / "example.txt"
    txt_file_path.write_text("Hallo. Das ist eine Testdatei", encoding="utf-8")
    result = runner.invoke(app, ["sortiere"], input="\nn\n")
    assert result.exit_code == 0
    assert "Sortiervorgang abgebrochen" in result.output
    assert txt_file_path.exists()
    assert txt_file_path.read_text(encoding="utf-8") == "Hallo. Das ist eine Testdatei"
    assert not (test_folder / "texte" / "example.txt").exists()


def test_cli_sorting_files_success(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    txt_file_path = test_folder / "example.txt"
    txt_file_path.write_text("Hallo. Das ist eine Testdatei", encoding="utf-8")
    result = runner.invoke(app, ["sortiere"], input="\ny\n")
    assert result.exit_code == 0
    assert "Sortierdurchlauf beendet." in result.output
    assert "Verschoben" in result.output
    assert not txt_file_path.exists()
    destination = (test_folder / "texte" / "example.txt")
    assert destination.read_text(encoding="utf-8") == "Hallo. Das ist eine Testdatei"
    assert destination.exists()
    assert "example.txt" in result.output
    assert "texte\\example.txt" in result.output

def test_move_with_unique_name_uses_next_free_number_when_number_two_is_taken(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    test_file_path = test_folder / "bericht.txt"
    destination_path = test_folder / "texte"
    destination_path.mkdir()
    test_file_path.write_text("Hallo. Das ist eine Testdatei", encoding="utf-8")
    destination_file1 = (test_folder / "texte" / "bericht.txt")
    destination_file2 = (test_folder / "texte" / "bericht_2.txt")
    destination_file1.write_text("Datei1", encoding="utf-8")
    destination_file2.write_text("Datei2", encoding="utf-8")
    result = runner.invoke(app, ["sortiere"], input="\ny\nvielleicht\nJa\n")
    assert result.exit_code == 0
    assert not test_file_path.exists()
    assert destination_file1.read_text(encoding="utf-8") == "Datei1"
    assert destination_file2.read_text(encoding="utf-8") == "Datei2"
    assert destination_file1.exists()
    assert destination_file2.exists()
    destination_file3 = (test_folder / "texte" / "bericht_3.txt")
    assert destination_file3.read_text(encoding="utf-8") == "Hallo. Das ist eine Testdatei"
    assert destination_file3.exists()

def test_cli_sorting_files_name_conflict(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    txt_file_path = test_folder / "example.txt"
    destination_path = test_folder / "texte"
    destination_path.mkdir()
    txt_file_path.write_text("Hallo. Das ist eine Testdatei", encoding="utf-8")
    destination = (test_folder / "texte" / "example.txt")
    destination.write_text("Alte Datei", encoding="utf-8")
    result = runner.invoke(app, ["sortiere"], input="\ny\nvielleicht\nNein\n")
    assert result.exit_code == 0
    assert "Übersprungen" in result.output
    assert "example.txt" in result.output
    assert "texte\\example.txt" in result.output
    assert txt_file_path.exists()
    assert txt_file_path.read_text(encoding="utf-8") == "Hallo. Das ist eine Testdatei"
    assert destination.read_text(encoding="utf-8") == "Alte Datei"
    assert (test_folder / "texte" / "example.txt").exists()

def test_cli_sorting_displays_relative_paths_for_external_folder(tmp_path, configured_workspace):
    test_folder = tmp_path / "verzeichnis"
    test_folder.mkdir()
    txt_file_path = test_folder / "example.txt"
    txt_file_path.write_text("Hallo. Das ist eine Testdatei", encoding="utf-8")
    configuration_path = configured_workspace / "config.json"
    sample_config = {"ordner": str(test_folder), "kategorien": {".txt": "texte"}}
    configuration_json = json.dumps(sample_config)
    configuration_path.write_text(configuration_json, encoding="utf-8")
    result = runner.invoke(app, ["sortiere"], input="\ny\n")
    assert result.exit_code == 0
    assert "Sortierdurchlauf beendet." in result.output
    assert not txt_file_path.exists()
    destination = (test_folder / "texte" / "example.txt")
    assert destination.read_text(encoding="utf-8") == "Hallo. Das ist eine Testdatei"
    assert destination.exists()
    assert "example.txt" in result.output
    assert "texte\\example.txt" in result.output


def test_cli_analyze_empty_folder(configured_workspace):
    empty_folder = configured_workspace / "testdateien"
    result = runner.invoke(app, ["analyse"], input="\n")
    assert result.exit_code == 0
    assert "Im ausgewählten Ordner wurden keine Dateien gefunden." in result.output
    assert "Möchtest du die Kategoriezuordnungen bearbeiten?" not in result.output
    assert empty_folder.exists()
    assert not list(empty_folder.iterdir())


def test_cli_analysis_uses_selected_configuration(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    test_file_path = test_folder / "example.txt"
    test_file_path.write_text("Beispieldatei", encoding="utf-8")
    alternative_configuration_path = configured_workspace / "alternative_config.json" 
    empty_folder = configured_workspace / "empty"
    empty_folder.mkdir()
    alternative_configuration = {"ordner": "empty", "kategorien" : {".txt": "texte"}}
    configuration_json = json.dumps(alternative_configuration)
    alternative_configuration_path.write_text(configuration_json, encoding="utf-8")
    result = runner.invoke(app, ["analyse", "--config", str(alternative_configuration_path)], input="\n")
    assert result.exit_code == 0
    assert "Im ausgewählten Ordner wurden keine Dateien gefunden." in result.output

def test_cli_sorting_uses_selected_configuration(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    txt_file_path = test_folder / "beispiel.txt"
    txt_file_path.write_text("Innerhalb der Beispieldatei", encoding="utf-8")
    alternative_configuration_path = test_folder / "alternative_config.json"
    alternative_configuration = {"ordner": "testdateien", "kategorien": {".txt": "archive"}}
    alternative_configuration_json = json.dumps(alternative_configuration)
    alternative_configuration_path.write_text(alternative_configuration_json, encoding="utf-8")
    default_destination_path = test_folder / "texte" / "beispiel.txt"
    alternative_destination_path = test_folder / "archive" / "beispiel.txt"
    result = runner.invoke(app, ["sortiere", "--config", str(alternative_configuration_path)], input="\ny\n")
    assert result.exit_code == 0
    assert not txt_file_path.exists()
    assert alternative_destination_path.is_file()
    assert alternative_destination_path.read_text(encoding="utf-8") == "Innerhalb der Beispieldatei"
    assert not default_destination_path.exists()

def test_cli_analysis_missing_selected_configuration(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    configuration_path = test_folder / "config.json"
    result = runner.invoke(app, ["analyse", "--config", str(configuration_path)], input="")
    assert result.exit_code == 1
    assert "Config Datei nicht gefunden" in result.output
    assert "Neuen Ordner eingeben oder Enter ⏎ für den Standardordner" not in result.output
    assert str(configuration_path) in result.output

def test_cli_sorting_missing_selected_configuration(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    configuration_path = test_folder / "config.json"
    result = runner.invoke(app, ["sortiere", "--config", str(configuration_path)], input="")
    assert result.exit_code == 1
    assert "Config Datei nicht gefunden" in result.output
    assert "Neuen Ordner eingeben oder Enter ⏎ für den Standardordner" not in result.output
    assert str(configuration_path) in result.output

def test_cli_analysis_invalid_json_reports_error(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    alternative_configuration_path = test_folder / "alternative_config.json"
    alternative_configuration = "{"
    alternative_configuration_path.write_text(alternative_configuration, encoding="utf-8")
    result = runner.invoke(app, ["analyse", "--config", str(alternative_configuration_path)], input="")
    assert result.exit_code == 1
    assert "Ungültiges JSON" in result.output
    assert str(alternative_configuration_path) in result.output
    assert "Neuen Ordner eingeben" not in result.output

def test_cli_analysis_invalid_configuration_reports_error(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    alternative_configuration_path = test_folder / "alternative_config.json"
    alternative_configuration = {"ordner": "testdateien", "kategorien": []}
    alternative_configuration_json = json.dumps(alternative_configuration)
    alternative_configuration_path.write_text(alternative_configuration_json, encoding="utf-8")
    result = runner.invoke(app, ["analyse", "--config", str(alternative_configuration_path)], input="")
    assert result.exit_code == 1
    assert "Ungültige Konfiguration" in result.output
    assert str(alternative_configuration_path) in result.output
    assert "Neuen Ordner eingeben oder Enter ⏎ für den Standardordner" not in result.output

def test_cli_analysis_permission_denied_reports_error(configured_workspace, monkeypatch):
    configuration_path = configured_workspace / "config.json"

    def deny_configuration_access(self, configuration_path):
        raise PermissionError
    monkeypatch.setattr(ConfigurationService, "load_configuration", deny_configuration_access)
    result = runner.invoke(app, ["analyse", "--config", str(configuration_path)], input="")
    assert result.exit_code == 1
    assert "Zugriff verweigert" in result.output
    assert str(configuration_path) in result.output
    assert "Neuen Ordner eingeben" not in result.output
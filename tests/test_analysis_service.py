from datei_organizer.analysis_service import AnalysisService
import pytest
import json
from unittest.mock import patch
from pathlib import Path

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


def test_analysis_ignores_files_in_subfolders(configured_workspace):
    test_folder = configured_workspace / "testdateien"
    subfolder = test_folder / "unterordner"
    subfolder.mkdir()
    txt_file_path = test_folder / "example1.txt"
    txt_file_path.write_text("example1", encoding="utf-8")
    pdf1_file_path = subfolder / "example2.pdf"
    pdf1_file_path.write_text("example2", encoding="utf-8")
    pdf2_file_path = subfolder / "example3.pdf"
    pdf2_file_path.write_text("example3", encoding="utf-8")
    sample_config = {"ordner": test_folder, "kategorien": {".txt": "texte"}}
    analysis_service = AnalysisService()
    analysis_dict = analysis_service.analyze_files(test_folder, sample_config["kategorien"])
    percentages = analysis_service.calculate_percentages(analysis_dict)   
    assert percentages[".txt"] == 100
    assert analysis_dict[".txt"]["anzahl"] == 1
    assert len(analysis_dict) == 1


def test_analysis_lower_case_file_extensions(configured_workspace):
    working_directory = configured_workspace / "testdateien"
    test_file1 = working_directory / "example1.TXT"
    test_file2 = working_directory / "example2.JPG"
    test_file1.write_text("example1", encoding="utf-8")
    test_file2.write_text("example2", encoding="utf-8")
    categories = {".txt" : "texte", ".jpg" : "bilder"}
    analysis_service = AnalysisService()
    result = analysis_service.analyze_files(working_directory, categories)
    assert ".txt" in result
    assert result[".txt"]["anzahl"] == 1
    assert result[".txt"]["kategorie"] == "texte"
    assert ".jpg" in result
    assert result[".jpg"]["anzahl"] == 1
    assert result[".jpg"]["kategorie"] == "bilder"


def test_analysis_category_assignments(configured_workspace):
    working_dir = configured_workspace / "testdateien"
    test_file1 = working_dir / "example1.txt"
    test_file2 = working_dir / "example2.jpg"
    test_file1.write_text("example1", encoding="utf-8")
    test_file2.write_text("example2", encoding="utf-8")
    categories = {".txt" : "texte"} 
    analysis_service = AnalysisService()
    result = analysis_service.analyze_files(working_dir, categories) 
    assert result[".txt"]["kategorie"] == "texte"
    assert result[".jpg"]["kategorie"] == None


def test_analysis_percentage_calculation(configured_workspace):
    working_dir = configured_workspace / "testdateien"
    test_file1 = working_dir / "example1.txt"
    test_file2 = working_dir / "example2.txt"
    test_file3 = working_dir / "example3.pdf"
    test_file1.write_text("example1", encoding="utf-8")
    test_file2.write_text("example2", encoding="utf-8")
    test_file3.write_text("example3", encoding="utf-8")
    categories = {".txt" : "texte", ".pdf" : "dokumente"} 
    analysis_service = AnalysisService()
    result = analysis_service.analyze_files(working_dir, categories)
    percentages = analysis_service.calculate_percentages(result)
    txt_percentage = 2 / 3 * 100
    pdf_percentage = 1 / 3 * 100
    assert txt_percentage == percentages[".txt"]
    assert pdf_percentage == percentages[".pdf"]



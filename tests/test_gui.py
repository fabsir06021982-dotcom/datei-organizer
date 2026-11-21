import gc
import time
import pytest
import tkinter as tk
from pathlib import Path
import json
from unittest.mock import patch
from datei_organizer.gui import OrganizerGUI
from datei_organizer.configuration_service import ConfigurationService

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

@pytest.fixture(scope="module")
def tk_session():
    # ttkbootstrap shares theme resources for the life of a Tcl interpreter.
    app = tk.Tk()
    app.withdraw()
    yield app
    app.destroy()


@pytest.fixture
def root(tk_session):
    # Finalize widgets from previous tests on the thread that owns Tk.
    gc.collect()
    window = tk.Toplevel(tk_session)
    yield window
    window.destroy()


def wait_for_job(gui):
    deadline = time.monotonic() + 10
    while gui.job.busy:
        gui.root.update()
        assert time.monotonic() < deadline
        time.sleep(0.005)


def test_gui_skips_conflicting_file_and_shows_empty_destination(configured_workspace, root):
    test_folder = configured_workspace / "testdateien"
    dest_path = test_folder / "texte"
    dest_path.mkdir()
    dest_file = dest_path / "bericht.txt"
    dest_file.write_text("Alt", encoding="utf-8")
    test_file = test_folder / "bericht.txt"
    test_file.write_text("Neu", encoding="utf-8")
    configuration = {"ordner": "testdateien", "kategorien": {".txt": "texte"}}    
    gui = OrganizerGUI(root, configuration)
    gui.selected_folder = test_folder 
    with patch("datei_organizer.gui.messagebox.askyesno", return_value=False) as conflict_dialog:
        gui.sort_files()
        wait_for_job(gui)
        conflict_dialog.assert_not_called()
        gui.start_sort_button.invoke()
        wait_for_job(gui)
        conflict_dialog.assert_called_once()
    row_ids = gui.sorting_tree.get_children()
    assert len(row_ids) == 1
    filename, source, destination, status, detail = gui.sorting_tree.item(row_ids[0], "values")
    assert filename == "bericht.txt"
    assert destination == ""
    assert status == "Übersprungen"
    assert dest_file.exists()
    assert test_file.read_text(encoding="utf-8") == "Neu"
    assert dest_file.read_text(encoding="utf-8") == "Alt"


def test_gui_keeps_both_files_and_shows_numbered_destination(configured_workspace, root):
    test_folder = configured_workspace / "testdateien"
    dest_path = test_folder / "texte"
    dest_path.mkdir()
    dest_file = dest_path / "bericht.txt"
    dest_file.write_text("Alt", encoding="utf-8")
    test_file = test_folder / "bericht.txt"
    test_file.write_text("Neu", encoding="utf-8")
    configuration = {"ordner": "testdateien", "kategorien": {".txt": "texte"}}    
    gui = OrganizerGUI(root, configuration)
    gui.selected_folder = test_folder 
    with patch("datei_organizer.gui.messagebox.askyesno", return_value=True) as conflict_dialog:
        gui.sort_files()
        wait_for_job(gui)
        conflict_dialog.assert_not_called()
        gui.start_sort_button.invoke()
        wait_for_job(gui)
        conflict_dialog.assert_called_once()
    row_ids = gui.sorting_tree.get_children()
    assert len(row_ids) == 1
    filename, source, destination, status, detail = gui.sorting_tree.item(row_ids[0], "values")
    assert filename == "bericht.txt"
    expected_destination = dest_path / "bericht_2.txt"
    assert Path(destination) == expected_destination
    assert status == "Verschoben"
    assert dest_file.read_text() == "Alt"
    assert Path(destination).read_text() == "Neu"
    assert not Path(source).exists()


def test_cancel_preview_preserves_source_and_missing_target_folder(configured_workspace, root):
    folder = configured_workspace / "testdateien"
    source = folder / "bericht.txt"
    source.write_text("Neu")
    gui = OrganizerGUI(root, {"ordner": str(folder), "kategorien": {".txt": "texte"}})
    gui.selected_folder = folder
    with patch("datei_organizer.gui.messagebox.askyesno") as dialog:
        gui.sort_files()
        wait_for_job(gui)
        gui.cancel_preview_button.invoke()
        dialog.assert_not_called()
    assert source.read_text() == "Neu"
    assert not (folder / "texte").exists()


def test_settings_view_persists_theme_and_scan_rules(configured_workspace, root):
    config_path = configured_workspace / "config.json"
    gui = OrganizerGUI(root, ConfigurationService().load_configuration(config_path), config_path)
    gui.page("Einstellungen")
    gui.variables["recursive"].set(True)
    gui.variables["max_depth"].set("1")
    gui.variables["theme"].set("bootstrap-light")
    gui.variables["conflict"].set("Umbenennen")
    gui.save_settings()
    saved = ConfigurationService().load_configuration(config_path)["optionen"]
    assert saved["recursive"] and saved["max_depth"] == 1
    assert saved["conflict"] == "rename" and gui.style.theme.name == "bootstrap-light"


def test_gui_analysis_can_be_cancelled_while_worker_runs(configured_workspace, root, monkeypatch):
    from threading import Event
    from datei_organizer.analysis_service import AnalysisService
    started = Event()
    def analyze(self, folder, categories, options, *, cancelled, progress, on_error, protected_paths):
        started.set()
        deadline = time.monotonic() + 5
        while not cancelled() and time.monotonic() < deadline:
            time.sleep(0.005)
        assert cancelled()
        return {}
    monkeypatch.setattr(AnalysisService, "analyze_files", analyze)
    gui = OrganizerGUI(root, {"ordner": str(configured_workspace), "kategorien": {}})
    gui.selected_folder = configured_workspace
    gui.analyze_folder()
    deadline = time.monotonic() + 10
    while not started.is_set():
        gui.root.update()
        assert time.monotonic() < deadline
        time.sleep(0.005)
    gui.abort.invoke()
    wait_for_job(gui)
    assert "Abgebrochen" in gui.status.get()

def test_start_navigation_follows_folder_analysis_and_results(configured_workspace, root):
    folder = configured_workspace / "testdateien"
    (folder / "example.txt").write_text("Inhalt")
    gui = OrganizerGUI(root, {"ordner": str(folder), "kategorien": {".txt": "texte"}})
    assert gui.selected_folder is None
    assert gui.navigation["Einstellungen"].instate(["!disabled"])
    assert all(gui.navigation[n].instate(["disabled"]) for n in ("Analyse", "Zuordnungen", "Ergebnisse"))
    with patch("datei_organizer.gui.filedialog.askdirectory", return_value=str(folder)):
        gui.select_folder()
    assert gui.navigation["Analyse"].instate(["!disabled"])
    assert gui.sort.instate(["disabled"])
    gui.analyze_folder()
    wait_for_job(gui)
    assert gui.navigation["Zuordnungen"].instate(["!disabled"])
    assert gui.sort.instate(["!disabled"])
    gui.sort_files()
    wait_for_job(gui)
    gui.start_sort_button.invoke()
    wait_for_job(gui)
    assert gui.navigation["Ergebnisse"].instate(["!disabled"])
    with patch("datei_organizer.gui.filedialog.askdirectory", return_value=str(configured_workspace)):
        gui.select_folder()
    assert gui.navigation["Ergebnisse"].instate(["disabled"])
    assert gui.current_page == "Start" and not gui.sorting_tree.get_children()

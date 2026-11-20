import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from datei_organizer.analysis_service import AnalysisService
from datei_organizer.cli import app
from datei_organizer.configuration_service import ConfigurationService
from datei_organizer.organize_service import OrganizeService
from datei_organizer.scanning import Options

CATEGORIES = {".txt": "Text"}


@pytest.fixture
def folder(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    return root


def put(root, name, content="data"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_recursive_filters_and_boundaries(folder):
    options = Options(recursive=True, max_depth=1, extensions="TXT", min_bytes=4, max_bytes=4,
                      modified_from="2024-01-02", modified_until="2024-01-02")
    for name in ("sub/ok.txt", "sub/ok.jpg", "sub/nested/deep.txt", ".hidden.txt", "Text/sorted.txt"):
        path = put(folder, name)
        stamp = datetime(2024, 1, 2, 12).timestamp()
        os.utime(path, (stamp, stamp))
    put(folder, "sub/small.txt", "x")
    put(folder, "sub/recent.txt")
    assert set(OrganizeService().preview_sorting(folder, CATEGORIES, options)) == {str(Path("sub/ok.txt"))}
    assert AnalysisService().analyze_files(folder, CATEGORIES, options)[".txt"]["anzahl"] == 1
    assert ".hidden.txt" in OrganizeService().preview_sorting(folder, CATEGORIES, Options(hidden=True))


@pytest.mark.parametrize("policy,layout,status", [("rename", False, "moved"), ("skip", False, "skipped"),
                                                  ("skip", True, "moved")])
def test_recursive_layout_and_conflicts(folder, policy, layout, status):
    for sub in ("a", "b"):
        put(folder, sub + "/x.txt", sub)
    service = OrganizeService()
    plan = service.preview_sorting(folder, CATEGORIES, Options(recursive=True, preserve_structure=layout))
    assert len(plan) == 2
    result = service.organize_files(folder, plan, conflict=policy)
    assert list(result.values())[1]["status"] == status
    expected = ["Text/a/x.txt", "Text/b/x.txt"] if layout else ["Text/x.txt"]
    if policy == "rename":
        expected += ["Text/x_2.txt"]
    assert all((folder / path).is_file() for path in expected)


def test_cancel_after_one_move_then_undo(folder):
    for name in ("a.txt", "b.txt"):
        put(folder, name, name)
    service = OrganizeService()
    plan = service.preview_sorting(folder, CATEGORIES)
    updates = []
    result = service.organize_files(folder, plan, cancelled=lambda: bool(updates),
                                    progress=lambda *args: updates.append(args))
    assert sorted(row["status"] for row in result.values()) == ["cancelled", "moved"]
    assert len(OrganizeService().undo(folder)) == 1
    assert all((folder / name).read_text() == name for name in plan)


@pytest.mark.parametrize("change", ["target", "source"])
def test_undo_refuses_unsafe_restore(folder, change):
    source = put(folder, "x.txt")
    service = OrganizeService()
    result = service.organize_files(folder, service.preview_sorting(folder, CATEGORIES))
    target = result["x.txt"]["destination"]
    (target if change == "target" else source).write_text("edited")
    row, = service.undo(folder).values()
    assert row["status"] == "failed"
    assert target.exists()
    assert (target if change == "target" else source).read_text() == "edited"


def test_replaced_target_directory_is_rejected(folder, tmp_path):
    source = put(folder, "x.txt")
    service = OrganizeService()
    plan = service.preview_sorting(folder, CATEGORIES)
    outside = tmp_path / "outside"
    outside.mkdir()
    (folder / "Text").symlink_to(outside, target_is_directory=True)
    assert service.organize_files(folder, plan)["x.txt"]["status"] == "failed"
    assert source.exists() and not list(outside.iterdir())


def test_unreadable_subtree_is_reported(folder):
    put(folder, "denied/x.txt")
    real_scan = os.scandir
    def restricted(path):
        if Path(path).name == "denied":
            raise PermissionError("locked")
        return real_scan(path)
    with patch("datei_organizer.scanning.os.scandir", restricted):
        plan = OrganizeService().preview_sorting(folder, CATEGORIES, Options(recursive=True))
    assert plan["denied"]["status"] == "failed"


def test_cli_dry_run_uses_saved_options(folder, tmp_path):
    source = put(folder, "sub/x.txt")
    config = tmp_path / "config.json"
    ConfigurationService().save_configuration(config, dict(ordner=str(folder), kategorien=CATEGORIES,
        optionen=dict(recursive=True, preserve_structure=True, logging=False)))
    run = CliRunner().invoke(app, ["sortiere", "--dry-run", "--config", str(config)], input="\n")
    assert run.exit_code == 0, run.exception
    assert "Sortiervorschau" in run.output and "x.txt" in run.output
    assert source.exists() and not (folder / "Text").exists()


@pytest.mark.parametrize("settings", [{"max_depth": -1}, {"recursive": 1}, {"min_bytes": 4, "max_bytes": 2},
                                      {"modified_from": "ungültig"}, {"conflict": "overwrite"}])
def test_invalid_options_are_rejected(settings):
    with pytest.raises(ValueError):
        Options.load(settings)



def test_settings_logging_switch_and_persistence(tmp_path, monkeypatch):
    from datei_organizer.log_service import configure_logging, log
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.json"
    values = {"recursive": True, "max_depth": 2, "logging": False, "conflict": "skip"}
    ConfigurationService().save_configuration(config, dict(ordner=".", kategorien=CATEGORIES, optionen=values))
    saved = Options.load(ConfigurationService().load_configuration(config)["optionen"])
    assert saved.max_depth == 2 and saved.recursive and saved.conflict == "skip"
    configure_logging(True)
    log.info("visible-first")
    configure_logging(saved.logging)
    log.warning("disabled-second")
    output = (tmp_path / "Hauptlog.log").read_text(encoding="utf-8")
    assert "visible-first" in output and "disabled-second" not in output


@pytest.mark.skipif(os.name != "nt", reason="Windows junction")
def test_windows_junction_is_not_traversed(folder, tmp_path):
    import subprocess
    outside = tmp_path / "external"
    put(outside, "private.txt")
    link = folder / "junction"
    subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
    assert OrganizeService().preview_sorting(folder, CATEGORIES, Options(recursive=True)) == {}
    assert (outside / "private.txt").read_text() == "data"


def test_cli_undo_restores_journalled_run(folder, tmp_path):
    source = put(folder, "note.txt")
    config = tmp_path / "settings.json"
    ConfigurationService().save_configuration(config, dict(ordner=str(folder), kategorien=CATEGORIES,
                                                           optionen={"logging": False}))
    runner = CliRunner()
    moved = runner.invoke(app, ["sortiere", "--config", str(config)], input="\ny\n")
    assert moved.exit_code == 0 and not source.exists()
    undone = runner.invoke(app, ["rueckgaengig", "--config", str(config)], input="\ny\n")
    assert undone.exit_code == 0 and "Zurückgenommen" in undone.output
    assert source.read_text() == "data"
    assert not (folder / "Text" / source.name).exists()


def test_undo_detects_content_change_even_when_metadata_matches(folder):
    source = put(folder, "x.txt", "ABCD")
    service = OrganizeService()
    row = service.organize_files(folder, service.preview_sorting(folder, CATEGORIES))[source.name]
    destination = row["destination"]
    previous = destination.stat()
    destination.write_text("DCBA")
    os.utime(destination, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    undone, = service.undo(folder).values()
    assert undone["status"] == "failed"
    assert destination.read_text() == "DCBA" and not source.exists()

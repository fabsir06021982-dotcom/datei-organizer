from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from datei_organizer import cli_view


@pytest.mark.parametrize("width,compact", [(48, True), (100, False)])
def test_preview_is_readable_without_colour_and_keeps_literal_names(tmp_path, monkeypatch, width, compact):
    output = StringIO()
    console = Console(file=output, width=width, no_color=True, color_system=None)
    monkeypatch.setattr(cli_view, "console", console)
    source = tmp_path / "[v1].txt"
    target = tmp_path / "texte" / source.name
    plan = {source.name: dict(source=source, destination=target, status="conflict")}
    console.print(cli_view.sorting_table(plan, tmp_path, preview=True))
    rendered = output.getvalue()
    assert "Sortiervorschau" in rendered and "Namenskonflikt" in rendered
    assert rendered.count("[v1].txt") == 2
    assert ("Dateipfade" in rendered) == compact
    assert "\x1b" not in rendered and max(map(len, rendered.splitlines())) <= width


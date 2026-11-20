"""Terminal presentation. Keep file names literal, including Rich markup characters."""
from contextlib import contextmanager
from pathlib import Path

from rich import box
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

console = Console(highlight=False, theme=Theme({
    "accent": "bold cyan", "muted": "dim", "ok": "green", "warning": "yellow",
    "danger": "bold red",
}))
STATUS = {
    "planned": ("Geplant", "cyan"), "conflict": ("Namenskonflikt", "warning"),
    "moved": ("Verschoben", "ok"), "skipped": ("Übersprungen", "muted"),
    "failed": ("Fehlgeschlagen", "danger"), "cancelled": ("Abgebrochen", "warning"),
}


def heading(section):
    console.print()
    console.rule(Text.assemble(("Datei-Organizer", "accent"), ("  /  ", "muted"), section),
                 align="left", style="cyan")
    console.print()


def report(title, caption=None):
    return Table(title=title, title_style="bold", title_justify="left", header_style="bold cyan",
                 box=box.SIMPLE_HEAD, padding=(0, 1), expand=True, border_style="dim",
                 caption=caption, caption_justify="left", caption_style="muted")


def paths_panel(title, pairs, style="cyan"):
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="muted")
    grid.add_column(overflow="fold")
    for label, path in pairs:
        grid.add_row(Text(label), Text(str(path)))
    return Panel(grid, title=Text(title), title_align="left", border_style=style, padding=(0, 1))


def sorting_table(result, folder: Path, preview=False, undo=False):
    title = "Rücknahme" if undo else ("Sortiervorschau" if preview else "Sortierergebnis")
    counts = {}
    for entry in result.values():
        key = entry["status"]
        counts[key] = counts.get(key, 0) + 1
    caption = "  ·  ".join(f"{label}: {counts[key]}" for key, (label, _) in STATUS.items() if key in counts)
    if undo:
        caption = caption.replace("Verschoben:", "Zurückgenommen:")
    table = report(title, caption)
    compact = console.width < 68
    table.add_column("Dateipfade" if compact else "Quelle", overflow="fold", ratio=2)
    if not compact:
        table.add_column("Geplantes Ziel" if preview else "Ziel", overflow="fold", ratio=3)
    table.add_column("Status", overflow="fold")
    for entry in result.values():
        status = entry["status"]
        source = Text(str(entry["source"].relative_to(folder)))
        target = Text(str(entry["destination"].relative_to(folder)))
        label, style = STATUS[status]
        badge = Text("Zurückgenommen" if undo and status == "moved" else label, style=style)
        if compact:
            source.append("\nZiel: ", style="muted")
            source.append_text(target)
            table.add_row(source, badge)
        else:
            table.add_row(source, target, badge)
    return table


@contextmanager
def file_progress(label):
    """Use a transient progress line on a terminal; keep redirected reports clean."""
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(),
                  TextColumn("{task.fields[count]}"), TextColumn("Fehler: {task.fields[errors]}"),
                  console=console, transient=True, disable=not console.is_terminal) as progress:
        task = progress.add_task(label, total=None, count="0 Dateien", errors=0)
        def report_progress(count, total, errors):
            progress.update(task, total=total or None, completed=count,
                            count=f"{count}/{total}" if total else f"{count} Dateien", errors=errors)
        yield report_progress

from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .main import analysiere_dateien, lade_konfiguration, prozent_dateien


app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Start the file organizer."""
    console.print()
    console.print(
        "🚀 [bold underline green]"
        "Willkommen im Datei-Organizer!"
        "[/bold underline green]"
    )
    console.print("[cyan]❓ Nutze --help für eine Liste aller Befehle[/cyan]")
    console.print()
    console.print()

    if ctx.invoked_subcommand is None:
        console.print(
            "[red italic]Kein Befehl übergeben. Beende...[/red italic] ➜🚪"
        )


@app.command("analyse")
def analyze() -> None:
    """Analyze a folder."""
    console.print("🔎 [bold underline green]Analyse[/bold underline green]")
    console.print("[cyan]Welchen Ordner willst du analysieren?[/cyan]")

    configuration_path = Path("config.json")
    configuration = lade_konfiguration(configuration_path)
    default_folder = Path(configuration["ordner"]).resolve()

    console.print(
        Panel(
            str(default_folder),
            title="Standardordner aus der Konfiguration",
        )
    )

    folder_input = Prompt.ask(
        "[cyan]Neuen Ordner eingeben oder Enter ⏎ "
        "für den Standardordner[/cyan]"
    )

    if folder_input == "":
        selected_folder = default_folder
        console.print(
            "[cyan]Standardordner aus der Konfiguration wird verwendet.[/cyan]"
        )
    else:
        selected_folder = Path(folder_input).resolve()

    if not selected_folder.is_dir():
        console.print(
            "[red italic]Der ausgewählte Ordner ist ungültig![/red italic]"
        )
        raise typer.Abort()

    console.print(
        Panel(str(selected_folder), title="Ausgewählter Ordner")
    )

    analysis_result = analysiere_dateien(
        selected_folder,
        configuration["kategorien"],
    )

    if not analysis_result:
        console.print(
            "[cyan]Im ausgewählten Ordner wurden keine Dateien gefunden.[/cyan]"
        )
        return

    percentages = prozent_dateien(analysis_result)
    console.print(create_analysis_table(analysis_result, percentages))

    if not Confirm.ask("Möchtest du die Kategoriezuordnungen bearbeiten?"):
        console.print(
            "[cyan]Kategoriezuordnungen werden nicht bearbeitet. Ende.[/cyan]"
        )
        return

    console.print("Kategoriezuordnungen")
    edit_assignments(configuration["kategorien"], analysis_result)


def edit_assignments(categories: dict, analysis_result: dict) -> None:
    """Prepare category assignments for editing."""
    # Work on a draft so changes can later be discarded.
    new_categories = categories.copy()

    for file_extension in analysis_result:
        display_extension = file_extension or "ohne Endung"
        assignment = new_categories.get(file_extension)

        if assignment is None:
            assignment = "nicht zugeordnet"

        console.print(f"{display_extension} -> {assignment}")


def create_analysis_table(
    analysis_result: dict,
    percentages: dict,
) -> Table:
    """Build and return a table containing the analysis results."""
    table = Table(box=box.SQUARE, title="Analyseergebnis")
    table.add_column("Dateiendung", style="purple", no_wrap=True)
    table.add_column("Anzahl", justify="right", style="magenta")
    table.add_column("Anteil", justify="right", style="green")
    table.add_column("Kategorie", style="cyan")

    for file_extension, data in analysis_result.items():
        display_extension = file_extension or "ohne Endung"
        category = data["kategorie"]

        if category is None:
            category = "nicht zugeordnet"

        table.add_row(
            display_extension,
            str(data["anzahl"]),
            f"{percentages[file_extension]:.2f}%",
            category,
        )

    return table


@app.command("sortiere")
def sort_files() -> None:
    """Sort files using the configured category assignments."""
    console.print("Sortiere")


if __name__ == "__main__":
    app()
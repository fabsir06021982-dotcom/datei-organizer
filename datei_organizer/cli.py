from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .main import analyze_files, load_configuration, calculate_percentages, validate_category_name, save_configuration


app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Start the file organizer."""
    console.print()
    console.print("🚀 [bold underline green]Willkommen im Datei-Organizer![/bold underline green]")
    console.print("[cyan]❓ Nutze --help für eine Liste aller Befehle[/cyan]")
    console.print()
    console.print()

    if ctx.invoked_subcommand is None:
        console.print("[red italic]Kein Befehl übergeben. Beende...[/red italic] ➜🚪")


@app.command("analyse")
def analyze() -> None:
    """Analyze a folder."""
    console.print("🔎 [bold underline green]Analyse[/bold underline green]")
    console.print("[cyan]Welchen Ordner willst du analysieren?[/cyan]")

    configuration_path = Path("config.json")
    configuration = load_configuration(configuration_path)
    default_folder = Path(configuration["ordner"]).resolve()

    console.print(Panel(str(default_folder), title="Standardordner aus der Konfiguration"))
    folder_input = Prompt.ask("[cyan]Neuen Ordner eingeben oder Enter ⏎ für den Standardordner[/cyan]")

    if folder_input == "":
        selected_folder = default_folder
        console.print("[cyan]Standardordner aus der Konfiguration wird verwendet.[/cyan]")
    else:
        selected_folder = Path(folder_input).resolve()

    if not selected_folder.is_dir():
        console.print("[red italic]Der ausgewählte Ordner ist ungültig![/red italic]")
        raise typer.Abort()

    console.print(Panel(str(selected_folder), title="Ausgewählter Ordner"))
    analysis_result = analyze_files(selected_folder, configuration["kategorien"])

    if not analysis_result:
        console.print("[cyan]Im ausgewählten Ordner wurden keine Dateien gefunden.[/cyan]")
        return

    percentages = calculate_percentages(analysis_result)
    console.print(create_analysis_table(analysis_result, percentages))

    if not Confirm.ask("Möchtest du die Kategoriezuordnungen bearbeiten?"):
        console.print("[cyan]Kategoriezuordnungen werden nicht bearbeitet. Ende.[/cyan]")
        return
    console.print()
    console.print()
    console.print("[bold underline magenta]📁 Kategoriezuordnungen[/bold underline magenta]")
    console.print()
    new_assignments = edit_assignments(configuration["kategorien"], analysis_result)
    console.print("[bold underline green]Neue Zuordnungstabelle[/bold underline green]")
    console.print(create_assignment_table(new_assignments, analysis_result))
    save_assignment = Confirm.ask("[cyan]Sollen die neuen Zuordnungen dauerhaft gespeichert werden?[/cyan]")
    if not save_assignment:
        console.print("[cyan]Neue Zuordnungen werden nicht gespeichert. Abbruch.[/cyan]")
        return
    configuration["kategorien"] = new_assignments
    save_configuration(configuration_path, configuration)
    console.print("[green]Erfolgreich gespeichert ✅.[/green]")


def edit_assignments(categories: dict, analysis_result: dict) -> dict:
    """Edit a copy of the category assignments and return the draft."""
    # Work on a draft so changes can later be discarded.
    new_categories = categories.copy()
    console.print(create_assignment_table(new_categories, analysis_result))
    for file_extension in analysis_result:
        display_extension = file_extension or "ohne Endung"
        assignment = new_categories.get(file_extension)
        if assignment is None:
            assignment = "nicht zugeordnet"

        change_assignment = Confirm.ask(f"[cyan]Möchten Sie die aktuelle Zuordnung von Ordner 📁 {assignment} zu Dateiendung📄 {display_extension} ändern?[/cyan]")
        if not change_assignment:
            continue
        delete_assignment = Confirm.ask("[cyan]Soll die Zuordnung gelöscht ✂️ werden?[/cyan]")
        if delete_assignment:
            delete_output = new_categories.pop(file_extension, None)
            if delete_output is None:
                console.print("[red italic]Löschen nicht möglich. Kategorienzuordnung fehlt.[/red italic]")
                continue
            console.print("[cyan]Zuordnung erfolgreich gelöscht.[/cyan]")
        else:
            for _ in range(3):
                new_assignment = Prompt.ask("[cyan]Bitte einen gültigen Ordnernamen ✅ eingeben?[/cyan]")
                cleaned_assignment = new_assignment.strip()
                try:
                    validate_category_name(cleaned_assignment)
                except ValueError as error:
                    console.print(f"[red italic]{error}[/red italic]")
                    continue
                new_categories[file_extension] = cleaned_assignment
                break
            else:
                console.print("[red italic]Keinen gültigen Ordnernamen eingegeben.[/red italic]")
                continue
    return new_categories


def create_assignment_table(categories: dict, analysis_result: dict) -> Table:
    """Build and return a table showing file extensions and their category assignments."""
    table = Table(box=box.SQUARE, title="Kategoriezuordnung")
    table.add_column("Dateiendung", style="purple", no_wrap=True)
    table.add_column("Kategorie", style="cyan")

    for file_extension in analysis_result:
        display_extension = file_extension or "ohne Endung"
        assignment = categories.get(file_extension)

        if assignment is None:
            assignment = "nicht zugeordnet"

        table.add_row(display_extension, assignment)

    return table


def create_analysis_table(analysis_result: dict, percentages: dict) -> Table:
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

        table.add_row(display_extension, str(data["anzahl"]), f"{percentages[file_extension]:.2f}%", category)

    return table


@app.command("sortiere")
def sort_files() -> None:
    """Sort files using the configured category assignments."""
    console.print("Sortiere")


if __name__ == "__main__":
    app()

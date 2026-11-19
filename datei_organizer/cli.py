from typing import Annotated
from pathlib import Path
import typer

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
import json
from datei_organizer.configuration_service import ConfigurationData, ConfigurationService
from datei_organizer.analysis_service import AnalysisService, AnalysisEntry
from datei_organizer.organize_service import OrganizeService, FilePaths
from datei_organizer.application import Application

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

def select_folder(default_folder: Path) -> Path:
    """
    choose and return the folder through user input with simple protection from incorrect input
    """
    default_folder = default_folder.resolve()

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

    return selected_folder

def load_configuration_and_select_folder(configuration_path: Path) -> tuple[ConfigurationData, Path]:
    configuration = load_cli_configuration(configuration_path)
    default_folder = Path(configuration["ordner"])
    selected_folder = select_folder(default_folder)
    console.print(Panel(str(selected_folder), title="Ausgewählter Ordner"))
    return configuration, selected_folder


@app.command("analyse")
def analyze(configuration_path: Annotated[Path, typer.Option("--config")] = Path("config.json")) -> None:
    """Analyze a folder."""
    console.print("🔎 [bold underline green]Analyse[/bold underline green]")
    console.print("[cyan]Welchen Ordner willst du analysieren?[/cyan]")
    configuration, selected_folder = load_configuration_and_select_folder(configuration_path)
    with console.status("Ordner wird analysiert..."):
        analysis_service = AnalysisService()
        analysis_result = analysis_service.analyze_files(selected_folder, configuration["kategorien"])

    if not analysis_result:
        console.print("[cyan]Im ausgewählten Ordner wurden keine Dateien gefunden.[/cyan]")
        return

    percentages = analysis_service.calculate_percentages(analysis_result)
    console.print(create_analysis_table(analysis_result, percentages))

    if not Confirm.ask("Möchtest du die Kategoriezuordnungen bearbeiten?"):
        console.print("[cyan]Kategoriezuordnungen werden nicht bearbeitet. Ende.[/cyan]")
        return
    console.print()
    console.print()
    console.print("[bold underline magenta]📁 Kategoriezuordnungen[/bold underline magenta]")
    console.print()
    new_assignments = edit_assignments(configuration["kategorien"], analysis_result)
    console.print()
    console.print()
    console.print("[bold underline green]Neue Zuordnungstabelle[/bold underline green]")
    console.print()
    console.print(create_assignment_table(new_assignments, analysis_result))
    console.print()
    console.print()
    save_assignment = Confirm.ask("[cyan]Sollen die neuen Zuordnungen dauerhaft gespeichert werden?[/cyan]")
    console.print()
    if not save_assignment:
        console.print("[cyan]Neue Zuordnungen werden nicht gespeichert. Abbruch.[/cyan]")
        return
    configuration["kategorien"] = new_assignments
    config_service = ConfigurationService()
    config_service.save_configuration(configuration_path, configuration)
    console.print("[green]✅ Erfolgreich gespeichert.[/green]")


def edit_assignments(categories: dict[str, str], analysis_result: dict[str, AnalysisEntry]) -> dict[str, str]:
    """Edit a copy of the category assignments and return the draft."""
    # Work on a draft so changes can later be discarded.
    new_categories = categories.copy()
    console.print(create_assignment_table(new_categories, analysis_result))
    for file_extension in analysis_result:
        display_extension = file_extension or "ohne Endung"
        assignment = new_categories.get(file_extension)
        if assignment is None:
            assignment = "nicht zugeordnet"

        change_assignment = Confirm.ask(f"[cyan]📄 -> 📁 Möchten Sie die aktuelle Zuordnung von Dateiendung {display_extension} zu Ordner {assignment} ändern?[/cyan]")
        if not change_assignment:
            continue
        delete_assignment = Confirm.ask("[cyan]✂️ Soll die Zuordnung gelöscht werden?[/cyan]")
        if delete_assignment:
            delete_output = new_categories.pop(file_extension, None)
            if delete_output is None:
                console.print("[red italic]Löschen nicht möglich. Kategorienzuordnung fehlt.[/red italic]")
                continue
            console.print("[cyan]Zuordnung erfolgreich gelöscht.[/cyan]")
        else:
            config_service = ConfigurationService()
            for _ in range(3):
                new_assignment = Prompt.ask("[cyan]✅ Bitte einen gültigen Ordnernamen eingeben?[/cyan]")
                cleaned_assignment = new_assignment.strip()
                try:
                    config_service.validate_category_name(cleaned_assignment)
                except ValueError as error:
                    console.print(f"[red italic]{error}[/red italic]")
                    continue
                new_categories[file_extension] = cleaned_assignment
                break
            else:
                console.print("[red italic]Keinen gültigen Ordnernamen eingegeben.[/red italic]")
                continue
    return new_categories


def create_assignment_table(categories: dict[str, str], analysis_result: dict[str, AnalysisEntry]) -> Table:
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


def create_analysis_table(analysis_result: dict[str, AnalysisEntry], percentages: dict[str, float]) -> Table:
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

def create_sorting_table(sorting_result: dict[str, FilePaths], selected_folder: Path) -> Table:
    """Build and return a table containing the sorting results."""
    table = Table(box=box.SQUARE, title="Sortierergebnis")
    table.add_column("Dateiname", style="purple", no_wrap=True)
    table.add_column("Quelldatei", justify="right", style="magenta")
    table.add_column("Zieldatei", justify="right", style="green")

    for filename in sorting_result:
        source = sorting_result[filename]["source"].relative_to(selected_folder)
        destination = sorting_result[filename]["destination"].relative_to(selected_folder)
        table.add_row(str(filename), str(source), str(destination))
    return table



@app.command("sortiere")
def sort_files(configuration_path: Annotated[Path, typer.Option("--config")] = Path("config.json")) -> None:
    """Sort files using the configured category assignments."""
    console.print("🔎 [bold underline green]Sortiere[/bold underline green]")
    console.print("[cyan]Welchen Ordner willst du sortieren lassen?[/cyan]")
    configuration, selected_folder = load_configuration_and_select_folder(configuration_path)
    console.print()    
    console.print("[italic magenta]Dateien werden anhand der gespeicherten Kategorien verschoben![/italic magenta]")
    console.print("[italic magenta]Nur Dateien im direkt ausgewählten Ordner werden sortiert[/italic magenta]")
    console.print() 
    confirm_sorting = Confirm.ask("[bold underline yellow]Bitte bestätigen Sie den Vorgang.[/bold underline yellow]")
    if not confirm_sorting:
        console.print("[cyan]Sortiervorgang abgebrochen.[/cyan]")
        return    
    organize_service = OrganizeService()
    organize_result = organize_service.organize_files(selected_folder, configuration["kategorien"])
    console.print("[cyan]Sortierdurchlauf beendet.[/cyan]")
    console.print(create_sorting_table(organize_result, selected_folder))
   

def load_cli_configuration(configuration_path: Path) -> ConfigurationData:
    """Load configuration and report CLI errors."""
    config_service = ConfigurationService()
    try:
        return config_service.load_configuration(configuration_path)
    except FileNotFoundError as error:
        console.print()
        console.print(f"[red italic]{error}[/red italic]")
        console.print(f"[red italic]{configuration_path} existiert nicht![/red italic]", soft_wrap=True)
        raise typer.Exit(code=1)
    except json.JSONDecodeError as error:
        console.print(f"[red italic]{error}[/red italic]")
        console.print(f"[red italic]Ungültiges JSON: {configuration_path}[/red italic]", soft_wrap=True)
        raise typer.Exit(code=1)
    except ValueError as error:
        console.print(f"[red italic]{error}[/red italic]")
        console.print(f"[red italic]Ungültige Konfiguration: {configuration_path}[/red italic]", soft_wrap=True)
        raise typer.Exit(code=1)
    except PermissionError as error:
        console.print(f"[red italic]{error}[/red italic]")
        console.print(f"[red italic]Zugriff verweigert: {configuration_path}[/red italic]", soft_wrap=True)
        raise typer.Exit(code=1)

def run_cli() -> None:
    application = Application()
    application.start(app)

if __name__ == "__main__":
    run_cli()

    

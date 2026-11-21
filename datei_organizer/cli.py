from typing import Annotated
from pathlib import Path
import typer

from rich.text import Text
from rich.prompt import Confirm, Prompt
from rich.table import Table
import json
from datei_organizer.configuration_service import ConfigurationData, ConfigurationService
from datei_organizer.analysis_service import AnalysisService, AnalysisEntry
from datei_organizer.organize_service import OrganizeService
from datei_organizer.application import Application
from .scanning import Options
from .cli_view import console, file_progress, heading, paths_panel, report, sorting_table
from .log_service import configure_logging, log

app = typer.Typer(help="Dateien analysieren, Sortierpläne prüfen und Verschiebungen zurücknehmen.",
                  add_completion=False, pretty_exceptions_show_locals=False)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    sections = {"analyse": "Analyse", "sortiere": "Sortierung", "rueckgaengig": "Rücknahme"}
    heading(sections.get(ctx.invoked_subcommand, "Übersicht"))
    if ctx.invoked_subcommand is None:
        commands = report("Befehle")
        commands.add_column("Aufruf", style="cyan")
        commands.add_column("Funktion")
        commands.add_row("analyse", "Dateitypen, Anteile und Kategorien anzeigen")
        commands.add_row("sortiere --dry-run", "Ziele und Konflikte vorab prüfen")
        commands.add_row("sortiere", "Vorschau bestätigen und Dateien verschieben")
        commands.add_row("rueckgaengig", "Letzten Lauf für einen Ordner zurücknehmen")
        console.print(commands)
        console.print("[muted]Aufruf: cli-organizer BEFEHL   ·   Hilfe: cli-organizer --help[/muted]")


def select_folder(default_folder: Path) -> Path:
    """
    choose and return the folder through user input with simple protection from incorrect input
    """
    default_folder = default_folder.resolve()

    console.print(paths_panel("Ordnerauswahl", [("Vorgabe", default_folder)]))
    folder_input = Prompt.ask("[cyan]Neuen Ordner eingeben oder Enter ⏎ für den Standardordner[/cyan]")

    if folder_input == "":
        selected_folder = default_folder

    else:
        selected_folder = Path(folder_input).resolve()

    if not selected_folder.is_dir():
        console.print("[danger]Der ausgewählte Ordner ist ungültig![/danger]")
        raise typer.Abort()

    return selected_folder

def load_configuration_and_select_folder(configuration_path: Path) -> tuple[ConfigurationData, Path]:
    configuration = load_cli_configuration(configuration_path)
    configure_logging(Options.load(configuration.get("optionen", {})).logging)
    log.info("CLI-Konfiguration geladen: %s", configuration_path)
    default_folder = Path(configuration["ordner"])
    selected_folder = select_folder(default_folder)
    if selected_folder != default_folder.resolve():
        console.print(Text(f"Ausgewählt: {selected_folder}", style="muted"))
    return configuration, selected_folder


@app.command("analyse")
def analyze(configuration_path: Annotated[Path, typer.Option("--config")] = Path("config.json")) -> None:
    """Dateitypen zählen und Kategoriezuordnungen bearbeiten."""
    configuration, selected_folder = load_configuration_and_select_folder(configuration_path)
    with file_progress("Analyse") as progress:
        analysis_service = AnalysisService()
        analysis_result = analysis_service.analyze_files(selected_folder, configuration["kategorien"], Options.load(configuration.get("optionen", {})), protected_paths=(configuration_path,), progress=progress, on_error=lambda path, error: console.print(f"{path}: {error}"))

    if not analysis_result:
        console.print("[cyan]Im ausgewählten Ordner wurden keine Dateien gefunden.[/cyan]")
        return

    percentages = analysis_service.calculate_percentages(analysis_result)
    console.print(create_analysis_table(analysis_result, percentages))

    if not Confirm.ask("Möchtest du die Kategoriezuordnungen bearbeiten?"):
        console.print("[cyan]Kategoriezuordnungen werden nicht bearbeitet. Ende.[/cyan]")
        return
    console.print()
    new_assignments = edit_assignments(configuration["kategorien"], analysis_result)
    console.print()
    console.print(create_assignment_table(new_assignments, analysis_result))
    save_assignment = Confirm.ask("[cyan]Sollen die neuen Zuordnungen dauerhaft gespeichert werden?[/cyan]")
    console.print()
    if not save_assignment:
        console.print("[cyan]Neue Zuordnungen werden nicht gespeichert. Abbruch.[/cyan]")
        return
    configuration["kategorien"] = new_assignments
    config_service = ConfigurationService()
    config_service.save_configuration(configuration_path, configuration)
    console.print("[green]Erfolgreich gespeichert.[/green]")


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

        change_assignment = Confirm.ask(Text(f"{display_extension} → {assignment}: Zuordnung ändern?"))
        if not change_assignment:
            continue
        delete_assignment = Confirm.ask("[cyan]Zuordnung löschen?[/cyan]")
        if delete_assignment:
            delete_output = new_categories.pop(file_extension, None)
            if delete_output is None:
                console.print("[danger]Löschen nicht möglich. Kategorienzuordnung fehlt.[/danger]")
                continue
            console.print("[cyan]Zuordnung erfolgreich gelöscht.[/cyan]")
        else:
            config_service = ConfigurationService()
            for _ in range(3):
                new_assignment = Prompt.ask("[cyan]Neuer Ordnername[/cyan]")
                cleaned_assignment = new_assignment.strip()
                try:
                    config_service.validate_category_name(cleaned_assignment)
                except ValueError as error:
                    console.print(Text(str(error), style="danger"))
                    continue
                new_categories[file_extension] = cleaned_assignment
                break
            else:
                console.print("[danger]Keinen gültigen Ordnernamen eingegeben.[/danger]")
                continue
    return new_categories


def create_assignment_table(categories: dict[str, str], analysis_result: dict[str, AnalysisEntry]) -> Table:
    """Build and return a table showing file extensions and their category assignments."""
    table = report("Kategoriezuordnung")
    table.add_column("Dateiendung", style="bold", overflow="fold")
    table.add_column("Kategorie", style="cyan")

    for file_extension in analysis_result:
        display_extension = file_extension or "ohne Endung"
        assignment = categories.get(file_extension)

        if assignment is None:
            assignment = "nicht zugeordnet"

        table.add_row(Text(display_extension), Text(assignment))

    return table


def create_analysis_table(analysis_result: dict[str, AnalysisEntry], percentages: dict[str, float]) -> Table:
    """Build and return a table containing the analysis results."""
    table = report("Analyseergebnis", f"{sum(item['anzahl'] for item in analysis_result.values())} Dateien")
    table.add_column("Dateiendung", style="bold", overflow="fold")
    table.add_column("Anzahl", justify="right", style="bold")
    table.add_column("Anteil", justify="right", style="cyan")
    table.add_column("Kategorie", style="cyan")

    for file_extension, data in sorted(analysis_result.items(), key=lambda item: (-item[1]["anzahl"], item[0])):
        display_extension = file_extension or "ohne Endung"
        category = data["kategorie"]

        if category is None:
            category = "nicht zugeordnet"

        table.add_row(Text(display_extension), str(data["anzahl"]), f"{percentages[file_extension]:.1f} %", Text(category))

    return table

def choose_conflict(source: Path, destination: Path) -> str:
    console.print(paths_panel("Namenskonflikt", [("Quelle", source), ("Belegtes Ziel", destination)], "yellow"))
    answer = Prompt.ask("Beide Dateien behalten und die eingehende Datei umbenennen?",
                        choices=["ja", "nein"], case_sensitive=False)
    return "rename" if answer.lower() == "ja" else "skip"


@app.command("sortiere")
def sort_files(configuration_path: Annotated[Path, typer.Option("--config")] = Path("config.json"), dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Sortierplan anzeigen und bestätigte Verschiebungen ausführen."""
    configuration, selected_folder = load_configuration_and_select_folder(configuration_path)
    options = Options.load(configuration.get("optionen", {}))
    organize_service = OrganizeService()
    try:
        with file_progress("Vorschau") as progress:
            plan = organize_service.preview_sorting(selected_folder, configuration["kategorien"], options,
                                                   protected_paths=(configuration_path,), progress=progress)
    except (ValueError, OSError) as exc:
        console.print(Text(str(exc), style="danger"))
        raise typer.Exit(1) from exc
    if not plan:
        console.print("Keine Dateien zum Sortieren gefunden.")
        return
    console.print(sorting_table(plan, selected_folder, preview=True))
    if dry_run:
        log.info("Dry-Run abgeschlossen: %s", selected_folder)
        console.print("[muted]Dry-Run abgeschlossen. Es wurden keine Dateien verschoben.[/muted]")
        return
    confirm_sorting = Confirm.ask("Diesen Sortierplan ausführen?", default=False)
    if not confirm_sorting:
        log.info("Sortierung vor Ausführung abgebrochen: %s", selected_folder)
        console.print("[cyan]Sortiervorgang abgebrochen.[/cyan]")
        return    
    with file_progress("Sortierung") as progress:
        organize_result = organize_service.organize_files(selected_folder, plan, conflict=options.conflict,
                                                          decide=choose_conflict, progress=progress)
    for entry in organize_result.values():
        if "error" in entry:
            console.print(Text(f"{entry['source']}: {entry['error']}", style="danger"))
    console.print()
    console.print(sorting_table(organize_result, selected_folder))
    console.print("[cyan]Sortierdurchlauf beendet.[/cyan]")

   

@app.command("rueckgaengig")
def undo(configuration_path: Annotated[Path, typer.Option("--config")] = Path("config.json")):
    """Letzte Verschiebungen für einen Ordner sicher zurücknehmen."""
    _, folder = load_configuration_and_select_folder(configuration_path)
    if Confirm.ask("Letzten Sortierlauf rückgängig machen?", default=False):
        with file_progress("Rücknahme") as progress:
            result = OrganizeService().undo(folder, progress=progress)
        if not result:
            console.print("Kein rücknehmbarer Lauf für diesen Ordner.")
            return
        console.print(sorting_table(result, folder, undo=True))
        for entry in result.values():
            if "error" in entry:
                console.print(Text(entry["error"], style="danger"))


def load_cli_configuration(configuration_path: Path) -> ConfigurationData:
    """Load configuration and report CLI errors."""
    config_service = ConfigurationService()
    try:
        return config_service.load_configuration(configuration_path)
    except FileNotFoundError as error:
        console.print()
        console.print(Text(str(error), style="danger"))
        console.print(Text(f"{configuration_path} existiert nicht!", style="danger"), soft_wrap=True)
        raise typer.Exit(code=1)
    except json.JSONDecodeError as error:
        console.print(Text(str(error), style="danger"))
        console.print(Text(f"Ungültiges JSON: {configuration_path}", style="danger"), soft_wrap=True)
        raise typer.Exit(code=1)
    except ValueError as error:
        console.print(Text(str(error), style="danger"))
        console.print(Text(f"Ungültige Konfiguration: {configuration_path}", style="danger"), soft_wrap=True)
        raise typer.Exit(code=1)
    except PermissionError as error:
        console.print(Text(str(error), style="danger"))
        console.print(Text(f"Zugriff verweigert: {configuration_path}", style="danger"), soft_wrap=True)
        raise typer.Exit(code=1)

def run_cli() -> None:
    application = Application()
    application.start(app)

if __name__ == "__main__":
    run_cli()

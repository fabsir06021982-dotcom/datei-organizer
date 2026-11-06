from pathlib import Path
from .main import (analysiere_dateien, organisiere_dateien, lade_konfiguration, prozent_dateien, zeige_analyse)
import typer
from rich.prompt import Prompt
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich import box




app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Datei-Organizer
    """
    console.print("\n")
    console.print("🚀 [bold underline green]Willkommen im Datei-Organizer![/bold underline green]")
    console.print("❓ [cyan]Nutze --help für eine Liste aller Befehle[/cyan]")
    console.print("\n\n")
    if ctx.invoked_subcommand is None:
        console.print("[red italic]Kein Befehl übergeben. Beende...[/red italic] ➜🚪")
    
@app.command()
def analyse():
    """
    Analysiere einen Ordner
    """
    console.print("🔎 [bold underline green]Analyse[/bold underline green]")
    console.print("[cyan]Welchen Ordner willst du analysieren?[/cyan]")

    konfigurationspfad = Path("config.json")
    konfiguration = lade_konfiguration(konfigurationspfad)
    ordner = konfiguration["ordner"]
    abs_ordner = Path(ordner).resolve()
    console.print(Panel(str(abs_ordner), title="Standardordner aus der Konfiguration"))
    ordnerauswahl = Prompt.ask("[cyan]Neuen Ordner eingeben oder Enter ⏎ für den Standardordner[/cyan]")
    if ordnerauswahl == "":
        ausgewaehlter_ordner = abs_ordner
        console.print("[cyan]Standardordner aus der Konfiguration wird verwendet.[/cyan]")
    else:
        ausgewaehlter_ordner = Path(ordnerauswahl)
    if ausgewaehlter_ordner.is_dir():
        console.print(Panel(str(ausgewaehlter_ordner), title="Ausgewaehlter Ordner"))
        analyse_ergebnis = analysiere_dateien(ausgewaehlter_ordner, konfiguration["kategorien"])
        if not analyse_ergebnis:
            console.print("[cyan]Im ausgewählten Ordner wurden keine Dateien gefunden.[/cyan]")
            return
        prozent = prozent_dateien(analyse_ergebnis)
        erstelle_analyse_tabelle(analyse_ergebnis, prozent)       
    else:
        console.print("[red italic]Der ausgewählte Ordner ist ungueltig![/red italic]")
        raise typer.Abort()

def erstelle_analyse_tabelle(analyse_ergebnis: dict, prozent: dict) -> None:
    table = Table(box=box.SQUARE, title="Analyseergebnis")
    table.add_column("Dateiendung", style="purple", no_wrap=True)
    table.add_column("Anzahl", style="magenta")
    table.add_column("Anteil", justify="right", style="green")
    table.add_column("Kategorie", justify="right", style="cyan")
    for eintrag in analyse_ergebnis:
        table.add_row(str(eintrag), str(analyse_ergebnis[eintrag]["anzahl"]),str(prozent[eintrag]), str(analyse_ergebnis[eintrag]["kategorie"]))
    console.print(table)


@app.command()
def sortiere():
    console.print("Sortiere")





if __name__ == "__main__":
    app()
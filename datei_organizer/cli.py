from pathlib import Path
from .main import (analysiere_dateien, organisiere_dateien, lade_konfiguration, prozent_dateien, zeige_analyse)
import typer
from rich import print
from rich.prompt import Prompt
from rich.panel import Panel
from rich.console import Console




app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Datei-Organizer
    """
    console.print("")
    console.print("🚀 [bold underline green]Willkommen im Datei-Organizer![/bold underline green]")
    console.print("❓ [cyan]Nutze --help für eine Liste aller Befehle[/cyan]")
    console.print("")
    console.print("")
    if ctx.invoked_subcommand is None:
        print("[yellow]Kein Befehl übergeben. Beende...[/yellow] ➜🚪")
    
@app.command()
def analyse():
    """
    Analysiere einen Ordner
    """
    console.print("🔎 [bold underline green]Analyse[/bold underline green]")
    console.print("[cyan]Welchen Ordner willst du analysieren?[cyan]")

    konfigurationspfad = Path("config.json")
    konfiguration = lade_konfiguration(konfigurationspfad)
    ordner = konfiguration["ordner"]
    abs_ordner = Path(ordner).resolve()
    console.print(Panel(str(abs_ordner), title="Ordner"))
    ordnerauswahl = Prompt.ask("Oder wähle einen Ordner aus")


@app.command()
def sortiere():
    print("Sortiere")





if __name__ == "__main__":
    app()
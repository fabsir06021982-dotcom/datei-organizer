from pathlib import Path
from .main import (analysiere_dateien, organisiere_dateien, lade_konfiguration, prozent_dateien, zeige_analyse)
import typer
from rich import print

app = typer.Typer()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Datei-Organizer
    """
    print("[bold green]Willkommen im Datei-Organizer! 🔥[/bold green]")
    print("[cyan]Nutze --help für eine Liste aller Befehle[/cyan]")

    if ctx.invoked_subcommand is None:
        print("[yellow]Kein Befehl übergeben. Beende...[/yellow]")
    
@app.command()
def analyse():
    print("Analyse")

@app.command()
def sortiere():
    print("Sortiere")




if __name__ == "__main__":
    app()
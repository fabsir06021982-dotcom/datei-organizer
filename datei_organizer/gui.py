import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from pathlib import Path
from main import lade_konfiguration

class OrganizerGUI():
    def __init__(self, root, konfiguration):
        self.root = root
        self.konfiguration = konfiguration
        self.ausgewaehlter_ordner = None
        self.styletheme_aendern()
        self.root.geometry("600x600")
        self.root.resizable(True, True)
        self.root.title("Advanced File Organizer")
        self.erstelle_widgets()
        
        

    
    def erstelle_widgets(self):
        self.label = ttk.Label(self.root, text="Willkommen beim Advanced File Organizer") 
        self.button = ttk.Button(self.root, text="Durchsuchen", command=self.waehle_ordner)
        self.label_ordner = ttk.Label(self.root, text="Kein Ordner ausgewählt")
        self.button_analyse = ttk.Button(self.root, text="Analyse", command=self.analysiere_ordner)

        self.label.grid(row=0, column=0)
        self.button.grid(row=1, column=0)
        self.label_ordner.grid(row=2, column=0)
        self.button_analyse.grid(row=4, column=0)
    
    def aendere_begruessung(self):
        self.label.config(text="Deine Dateien einfach organisieren!")
        self.button.config(text="Erledigt")

    def waehle_ordner(self):
        auswahl = filedialog.askdirectory(parent=self.root, initialdir=self.ermittle_arbeitsverzeichnis())
        if not auswahl:
            self.zeige_status(self.label_ordner, "Kein Ordner ausgewählt")
            self.ausgewaehlter_ordner = None
            
        else:
            
            self.ausgewaehlter_ordner = Path(auswahl)
            self.zeige_status(self.label_ordner, self.ausgewaehlter_ordner)

        
    def ermittle_arbeitsverzeichnis(self) -> Path:
        arbeitsverzeichnis = Path(self.konfiguration["ordner"])
        if arbeitsverzeichnis.is_dir():
            return arbeitsverzeichnis
        else:
            return Path.home()

    def analysiere_ordner(self):
        if self.ausgewaehlter_ordner is None:
            self.zeige_fehler(self.label_ordner, "Bitte zuerst einen Ordner auswählen!")
            return 
        else:
            self.zeige_status(self.label_ordner, self.ausgewaehlter_ordner)
    
    def styletheme_aendern(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Fehler.TLabel", foreground="red")
        self.style.configure("Status.TLabel", foreground="black")
        self.style.configure("Warnung.TLabel", foreground="orange")
    
   
    def zeige_fehler(self, label, nachricht: str):
        label.configure(text=nachricht)
        label.configure(style="Fehler.TLabel")
    
    def zeige_status(self, label, nachricht: str):
        label.config(text=nachricht)
        label.configure(style="Status.TLabel")
    
    def zeige_warnung(self, label, nachricht: str):
        label.configure(text=nachricht)
        label.configure(style="Warnung.TLabel")

    
    def extrahiere_kategorien(self) -> set:
        kategorien = self.konfiguration["kategorien"]










konfigurationspfad = Path("config.json")
konfiguration = lade_konfiguration(konfigurationspfad)

root = tk.Tk()
organizergui = OrganizerGUI(root, konfiguration)



root.mainloop()
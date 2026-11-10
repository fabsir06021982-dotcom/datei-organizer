import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from pathlib import Path
from .main import load_configuration, analyze_files, calculate_percentages

class OrganizerGUI():
    def __init__(self, root, configuration):
        self.root = root
        self.configuration = configuration
        self.selected_folder = None
        self.configure_theme()
        self.analysis_result = None
        self.root.geometry("600x600")
        self.root.resizable(True, True)
        self.root.title("Advanced File Organizer")
        self.create_widgets()


    def create_widgets(self):
        self.label = ttk.Label(self.root, text="Willkommen beim Advanced File Organizer")
        self.button = ttk.Button(self.root, text="Durchsuchen", command=self.select_folder)
        self.folder_label = ttk.Label(self.root, text="Kein Ordner ausgewählt")
        self.analyze_button = ttk.Button(self.root, text="Analyse", command=self.analyze_folder)
        self.status_label = ttk.Label(self.root, text="")
        self.analysis_tree = ttk.Treeview(self.root, columns=["file_extension", "count", "percentages", "category"], show="headings")
        self.analysis_tree.heading("file_extension", text="Dateiendung")
        self.analysis_tree.heading("count", text="Anzahl")
        self.analysis_tree.heading("percentages", text="Anteil")
        self.analysis_tree.heading("category", text="Kategorie")

        self.label.grid(row=0, column=0)
        self.button.grid(row=1, column=0)
        self.folder_label.grid(row=2, column=0)
        self.analyze_button.grid(row=4, column=0)
        self.status_label.grid(row=5, column=0)
        


    def update_greeting(self):
        self.label.config(text="Deine Dateien einfach organisieren!")
        self.button.config(text="Erledigt")

    def select_folder(self):
        """Select a folder and update the displayed selection."""
        selection = filedialog.askdirectory(parent=self.root, initialdir=self.get_initial_directory())
        if not selection:
            self.show_status(self.status_label, "Kein Ordner ausgewählt")
            self.selected_folder = None

        else:

            self.selected_folder = Path(selection)
            self.show_status(self.folder_label, self.selected_folder)



    def get_initial_directory(self) -> Path:
        """Use the configured folder if available, otherwise use the home directory."""
        working_directory = Path(self.configuration["ordner"])
        if working_directory.is_dir():
            return working_directory
        else:
            return Path.home()

    def analyze_folder(self):
        """Analyze the selected folder and store the results."""
        if self.selected_folder is None:
            self.analysis_tree.grid_remove()
            self.show_error(self.status_label, "Bitte zuerst einen Ordner auswählen!")
            return
        self.analysis_result = analyze_files(self.selected_folder, self.configuration["kategorien"])
        if not self.analysis_result:
            self.analysis_tree.grid_remove()
            self.show_status(self.status_label, "Im ausgewählten Ordner wurden keine Dateien gefunden.")
            return
        self.percentages = calculate_percentages(self.analysis_result)
        self.show_status(self.status_label, "Analyse abgeschlossen")


    def show_analysis_table(self):
        self.analysis_tree.grid(row=6, column=0)


    def configure_theme(self):
        """Configure the theme and styles used for status messages."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Error.TLabel", foreground="red")
        self.style.configure("Status.TLabel", foreground="black")
        self.style.configure("Warning.TLabel", foreground="orange")


    def show_error(self, label, message: str):
        label.configure(text=message)
        label.configure(style="Error.TLabel")

    def show_status(self, label, message: str):
        label.config(text=message)
        label.configure(style="Status.TLabel")

    def show_warning(self, label, message: str):
        label.configure(text=message)
        label.configure(style="Warning.TLabel")


    def extract_categories(self) -> set:
        """Read the configured categories for the unfinished GUI category selector."""
        categories = self.configuration["kategorien"]


if __name__ == "__main__":

    configuration_path = Path("config.json")
    configuration = load_configuration(configuration_path)

    root = tk.Tk()
    organizer_gui = OrganizerGUI(root, configuration)


    root.mainloop()

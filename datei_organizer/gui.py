import tkinter as tk
import ttkbootstrap as ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import font
from pathlib import Path
import platform
from .main import load_configuration, analyze_files, calculate_percentages, validate_category_name, save_configuration, organize_files

class OrganizerGUI():
    def __init__(self, root, configuration):
        system = platform.system()
        if system == "Windows":
            font_family = "Segoe UI"
        elif system == "Darwin":
            font_family = "Helvetica Neue"
        else:
            font_family = "DejaVu Sans"
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family=font_family, size=12)
        self.root = root
        self.root.option_add("*Font", default_font)
        self.configuration = configuration
        self.selected_folder = None
        self.configure_theme()
        self.analysis_result = None
        self.root.geometry("1000x1000")
        
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.resizable(True, True)
        self.root.title("Advanced File Organizer")
        self.draft_categories = self.configuration["kategorien"].copy() #{file_extension : category}
        self.extension_by_item = {} #{item_id : file_extension}
        self.selected_extension = None
        self.create_widgets()

       


    def create_widgets(self):
        self.label = ttk.Label(self.root, bootstyle="primary", text="Advanced File Organizer", font=("-size 18 -weight bold -underline True"), padding=5, relief="flat", justify="center")
        self.button = ttk.Button(self.root, bootstyle="primary", text="Durchsuchen", command=self.select_folder)
        self.folder_label = ttk.Label(self.root, bootstyle="secondary outline", text="Bestimmen Sie einen Ordner")
        self.analyze_button = ttk.Button(self.root, bootstyle="primary", text="Analyse", command=self.analyze_folder)
        self.status_label = ttk.Label(self.root, font=("-size 14"), text="",justify="center")
        self.analysis_tree = ttk.Treeview(self.root, columns=["file_extension", "count", "percentages", "category"], show="headings", selectmode="browse")
        self.analysis_tree.heading("file_extension", text="Dateiendung")
        self.analysis_tree.heading("count", text="Anzahl")
        self.analysis_tree.heading("percentages", text="Anteil")
        self.analysis_tree.heading("category", text="Kategorie")
        self.analysis_tree.bind("<<TreeviewSelect>>", self.on_analysis_selection)
        self.category_var = tk.StringVar(self.root)
        self.category_label = ttk.Label(self.root, text="Kategorie")
        self.category_entry = ttk.Entry(self.root, textvariable=self.category_var)
        self.assignment_button = ttk.Button(self.root, text="Zuordnung übernehmen", command=self.apply_assignment)
        self.delete_button = ttk.Button(self.root, text="Zuordnung löschen", command=self.delete_assignment)
        self.reset_button = ttk.Button(self.root, text="Änderungen verwerfen", command=self.discard_changes)
        self.save_button = ttk.Button(self.root, text="Änderungen speichern", command=self.save_assignment)       
        self.save_default_var = tk.BooleanVar(self.root, value=False)
        self.folder_checkbutton = ttk.Checkbutton(self.root, variable=self.save_default_var, text="Ausgewählten Ordner als Standard speichern", takefocus=0)
        self.sort_button = ttk.Button(self.root, text="Sortieren", command=self.sort_files)
        self.label.grid(row=1, column=1, pady=15)
        self.button.grid(row=2, column=1, pady=5)
        self.folder_label.grid(row=3, column=1, pady=5)
        self.analyze_button.grid(row=4, column=1, pady=15)

        self.analysis_tree.grid(row=5, column=1, pady=5)
        self.category_label.grid(row=6, column=1, pady=5)
        self.category_entry.grid(row=7, column=1, pady=5)
        self.assignment_button.grid(row=8, column=1, pady=5)
       
        self.delete_button.grid(row=9, column=1, pady=5)
        self.reset_button.grid(row=10, column=1, pady=5)
        self.folder_checkbutton.grid(row=11, column=1, pady=5)
        self.save_button.grid(row=12, column=1, pady=5)
        self.sort_button.grid(row=13, column=1, pady=5) 
        self.status_label.grid(row=14, column=1, pady=5)
        self.hide_widgets()
      
    def on_analysis_selection(self, event):
        """
        event handler which refresh the input field of categories if the user click on a item on the analysis table
        """
        selected = self.analysis_tree.selection()
        if not selected:
            self.selected_extension = None
            self.category_var.set("")
            return
        item_id = selected[0]
        self.selected_extension = self.extension_by_item.get(item_id)
        category = self.draft_categories.get(self.selected_extension, "")
        self.category_var.set(category)

    def apply_assignment(self) -> None:
        """
        Validate the category name and update the draft assignment.
        """
        if self.selected_extension is None:
            self.show_error(self.status_label, "Keine Dateiendung ausgewählt")
            return
        input_text = self.category_entry.get().strip()
        try:
            validate_category_name(input_text)
        except ValueError as error:
            self.show_error(self.status_label, str(error))
            return      
        selected = self.analysis_tree.selection()
        item_id = selected[0]
        self.analysis_tree.set(item_id, "category", input_text)      
        self.draft_categories[self.selected_extension] = input_text  
        self.show_status(self.status_label, "Zuordnung wurde übernommen. Änderung noch nicht gespeichert")


    def delete_assignment(self) -> None:
        """
        Remove the selected category assignment from the draft.
        """
        selected = self.analysis_tree.selection()
        if not selected:
            self.selected_extension = None
            self.show_status(self.status_label, "Keine Endungsgruppe ausgewählt")
            return
        item_id = selected[0]
        file_extension = self.extension_by_item.get(item_id)            
        removed_category = self.draft_categories.pop(file_extension, None)
        if removed_category is None:
            self.show_status(self.status_label, "Für diese Dateiendung besteht keine Zuordnung")
            return        
        self.category_var.set("")
        self.analysis_tree.set(item_id, "category", "nicht zugeordnet") 
        self.show_status(self.status_label, "Zuordnung entfernt. Änderung noch nicht gespeichert")
    
    def hide_widgets(self) -> None:
        self.analysis_tree.grid_remove()
        self.category_label.grid_remove()
        self.category_entry.grid_remove()
        self.assignment_button.grid_remove()
        self.delete_button.grid_remove()
        self.reset_button.grid_remove()
        self.save_button.grid_remove()    
        self.folder_checkbutton.grid_remove()
        self.sort_button.grid_remove()
    
    def unhide_widgets(self) -> None:
        self.analysis_tree.grid()
        self.category_label.grid()
        self.category_entry.grid()
        self.assignment_button.grid()
        self.delete_button.grid()
        self.reset_button.grid()
        self.save_button.grid()    
        self.folder_checkbutton.grid()
        self.sort_button.grid()


    def discard_changes(self) -> None:
        """
        Discard changes and restore assignments and table
        """
        if self.analysis_result is None:
            return
        self.draft_categories = self.configuration["kategorien"].copy()
        self.selected_extension = None
        self.category_var.set("")
        for item in self.analysis_tree.get_children():
            self.analysis_tree.delete(item)
        self.extension_by_item = {}
        for file_extension in self.analysis_result:
            category = self.configuration["kategorien"].get(file_extension)
            count = self.analysis_result[file_extension]["anzahl"]
            percent = self.percentages.get(file_extension)
            display_extension = file_extension or "ohne Endung"
            if category is None:
                category = "nicht zugeordnet"
            item_id = self.analysis_tree.insert("", "end", values=(display_extension, count, f"{percent:.2f}%", category))
            self.extension_by_item[item_id] = file_extension
        self.show_status(self.status_label, "Zuordnung wurde zurückgesetzt")    

    
    def save_assignment(self) -> None:
        """
        Save assignments in configuration
        """
        configuration_to_save = self.configuration.copy()
        configuration_to_save["kategorien"] = self.draft_categories.copy()
        if not self.save_default_var.get():
            self.show_status(self.status_label, "Standardordner bleibt erhalten.")
        elif self.selected_folder:
            self.show_status(self.status_label, "Ordner ausgewählt.")
            configuration_to_save["ordner"] = str(self.selected_folder)
        elif self.selected_folder is None:
            self.show_status(self.status_label, "Kein Ordner ausgewählt.")
            return
        try:           
            save_configuration(Path("config.json"), configuration_to_save)  
        except OSError:
            self.show_error(self.status_label, "Die Konfiguration konnte nicht gespeichert werden.")
            return       
        self.configuration = configuration_to_save
        self.show_status(self.status_label, "Konfiguration erfolgreich gespeichert.")

                   
        

          
       

    def update_greeting(self):
        self.label.config(text="Deine Dateien einfach organisieren!")
        self.button.config(text="Erledigt")

    def select_folder(self):
        """Select a folder and update the displayed selection."""
        selection = filedialog.askdirectory(parent=self.root, initialdir=self.get_initial_directory())
        if not selection or selection == "":
            self.show_status(self.folder_label, "")
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
            self.hide_widgets()
            self.show_error(self.status_label, "Bitte zuerst einen Ordner auswählen!")
            return
        self.analysis_result = analyze_files(self.selected_folder, self.configuration["kategorien"])
        if not self.analysis_result:
            self.hide_widgets()
            self.show_status(self.status_label, "Im ausgewählten Ordner wurden keine Dateien gefunden.")
            return
        self.percentages = calculate_percentages(self.analysis_result)
        self.show_analysis_table()
        self.show_status(self.status_label, "Analyse abgeschlossen")
    
    def sort_files(self) -> None:
        """
        Sort files from selected or default folder and arrange them into assigned categories
        """
        if self.selected_folder is None:
            self.show_status(self.status_label, "Kein Ordner ausgewählt.")
            return
        if self.draft_categories != self.configuration["kategorien"]:
            self.show_status(self.status_label, "Bitte Änderungen speichern oder verwerfen.")
            return
        sorting_confirmed = messagebox.askyesno(title="Sortierung bestätigen", message="Dateien jetzt sortieren?", detail=f"Nur direkt enthaltene Dateien werden anhand der gespeicherten Kategorien verschoben. Ordner: {self.selected_folder}", icon=messagebox.QUESTION, default=messagebox.NO, parent=self.root)
        if not sorting_confirmed:
            self.show_status(self.status_label, "Sortieren abgebrochen.")
            return
        self.show_status(self.status_label, "Sortierung bestätigt.")
        organize_files(self.selected_folder, self.configuration["kategorien"])
        self.show_status(self.status_label, "Sortiervorgang abgeschlossen.")
        




    def show_analysis_table(self):
        for item in self.analysis_tree.get_children():
            self.analysis_tree.delete(item)
        self.extension_by_item = {}
        for file_extension, data in self.analysis_result.items():
            count = data["anzahl"]
            percentage = self.percentages[file_extension]
            display_extension = file_extension or "ohne Endung"
            category = self.draft_categories.get(file_extension)
            if category is None:
                category = "nicht zugeordnet"            
            item_id = self.analysis_tree.insert("", "end", values=(display_extension, count, f"{percentage:.2f}%", category))
            self.extension_by_item[item_id] = file_extension
        self.selected_extension = None
        self.category_var.set("")
        self.unhide_widgets()
        self.analysis_tree.grid()


    def configure_theme(self):
        """Configure the theme and styles used for status messages."""
        self.style = ttk.Style()
        self.style.theme_use("bootstrap-dark")



    def show_error(self, label, message: str):
        label.configure(text=message, bootstyle="danger" )


    def show_status(self, label, message: str):
        label.config(text=message, bootstyle="info")


    def show_warning(self, label, message: str):
        label.configure(text=message, bootstyle="warning")


    def extract_categories(self) -> set:
        """Read the configured categories for the unfinished GUI category selector."""
        categories = self.configuration["kategorien"]


if __name__ == "__main__":

    configuration_path = Path("config.json")
    configuration = load_configuration(configuration_path)

    root = tk.Tk()
    organizer_gui = OrganizerGUI(root, configuration)


    root.mainloop()

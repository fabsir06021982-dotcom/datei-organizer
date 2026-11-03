import tkinter as tk
from tkinter import ttk

class OrganizerGUI():
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced File Organizer")
        self.erstelle_widgets()

    
    def erstelle_widgets(self):
        self.label = ttk.Label(self.root, text="Willkommen beim Advanced File Organizer") 
        self.button = ttk.Button(self.root, text="Durchsuchen", command=self.aendere_begruessung)

        self.label.grid(row=0, column=0)
        self.button.grid(row=1, column=0)
    
    def aendere_begruessung(self):
        self.label.config(text="Deine Dateien einfach organisieren!")
        self.button.config(text="Erledigt")







root = tk.Tk()
organizergui = OrganizerGUI(root)


root.mainloop()
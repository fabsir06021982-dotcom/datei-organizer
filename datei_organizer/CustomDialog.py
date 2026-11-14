import tkinter as tk
from tkinter import ttk

class CustomDialog(tk.Toplevel):
    def __init__(self, parent):
        self.title("Advanced File Organizer")
        self.geometry("250x120")
        self.transient(parent)
        self.grab_set()

        self.label = ttk.Label(self, text="Dateien jetzt sortieren?")
        self.label.pack(pady=10)

        self.entry = ttk.Entry(self)
        self.entry.pack(pady=5)

        self.button = ttk.Button(self, text="Ja", command=self.on_yes)
        self.button.pack(pady=10)

        self.result = None
        self.wait_windows(self)

    
    def on_yes(self):
        self.result = self.entry.get()
        self.destroy


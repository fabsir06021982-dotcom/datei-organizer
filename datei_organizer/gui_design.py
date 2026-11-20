"""Artwork and layout shared by the desktop views."""
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk, ImageSequence
import ttkbootstrap as ttk

ASSETS = Path(__file__).with_name("assets")
NAV = {"Start": "start", "Analyse": "analyse", "Zuordnungen": "zuordnungen",
       "Ergebnisse": "ergebnisse", "Einstellungen": "einstellungen"}


class Design:
    def __init__(self, root, style):
        self.root, self.style = root, style
        self.cache = {}
        self.configure()

    def configure(self):
        colors = self.style.colors
        dark = self.style.theme.name == "bootstrap-dark"
        self.bg = "#0b1422" if dark else colors.bg
        self.panel = "#101c30" if dark else colors.bg
        self.card = "#18263b" if dark else colors.inputbg
        self.line = "#32465f" if dark else colors.border
        self.fg = "#edf3ff" if dark else colors.fg
        self.muted = "#a9b9cd" if dark else colors.secondary
        self.blue = "#087cf0" if dark else colors.primary
        for name, color in (("Shell", self.bg), ("Panel", self.panel), ("Card", self.card)):
            self.style.configure(name+".TFrame", background=color)
            for kind, font, ink in (("Text", ("Segoe UI", 11), self.fg),
                                    ("Muted", ("Segoe UI", 10), self.muted),
                                    ("Title", ("Segoe UI", 24, "bold"), self.fg),
                                    ("Heading", ("Segoe UI", 13, "bold"), self.fg)):
                self.style.configure(kind+name+".TLabel", background=color, foreground=ink, font=font)
        for name, fill in (("Nav", self.panel), ("Action", self.card)):
            key = name+".TButton"
            self.style.configure(key, background=fill, foreground=self.fg, bordercolor=fill,
                                 padding=(12, 9), anchor="w" if name == "Nav" else "center",
                                 font=("Segoe UI", 11))
            self.style.map(key, background=[("disabled", fill), ("selected", self.blue), ("active", self.blue)],
                           foreground=[("disabled", self.muted), ("selected", "white"), ("active", "white")])

    def image(self, name, size, tint=None):
        key = (name, size, tint)
        if key not in self.cache:
            with Image.open(ASSETS / (name+".png")) as source:
                im = source.convert("RGBA")
            im.thumbnail((size, size), Image.Resampling.LANCZOS)
            if tint:
                colored = Image.new("RGBA", im.size, tint)
                colored.putalpha(im.getchannel("A"))
                im = colored
            self.cache[key] = ImageTk.PhotoImage(im, master=self.root)
        return self.cache[key]

    def frames(self):
        with Image.open(ASSETS / "loading.gif") as gif:
            return [ImageTk.PhotoImage(f.convert("RGBA"), master=self.root) for f in ImageSequence.Iterator(gif)]

    def surface(self, parent, role="Card", padding=14):
        # A rounded outline surrounds live Tk controls so keyboard focus stays native.
        color = self.card if role == "Card" else self.panel
        outer = tk.Canvas(parent, highlightthickness=0, borderwidth=0,
                          background=self.panel if role == "Card" else self.bg)
        content = ttk.Frame(outer, style=role+".TFrame")
        window = outer.create_window(padding, padding, anchor="nw", window=content)
        def resize(event):
            w, h, r = event.width-1, event.height-1, 13
            outer.delete("edge")
            outer.create_polygon(r,1,w-r,1,w,1,w,r,w,h-r,w,h,w-r,h,r,h,1,h,1,h-r,1,r,1,1,
                                 smooth=True, fill=color, outline=self.line, tags="edge")
            outer.tag_lower("edge")
            outer.itemconfigure(window, width=max(1,w-2*padding), height=max(1,h-2*padding))
        outer.bind("<Configure>", resize)
        return outer, content


def file_icon(extension):
    ext = extension.lower().lstrip(".")
    for icon, extensions in (("bild", "png jpg jpeg gif webp bmp svg"), ("video", "mp4 mov avi mkv"),
                             ("dokument", "txt md pdf doc docx odt"), ("system", "sys dll exe ini"),
                             ("archive", "zip rar tar gz 7z"), ("audio", "mp3 wav flac"),
                             ("tabelle", "csv xls xlsx ods")):
        if ext in extensions.split():
            return "file_"+icon
    return "file_datei"

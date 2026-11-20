"""Desktop interface for planning, executing and undoing file operations."""
from .log_service import log
from dataclasses import asdict, fields
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk

from .analysis_service import AnalysisService
from .configuration_service import ConfigurationService
from .gui_job import GuiJob
from .gui_design import Design, NAV, file_icon
from .log_service import configure_logging
from .organize_service import OrganizeService, summary
from .scanning import Options

LABELS = {"planned": "Geplant", "conflict": "Namenskonflikt", "moved": "Verschoben",
          "skipped": "Übersprungen", "failed": "Fehlgeschlagen", "cancelled": "Abgebrochen"}
SETTINGS = {"recursive": "Unterordner durchsuchen", "max_depth": "Maximale Tiefe (leer: unbegrenzt)",
            "extensions": "Dateiendungen (durch Komma getrennt)", "min_bytes": "Mindestgröße in Bytes",
            "max_bytes": "Höchstgröße in Bytes", "modified_from": "Geändert ab (JJJJ-MM-TT)",
            "modified_until": "Geändert bis (JJJJ-MM-TT)", "hidden": "Versteckte Dateien einbeziehen",
            "preserve_structure": "Unterordnerstruktur erhalten", "conflict": "Namenskonflikte",
            "theme": "Theme", "logging": "Logging einschalten"}
POLICIES = {"Nachfragen": "ask", "Umbenennen": "rename", "Überspringen": "skip"}


def tree(parent, headings, *, icons=False):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    view = ttk.Treeview(frame, columns=tuple(headings), show=("tree", "headings") if icons else "headings", selectmode="browse")
    if icons:
        view.column("#0", width=34, minwidth=34, stretch=False)
    for key, label in headings.items():
        view.heading(key, text=label)
        view.column(key, width=140, minwidth=70)
    scroll = ttk.Scrollbar(frame, command=view.yview)
    view.configure(yscrollcommand=scroll.set)
    horizontal = ttk.Scrollbar(frame, orient="horizontal", command=view.xview)
    view.configure(xscrollcommand=horizontal.set)
    horizontal.pack(side="bottom", fill="x")
    scroll.pack(side="right", fill="y")
    view.pack(fill="both", expand=True)
    return view


class OrganizerGUI:
    def __init__(self, root, configuration, configuration_path=Path("config.json")):
        self.root, self.configuration, self.configuration_path = root, configuration, configuration_path
        self.options = Options.load(configuration.get("optionen", {}))
        self.style = ttk.Style()
        self.style.theme_use(self.options.theme if self.options.theme in self.style.theme_names() else "bootstrap-dark")
        configure_logging(self.options.logging)
        self.selected_folder = None
        self.analyzed = self.has_results = False
        self.current_page = "Start"
        self.design = Design(root, self.style)
        self.service = OrganizeService()
        self.draft = dict(configuration["kategorien"])
        root.title("Advanced File Organizer")
        root.iconphoto(True, self.design.image("logo", 32))
        root.geometry("1140x760")
        root.minsize(910, 630)
        self.pages, self.navigation = {}, {}
        self.status = tk.StringVar(value="Bereit.")
        self.context = tk.StringVar(value="Kein Ordner ausgewählt")
        footer = ttk.Frame(root, padding=(16, 8), style="Card.TFrame")
        footer.pack(side="bottom", fill="x")
        self.indicator = ttk.Label(footer, image=self.design.image("info", 18, self.design.muted), style="TextCard.TLabel")
        self.indicator.pack(side="left", padx=(0, 8))
        ttk.Label(footer, textvariable=self.status, style="TextCard.TLabel", wraplength=560).pack(side="left")
        ttk.Label(footer, textvariable=self.context, style="MutedCard.TLabel").pack(side="right")
        self.progress_area = ttk.Frame(root, padding=(16, 4))
        self.bar = ttk.Progressbar(self.progress_area)
        self.bar.pack(side="left", fill="x", expand=True)
        self.abort = ttk.Button(self.progress_area, text="Abbrechen", command=self.cancel)
        self.abort.pack(side="right", padx=(8, 0))
        self.animation = self.design.frames()
        self.animation_id = None
        self.job = GuiJob(root, self.update_progress, self.job_error)
        self.closing = False
        root.protocol("WM_DELETE_WINDOW", self.close)
        shell = ttk.Frame(root, style="Shell.TFrame")
        shell.pack(fill="both", expand=True)
        self.shell = shell
        sidebar = ttk.Frame(shell, padding=(10, 28), width=184, style="Panel.TFrame")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        content = ttk.Frame(shell, padding=(16, 18), style="Shell.TFrame")
        content.pack(side="left", fill="both", expand=True)
        for name in NAV:
            self.pages[name] = ttk.Frame(content, padding=0 if name == "Start" else 14, style="Panel.TFrame")
            button = ttk.Button(sidebar, text="  "+name, compound="left", style="Nav.TButton",
                                command=lambda n=name: self.page(n))
            button.pack(fill="x", pady=3)
            self.navigation[name] = button
            if name != "Start":
                ttk.Label(self.pages[name], text=name, style="TitlePanel.TLabel").pack(anchor="w", pady=(0, 12))
        self.build_home()
        tools = ttk.Frame(self.pages["Analyse"])
        tools.pack(fill="x", pady=(0, 8))
        ttk.Button(tools, text="Analysieren", command=self.analyze_folder).pack(side="left")
        self.to_assignments = ttk.Button(tools, text="Zuordnungen bearbeiten", command=lambda: self.page("Zuordnungen"))
        self.to_assignments.pack(side="left", padx=6)
        self.analysis_tree = tree(self.pages["Analyse"], {"ext": "Endung", "count": "Anzahl", "percent": "Anteil", "category": "Kategorie"}, icons=True)
        assignments = self.pages["Zuordnungen"]
        self.extension, self.category = tk.StringVar(), tk.StringVar()
        for label, variable in (("Dateiendung (leer für Dateien ohne Endung)", self.extension), ("Kategorie", self.category)):
            ttk.Label(assignments, text=label).pack(anchor="w")
            ttk.Entry(assignments, textvariable=variable).pack(fill="x")
        controls = ttk.Frame(assignments)
        controls.pack(fill="x")
        for text, action in (("Übernehmen", self.assign), ("Zuordnung löschen", self.remove),
                             ("Verwerfen", self.reset), ("Speichern", self.save_assignments), ("Sortiervorschau", self.sort_files)):
            ttk.Button(controls, text=text, command=action).pack(side="left")
        self.assignment_tree = tree(assignments, {"ext": "Endung", "category": "Kategorie"})
        self.assignment_tree.bind("<<TreeviewSelect>>", self.pick_assignment)
        self.refresh_assignments()
        ttk.Button(self.pages["Ergebnisse"], text="Letzten Lauf rückgängig machen", command=self.undo).pack(anchor="w", pady=6)
        self.sorting_tree = tree(self.pages["Ergebnisse"], {"name": "Datei", "source": "Quelle", "target": "Ziel", "status": "Status", "error": "Details"}, icons=True)
        self.settings_form()
        self.page("Start")

    def build_home(self):
        start = self.pages["Start"]
        for widget in start.winfo_children():
            widget.destroy()
        d = self.design
        border, panel = d.surface(start, "Panel", 24)
        border.pack(fill="both", expand=True)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        hero = ttk.Frame(panel, style="Panel.TFrame")
        hero.grid(row=0, column=0)
        ttk.Label(hero, image=d.image("logo", 128), style="TextPanel.TLabel").pack()
        ttk.Label(hero, text="Advanced File Organizer", style="TitlePanel.TLabel").pack(pady=(5, 0))
        ttk.Label(hero, text="Dateien analysieren, kategorisieren und automatisch sortieren.",
                  style="TextPanel.TLabel").pack(pady=(3, 0))
        flow = ttk.Frame(panel, style="Panel.TFrame")
        flow.grid(row=1, column=0, sticky="ew")
        steps = (("folder", "1. Ordner auswählen", "Quellordner festlegen."),
                 ("analyse", "2. Analysieren", "Dateien auswerten und Übersicht erstellen."),
                 ("sort", "3. Sortieren", "Dateien nach Zuordnung verschieben."))
        for index, (icon, title, detail) in enumerate(steps):
            col = index * 2
            flow.columnconfigure(col, weight=1, uniform="steps")
            outer, card = d.surface(flow, padding=10)
            outer.configure(height=94, width=1)
            outer.grid(row=0, column=col, sticky="ew")
            ttk.Label(card, image=d.image(icon, 26, "#39afff"), style="TextCard.TLabel").pack(side="left", padx=(0, 7))
            words = ttk.Frame(card, style="Card.TFrame")
            words.pack(side="left", expand=True, fill="x")
            ttk.Label(words, text=title, style="TextCard.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            caption = ttk.Label(words, text=detail, style="MutedCard.TLabel")
            caption.pack(anchor="w")
            words.bind("<Configure>", lambda e, label=caption: label.configure(wraplength=max(68, e.width-3)))
            if index < 2:
                ttk.Label(flow, text="→", style="TextPanel.TLabel").grid(row=0, column=col+1, padx=4)
        outer, card = d.surface(panel, padding=14)
        outer.configure(height=145, width=1)
        outer.grid(row=2, column=0, sticky="ew")
        ttk.Label(card, text="Quellordner", style="HeadingCard.TLabel").pack(anchor="w")
        line = ttk.Frame(card, style="Card.TFrame")
        line.pack(fill="x", pady=(4, 8))
        self.folder_text = tk.StringVar(value=str(self.selected_folder or "Noch kein Ordner ausgewählt …"))
        self.folder_label = ttk.Entry(line, textvariable=self.folder_text, state="readonly")
        self.folder_label.pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Ordner wechseln", image=d.image("folder", 16), compound="left",
                   command=self.select_folder).pack(side="right", padx=(6, 0))
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack()
        self.pick = ttk.Button(actions, text=" Ordner auswählen", image=d.image("play", 18), compound="left",
                               bootstyle="primary", command=self.select_folder)
        self.pick.pack(side="left", padx=4)
        self.analyze = ttk.Button(actions, text=" Analysieren", image=d.image("play", 18), compound="left", command=self.analyze_folder)
        self.analyze.pack(side="left", padx=4)
        self.sort = ttk.Button(actions, text=" Sortieren", image=d.image("sort", 18), compound="left", command=self.sort_files)
        self.sort.pack(side="left", padx=4)

    def access(self):
        return {"Start": True, "Analyse": bool(self.selected_folder), "Zuordnungen": self.analyzed,
                "Ergebnisse": self.has_results, "Einstellungen": True}

    def refresh_navigation(self):
        for name, enabled in self.access().items():
            button = self.navigation[name]
            active = self.current_page == name
            tint = "white" if active else (self.design.fg if enabled else self.design.muted)
            button.configure(image=self.design.image(NAV[name], 22, tint))
            button.state(["!disabled" if enabled else "disabled", "selected" if active else "!selected"])
        self.analyze.state(["!disabled" if self.selected_folder else "disabled"])
        self.sort.state(["!disabled" if self.analyzed else "disabled"])
        self.to_assignments.state(["!disabled" if self.analyzed else "disabled"])
        if self.selected_folder:
            self.pick.pack_forget()
        elif not self.pick.winfo_manager():
            self.pick.pack(side="left", before=self.analyze, padx=4)
        self.context.set("Kein Ordner ausgewählt" if not self.selected_folder else
                         ("Analyse vorhanden" if self.analyzed else "Keine Analyse durchgeführt"))

    def page(self, name):
        if not self.access()[name]:
            return
        self.current_page = name
        for frame in self.pages.values():
            frame.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        self.refresh_navigation()

    def settings_form(self):
        page = self.pages["Einstellungen"]
        ttk.Button(page, text="Quellordner als Standard speichern", command=self.save_default).pack(anchor="w", pady=(0, 4))
        self.variables = {}
        for field in fields(self.options):
            key, value = field.name, getattr(self.options, field.name)
            row = ttk.Frame(page)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=SETTINGS[key], width=38).pack(side="left")
            if type(value) is bool:
                variable = tk.BooleanVar(value=value)
                widget = ttk.Checkbutton(row, variable=variable)
            else:
                variable = tk.StringVar(value="" if value is None else str(value))
                if key in ("theme", "conflict"):
                    choices = self.style.theme_names() if key == "theme" else tuple(POLICIES)
                    if key == "conflict":
                        variable.set(next(label for label, code in POLICIES.items() if code == value))
                    widget = ttk.Combobox(row, textvariable=variable, values=choices, state="readonly")
                else:
                    widget = ttk.Entry(row, textvariable=variable)
            widget.pack(side="left", fill="x", expand=True)
            self.variables[key] = variable
        ttk.Button(page, text="Einstellungen speichern", command=self.save_settings).pack(anchor="w", pady=8)

    def persist(self, **updates):
        if self.job.busy:
            return False
        config = {**self.configuration, **updates}
        try:
            ConfigurationService().save_configuration(self.configuration_path, config)
        except (ValueError, OSError) as exc:
            self.job_error(exc)
            return False
        self.configuration = config
        self.status.set("Gespeichert")
        log.info("Konfiguration gespeichert: %s", self.configuration_path)
        return True

    def save_settings(self):
        try:
            data = {key: var.get() for key, var in self.variables.items()}
            for key in ("max_depth", "min_bytes", "max_bytes"):
                data[key] = int(data[key]) if data[key].strip() else None
            data["conflict"] = POLICIES[data["conflict"]]
            options = Options.load(data)
            if self.persist(optionen=asdict(options)):
                self.options = options
                configure_logging(options.logging)
                self.style.theme_use(options.theme)
                self.design.configure()
                self.build_home()
                self.refresh_navigation()
        except (KeyError, ValueError, OSError) as exc:
            self.job_error(exc)

    def select_folder(self):
        if self.job.busy:
            return
        selected = filedialog.askdirectory(parent=self.root, initialdir=self.selected_folder or (Path(self.configuration["ordner"]) if Path(self.configuration["ordner"]).is_dir() else Path.home()))
        if selected:
            self.selected_folder = Path(selected).resolve()
            log.info("Arbeitsordner gewählt: %s", self.selected_folder)
            self.folder_text.set(selected)
            self.analyzed = self.has_results = False
            self.reset()
            self.status.set("Quellordner ausgewählt.")
            self.page("Start")
            self.analysis_tree.delete(*self.analysis_tree.get_children())
            self.sorting_tree.delete(*self.sorting_tree.get_children())

    def save_default(self):
        if self.selected_folder:
            self.persist(ordner=str(self.selected_folder))

    def refresh_assignments(self):
        self.assignment_tree.delete(*self.assignment_tree.get_children())
        for ext, category in sorted(self.draft.items()):
            self.assignment_tree.insert("", "end", values=(ext, category))

    def pick_assignment(self, event):
        selected = self.assignment_tree.selection()
        if selected:
            ext, category = self.assignment_tree.item(selected[0], "values")
            self.extension.set(ext)
            self.category.set(category)

    def assign(self):
        name = self.category.get().strip()
        try:
            ConfigurationService().validate_category_name(name)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.draft[self.extension.get().strip().lower()] = name
        self.refresh_assignments()

    def remove(self):
        self.draft.pop(self.extension.get().strip().lower(), None)
        self.refresh_assignments()

    def reset(self):
        self.draft = dict(self.configuration["kategorien"])
        self.refresh_assignments()

    def save_assignments(self):
        self.persist(kategorien=dict(self.draft))

    def close(self):
        if self.job.busy:
            self.closing = True
            self.cancel()
        else:
            self.root.destroy()

    def cancel(self):
        self.job.stop.set()
        log.info("Abbruch angefordert")
        self.status.set("Abbruch angefordert …")

    def update_progress(self, count, total, errors):
        if total:
            self.bar.stop()
            self.bar.configure(mode="determinate", maximum=total, value=count)
        self.status.set(f"{self.phase} · Dateien: {count}" + (f"/{total} ({100 * count / total:.0f} %)" if total else "") + f" · Fehler: {errors}")

    def animate(self, index=0):
        self.indicator.configure(image=self.animation[index])
        self.animation_id = self.root.after(90, self.animate, (index+1) % len(self.animation))

    def end_progress(self):
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.indicator.configure(image=self.design.image("info", 18, self.design.muted))
        self.bar.stop()
        self.progress_area.pack_forget()

    def job_error(self, error):
        log.error("Vorgang fehlgeschlagen: %s", error)
        self.status.set(str(error))
        if not self.job.busy:
            self.end_progress()
            self.abort.configure(state="disabled")
            if self.closing:
                self.root.destroy()

    def run_job(self, phase, work, finished):
        if self.job.busy:
            return
        self.phase = phase
        self.status.set(phase)
        log.info("%s gestartet", phase)
        self.progress_area.pack(side="bottom", fill="x", before=self.shell)
        self.animate()
        self.abort.configure(state="normal")
        self.bar.configure(mode="indeterminate")
        self.bar.start()
        def complete(value, cancelled):
            self.end_progress()
            self.bar.configure(mode="determinate")
            self.abort.configure(state="disabled")
            log.info("%s beendet, Abbruch=%s", phase, cancelled)
            if self.closing:
                self.root.destroy()
                return
            finished(value, cancelled)
        self.job.start(work, complete)

    def analyze_folder(self):
        folder = self.selected_folder
        if not folder:
            self.status.set("Bitte einen Ordner auswählen.")
            return
        service = AnalysisService()
        errors = []
        def work(stop, report, ask):
            return service.analyze_files(folder, self.configuration["kategorien"], self.options,
                                         protected_paths=(self.configuration_path,), cancelled=stop, progress=report, on_error=lambda p,e: errors.append(str(e)))
        def finish(result, stopped):
            self.analyzed = bool(result) and not stopped
            self.page("Analyse")
            self.analysis_tree.delete(*self.analysis_tree.get_children())
            percentages = service.calculate_percentages(result)
            for ext, item in sorted(result.items()):
                self.analysis_tree.insert("", "end", image=self.design.image(file_icon(ext), 20), values=(ext or "ohne Endung", item["anzahl"], f"{percentages[ext]:.1f} %", item["kategorie"] or "–"))
            self.status.set(("Abgebrochen" if stopped else "Analyse abgeschlossen") +
                            f" · Dateien: {sum(item['anzahl'] for item in result.values())} · Fehler: {len(errors)}")
        self.run_job("Analyse", work, finish)

    def sort_files(self):
        folder = self.selected_folder
        if not folder or self.draft != self.configuration["kategorien"]:
            self.status.set("Ordner auswählen und Änderungen an Zuordnungen speichern oder verwerfen.")
            return
        def finish(plan, stopped):
            if stopped or not plan:
                self.status.set("Vorschau abgebrochen" if stopped else "Keine passenden Dateien")
                return
            self.preview_window(folder, plan)
        self.run_job("Vorschau", lambda stop, report, ask: self.service.preview_sorting(
            folder, self.configuration["kategorien"], self.options, protected_paths=(self.configuration_path,), cancelled=stop, progress=report), finish)

    def preview_window(self, folder, plan):
        window = tk.Toplevel(self.root)
        window.title("Sortiervorschau")
        window.geometry("760x380")
        window.transient(self.root)
        buttons = ttk.Frame(window)
        buttons.pack(side="bottom", fill="x")
        view = tree(window, {"source": "Quelle", "target": "Geplantes Ziel", "status": "Status"})
        for key, entry in plan.items():
            view.insert("", "end", values=(key, entry["destination"].relative_to(folder), LABELS[entry["status"]]))
        def cancel():
            log.info("Vorschau verworfen: %s", folder)
            window.destroy()
            self.status.set("Vorschau abgebrochen")
        def confirm():
            window.destroy()
            def work(stop, report, ask):
                def decide(source, target):
                    return ask(lambda: "rename" if messagebox.askyesno(
                        "Namenskonflikt", "Beide Dateien behalten und die eingehende Datei umbenennen?",
                        detail=f"Quelle: {source}\nBelegtes Ziel: {target}", parent=self.root, default="no") else "skip")
                return self.service.organize_files(folder, plan, conflict=self.options.conflict,
                                                   decide=decide, cancelled=stop, progress=report)
            self.run_job("Sortierung", work, self.results)
        window.protocol("WM_DELETE_WINDOW", cancel)
        self.cancel_preview_button = ttk.Button(buttons, text="Abbrechen", command=cancel)
        self.cancel_preview_button.pack(side="right")
        self.start_sort_button = ttk.Button(buttons, text="Sortierung starten", command=confirm)
        self.start_sort_button.pack(side="right")
        window.grab_set()

    def results(self, rows, stopped):
        self.has_results = True
        self.page("Ergebnisse")
        self.sorting_tree.delete(*self.sorting_tree.get_children())
        for name, row in rows.items():
            target = "" if row["status"] in ("skipped", "cancelled") else row["destination"]
            self.sorting_tree.insert("", "end", image=self.design.image(file_icon(Path(name).suffix), 20), values=(name, row["source"], target, LABELS[row["status"]], row.get("error", "")))
        self.status.set(("Abgebrochen · " if stopped else "") + summary(rows))

    def undo(self):
        folder = self.selected_folder
        if folder and not self.job.busy and messagebox.askyesno("Rückgängig", "Letzten Lauf für diesen Ordner zurücknehmen?", parent=self.root):
            self.run_job("Rücknahme", lambda stop, report, ask: self.service.undo(folder, cancelled=stop, progress=report), self.results)


def start_gui():
    path = Path("config.json")
    config = ConfigurationService().load_configuration(path)
    root = tk.Tk()
    OrganizerGUI(root, config, path)
    root.mainloop()


def run_gui():
    start_gui()


if __name__ == "__main__":
    run_gui()


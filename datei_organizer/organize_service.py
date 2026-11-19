import logging
import shutil
from pathlib import Path
from typing import TypedDict
import re

class FilePaths(TypedDict):
    source: Path
    destination: Path
    status: str
        

class OrganizeService:
    """
    Service for sorting files into their assigned categories
    """
    def determine_category(self, file_path: Path, categories: dict[str, str]) -> str | None:
        """Return the configured category, or None for an unmapped extension."""
        category = categories.get(file_path.suffix.lower())
        if category is None:
            return None
        return category
    

    def organize_files(self, folder: Path, categories: dict[str, str]) -> dict[str, FilePaths]:
        """Move mapped files in the selected folder without overwriting existing files and return dict of successfully moved files"""
        if not folder.is_dir():
            raise FileNotFoundError("Arbeitsverzeichnis nicht gefunden")

        # Resolve the base folder before checking destination containment.
        absolute_folder = folder.resolve()
        
        result_dict: dict[str, FilePaths] = {}
        for file_path in folder.iterdir():
            if file_path.is_dir():
                continue
             
            category = self.determine_category(file_path, categories)
            if category is None:
                continue

            destination_folder = absolute_folder / category
            destination_folder = destination_folder.resolve()

            if not destination_folder.is_relative_to(absolute_folder):
                raise ValueError("Fertiger Pfad liegt nicht innerhalb von ordner Pfad")

            if not destination_folder.exists():
                try:

                    # Create the category folder only when it does not exist.
                    destination_folder.mkdir()
                    logging.info("Der Ordner %s wurde erfolgreich erstellt", destination_folder)
                except OSError as error:
                    logging.warning("Ordner konnte nicht erstellt werden: %s", error)
                    continue
            else:
                    logging.info("Der Ordner %s ist bereits vorhanden", destination_folder)

            # Preserve the original file name in the destination folder.
            destination_file = destination_folder / file_path.name
                           
            # Build the source path from the resolved base folder.
            source_file = absolute_folder / file_path.name
                        
            status = "moved"
            if destination_file.exists():
                log = f"Datei %s existiert bereits in %s"
                status = "conflict"
            else:
                try:
                    # Move the source file into its configured category folder.
                    shutil.move(source_file, destination_folder)
                    log = f"Datei %s wurde erfolgreich nach %s verschoben"
                except OSError:
                    logging.exception("Die Datei %s konnte nicht nach %s verschoben werden ", source_file, destination_folder)
                    continue
            logging.info(log, source_file, destination_folder)
            result_dict[file_path.name] = {"source": source_file, "destination": destination_file, "status": status} 

        return result_dict

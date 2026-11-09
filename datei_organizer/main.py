from pathlib import Path, PureWindowsPath, PurePosixPath
import logging
from logging.handlers import RotatingFileHandler
import shutil
import json

handler = RotatingFileHandler(filename="Hauptlog.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")

handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
stream_formatter = logging.Formatter("%(levelname)s - %(message)s")
stream_handler.setFormatter(stream_formatter)
logging.getLogger().addHandler(stream_handler)

def load_configuration(configuration_path: Path):
    """Load the configuration and validate its structure and category names."""
    try:
        with configuration_path.open("r", encoding="utf-8") as configuration_file:
            configuration = json.load(configuration_file)
            if not isinstance(configuration, dict):
                raise ValueError("Config Datei enthält kein Dict")
            elif "ordner" not in configuration or "kategorien" not in configuration or not isinstance(configuration["ordner"], str) or not isinstance(configuration["kategorien"], dict):
                raise ValueError("Erforderliche Struktur oder Datentypen stimmen nicht")
            for file_extension, category in configuration["kategorien"].items():
                # An empty extension represents files without a suffix.
                if not isinstance(file_extension, str) or (file_extension != "" and not file_extension.strip()):
                    raise ValueError("JSON Datei enthält falsche Werte")
                validate_category_name(category)

            if not configuration["ordner"].strip():
                raise ValueError("In der JSON fehlen Werte")

            return configuration
    except FileNotFoundError as error:
        raise FileNotFoundError("Config Datei nicht gefunden") from error


def validate_category_name(category: str) -> None:
    """Validate a category name and raise ValueError if it is invalid."""
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Falscher Datentyp oder leerer String")
    # Check both path syntaxes even when running on only one operating system.
    windows_path = PureWindowsPath(category)
    posix_path = PurePosixPath(category)
    if windows_path.is_absolute() or posix_path.is_absolute() or ".." in windows_path.parts or ".." in posix_path.parts or windows_path.drive != "" or "/" in category or "\\" in category:
        raise ValueError("Pfadangabe enthalten")
    if category == ".":
        raise ValueError("Pfadangabe enthalten")


def save_configuration(configuration_path: Path, configuration: dict) -> None:
    """Write the complete configuration as UTF-8 JSON."""
    with configuration_path.open("w", encoding="utf-8") as configuration_file:
        json.dump(configuration, configuration_file, indent=4, ensure_ascii=False)


def determine_category(file_path: Path, categories: dict[str, str]) -> str | None:
    """Return the configured category, or None for an unmapped extension."""
    category = categories.get(file_path.suffix.lower())
    if category is None:
        return None
    return category

def organize_files(folder: Path, categories: dict[str, str]) -> None:
    """Move mapped files in the selected folder without overwriting existing files."""
    if not folder.is_dir():
        raise FileNotFoundError("Arbeitsverzeichnis nicht gefunden")

    # Resolve the base folder before checking destination containment.
    absolute_folder = folder.resolve()

    for file_path in folder.iterdir():
        if file_path.is_dir():
            continue

        category = determine_category(file_path, categories)
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
        # Keep existing destination files instead of overwriting them.
        if destination_file.exists():
            logging.info("Datei existiert bereits: %s", destination_file)
            continue
        # Build the source path from the resolved base folder.
        source_file = absolute_folder / file_path.name

        try:
            # Move the source file into its configured category folder.
            shutil.move(source_file, destination_folder)
            logging.info("Datei %s wurde erfolgreich nach %s verschoben", source_file, destination_folder)
        except OSError:
            logging.exception("Die Datei %s konnte nicht nach %s verschoben werden ", source_file, destination_folder)

def analyze_files(folder_path: Path, categories: dict) -> dict:
    """Count files recursively by extension and look up their configured categories."""
    analysis_result = {}
    folder = Path(folder_path)
    for path in folder.rglob("*"):
        if path.is_file():
            file_extension = path.suffix.lower()
            if file_extension in analysis_result:
                analysis_result[file_extension]["anzahl"] += 1
            else:
                analysis_result[file_extension] = {"anzahl" : 1, "kategorie" : categories.get(file_extension)}
    return analysis_result

def calculate_percentages(analysis_result: dict) -> dict:
    """Return each extension group's percentage of the analyzed files."""
    total_files = sum(entry["anzahl"] for entry in analysis_result.values())
    percentages = {}
    for file_extension in analysis_result:
        count = analysis_result[file_extension]["anzahl"]
        percentage = count / total_files * 100
        percentages.update({file_extension : percentage})
    return percentages

def display_analysis(analysis_result, percentages):
    """Print counts, percentages, and categories for each extension group."""
    for item in analysis_result:
        count = analysis_result[item]["anzahl"]
        percentage = percentages[item]
        category = analysis_result[item]["kategorie"]
        if item == "":
            item = "ohne Endung"
        if category is None:
            category = "nicht zugeordnet"
        print(f"Dateiendung: {item}, Anzahl: {count}, Prozent: {percentage:.2f}%, Kategorie: {category}")

if __name__ == "__main__":
    configuration_path = Path("config.json")

    try:

        configuration = load_configuration(configuration_path)

    except FileNotFoundError as error:
        print(f"Datei nicht gefunden: {error}")
        raise SystemExit(1)
    except json.JSONDecodeError as error:
        print(f"JSON fehlerhaft: {error}")
        raise SystemExit(1)
    except ValueError as error:
        print(f"Werte in JSON nicht korrekt: {error}")
        raise SystemExit(1)


    categories = configuration["kategorien"]
    folder = Path(configuration["ordner"])

    try:
        organize_files(folder, categories)
    except FileNotFoundError as error:
        print(f"Arbeitsverzeichnis nicht gefunden: {error}")
        raise SystemExit(1)
    analysis_result = analyze_files(folder, categories)
    percentages = calculate_percentages(analysis_result)
    display_analysis(analysis_result, percentages)

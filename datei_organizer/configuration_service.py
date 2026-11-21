from pathlib import Path, PureWindowsPath, PurePosixPath
import json
from .log_service import log
import os
import tempfile
from .scanning import Options
from typing import TypedDict

class _OptionalConfiguration(TypedDict, total=False):
    optionen: dict


class ConfigurationData(_OptionalConfiguration):
    ordner: str
    kategorien: dict[str, str]

class ConfigurationService:
    """
    Handles loading, saving, and validation
    """
    def load_configuration(self, configuration_path: Path) -> ConfigurationData:
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
                    self.validate_category_name(category)

                if not configuration["ordner"].strip():
                    raise ValueError("In der JSON fehlen Werte")

                Options.load(configuration.get("optionen", {}))
                log.debug("Konfiguration geladen: %s", configuration_path)
                return configuration
        except FileNotFoundError as error:
            raise FileNotFoundError("Config Datei nicht gefunden") from error


    def save_configuration(self, configuration_path: Path, configuration: ConfigurationData) -> None:
        """Write the complete configuration as UTF-8 JSON."""
        try:
            serialized_configuration = json.dumps(configuration, indent=4, ensure_ascii=False)
            configuration_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=configuration_path.parent,
                                             delete=False) as temp:
                temp_path = Path(temp.name)
            try:
                temp_path.write_text(serialized_configuration, encoding="utf-8")
                os.replace(temp_path, configuration_path)
                log.info("Konfiguration gespeichert: %s", configuration_path)
            finally:
                temp_path.unlink(missing_ok=True)
        except OSError as error:
            raise OSError(f"{configuration_path} kann nicht erstellt werden: {error}") from error
        except TypeError as error:
            raise TypeError(f"{configuration} enthält ungültige Werte: {error}") from error


    def validate_category_name(self, category: str) -> None:
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
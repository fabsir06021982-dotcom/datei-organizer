from .log_service import log
from .scanning import Options, scan
from typing import TypedDict

class AnalysisEntry(TypedDict):
    anzahl: int
    kategorie: str | None



class AnalysisService:
    """
    Calculates the analysis result and returns it
    """
    def analyze_files(self, folder_path, categories, options=None, *, protected_paths=(), cancelled=lambda: False,
                      progress=lambda *args: None, on_error=lambda *args: None):
        """Count matching files, reporting discovery and processing separately."""
        files = []
        errors = 0
        def error(path, exc):
            nonlocal errors
            errors += 1
            on_error(path, exc)
            progress(len(files), 0, errors)
        for path in scan(folder_path, categories, options or Options(), cancelled, error, protected_paths):
            files.append(path)
            progress(len(files), 0, errors)
        result = {}
        for index, path in enumerate(files, 1):
            if cancelled():
                break
            extension = path.suffix.lower()
            entry = result.setdefault(extension, {"anzahl": 0, "kategorie": categories.get(extension)})
            entry["anzahl"] += 1
            progress(index, len(files), errors)
        log.info("Analyse in %s: %d Dateien, %d Fehler, Abbruch=%s", folder_path, len(files), errors, cancelled())
        return result

    def calculate_percentages(self, analysis_result: dict[str, AnalysisEntry]) -> dict[str, float]:
        """Return each extension group's percentage of the analyzed files."""
        total_files = sum(entry["anzahl"] for entry in analysis_result.values())
        percentages = {}
        for file_extension in analysis_result:
            count = analysis_result[file_extension]["anzahl"]
            percentage = count / total_files * 100
            percentages.update({file_extension : percentage})
        return percentages


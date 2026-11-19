from pathlib import Path
from typing import TypedDict

class AnalysisEntry(TypedDict):
    anzahl: int
    kategorie: str | None



class AnalysisService:
    """
    Calculates the analysis result and returns it
    """
    def analyze_files(self, folder_path: Path, categories: dict[str, str]) -> dict[str, AnalysisEntry]:
        """Count files by extension and look up their configured categories."""
        analysis_result: dict[str, AnalysisEntry] = {}
        folder = Path(folder_path)
        for path in folder.glob("*"):
            if path.is_file():
                file_extension = path.suffix.lower()
                if file_extension in analysis_result:
                    analysis_result[file_extension]["anzahl"] += 1
                else:
                    analysis_result[file_extension] = {"anzahl" : 1, "kategorie" : categories.get(file_extension)}
        return analysis_result


    def calculate_percentages(self, analysis_result: dict[str, AnalysisEntry]) -> dict[str, float]:
        """Return each extension group's percentage of the analyzed files."""
        total_files = sum(entry["anzahl"] for entry in analysis_result.values())
        percentages = {}
        for file_extension in analysis_result:
            count = analysis_result[file_extension]["anzahl"]
            percentage = count / total_files * 100
            percentages.update({file_extension : percentage})
        return percentages


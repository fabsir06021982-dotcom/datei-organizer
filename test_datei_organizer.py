from pathlib import Path
from main import bestimme_kategorie, kategorien


def test_bestimme_kategorie():
    result = bestimme_kategorie(Path("beispiel.txt"), kategorien)
    assert result == "texte"
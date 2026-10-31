import pytest
from pathlib import Path
from main import bestimme_kategorie

kategorien = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

@pytest.mark.parametrize("input1, expected", [("beispiel.txt", "texte"), ("bild.png", "bilder"), ("archive.xyz", "sonstiges")])
def test_txt(input1: str, expected: str):
    pfad = Path(input1)
    
    result = bestimme_kategorie(pfad, kategorien)
    assert result == expected

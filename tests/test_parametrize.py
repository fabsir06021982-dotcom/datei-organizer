import pytest
from pathlib import Path
from datei_organizer.main import determine_category

categories = {
    ".txt": "texte",
    ".png": "bilder",
    ".jpg": "bilder",
    ".pdf": "dokumente"
}

@pytest.mark.parametrize("input1, expected", [("beispiel.txt", "texte"), ("bild.png", "bilder"), ("archive.xyz", None)])
def test_txt(input1: str, expected: None | str):
    path = Path(input1)

    result = determine_category(path, categories)
    assert result == expected


    

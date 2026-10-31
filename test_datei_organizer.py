from pathlib import Path
from main import bestimme_kategorie, kategorien



def test_txt():
    result = bestimme_kategorie(Path("beispiel.txt"), kategorien)
    assert result == "texte"

def test_png():
    result = bestimme_kategorie(Path("bild.png"), kategorien)
    assert result == "bilder"

def test_unbekannt():
    result = bestimme_kategorie(Path("archiv.xyz"), kategorien)
    assert result == "sonstiges"

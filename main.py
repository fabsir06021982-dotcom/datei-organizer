from pathlib import Path

ordner = Path("testdateien")

for datei in ordner.iterdir():
    print(datei.stem, datei.suffix)


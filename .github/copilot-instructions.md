# Copilot instructions for datei-organizer

## Build, test, and lint commands

This repository does not currently define a build system, test suite, or lint configuration. There is no `pytest`, `tox`, `ruff`, `flake8`, `pyproject.toml`, `setup.cfg`, `package.json`, or CI workflow to use.

Use the following as the default validation command from the repository root:

```bash
python main.py
```

This project is intentionally tiny and centered on a single script. Treat `python main.py` as the primary smoke test. Because the script uses a relative path (`testdateien`), it should be run from the repo root so the file organization logic resolves correctly.

## High-level architecture

This repository is a very small Python utility for organizing files in `testdateien/` by file extension.

- `main.py` is the only application entry point.
- It defines a `Path` object for `testdateien` and a `kategorien` dictionary that maps extensions to destination folders.
- The script iterates over files in the directory and checks each file's suffix to determine where it should be placed.
- The intended behavior is extension-based grouping such as `".txt" -> "texte"`, `".png"`/`".jpg"` -> `"bilder"`, and `".pdf"` -> `"dokumente"`.

There is no package structure, no CLI framework, and no multi-module architecture yet. Changes should stay small and readable unless the repository expands substantially.

## Key conventions

- Keep commands and file paths relative to the repository root; do not assume an IDE-specific working directory.
- Favor direct, simple Python patterns over introducing abstractions or new frameworks.
- Treat `testdateien/` as sample data. It is intentionally ignored via `.gitignore` and should not be treated as production data.
- When working with files, prefer `pathlib.Path` and `.suffix` over manual string parsing.
- Preserve the repo's minimal scope: a single script that sorts files by extension.
- Avoid adding unrelated infrastructure or broad refactors for a project this small.

## Repository context

- The project is a single-file Python utility, not a large application.
- The README is intentionally minimal, so the behavior is defined mainly by `main.py` and the sample files in `testdateien/`.
- If you need to validate a change, prefer a direct script-level check instead of inventing a full test harness that is not present in the repo.

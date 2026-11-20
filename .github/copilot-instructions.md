# Working on the File Organizer

Install dependencies with `poetry install`. Run the full suite with `poetry run python -m pytest tests -q`. GUI tests require Tk and a desktop session. Windows covers the junction-specific test.

Keep parsing, prompts and presentation in the CLI and GUI. Both frontends use shared services for configuration, scanning, previews, file moves and undo. Preserve the separation between preview and execution. Exercise filesystem changes in temporary directories with an isolated move journal.

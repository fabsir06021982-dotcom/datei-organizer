import pytest


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    monkeypatch.setenv("DATEI_ORGANIZER_HISTORY", str(tmp_path / "history"))
    yield
    from datei_organizer.log_service import configure_logging, log
    configure_logging(False)
    log.disabled = False

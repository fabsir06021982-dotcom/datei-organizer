from collections.abc import Callable
from .log_service import prepare_logging

class Application:
    def start(self, start_interface: Callable[[], None]) -> None:
        prepare_logging()
        start_interface()

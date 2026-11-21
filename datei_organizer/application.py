from collections.abc import Callable

class Application:
    def start(self, start_interface: Callable[[], None]) -> None:
        start_interface()

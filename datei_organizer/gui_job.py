"""Keep file work off the Tk thread and marshal dialogs back to it."""
from queue import Empty, Queue
from threading import Event, Lock, Thread


class GuiJob:
    def __init__(self, root, progress, on_error):
        self.root, self.progress, self.on_error = root, progress, on_error
        self.busy = False
        self.stop = Event()
        self.lock = Lock()
        self.latest = None

    def report(self, count, total, errors):
        with self.lock:
            self.latest = count, total, errors

    def start(self, work, finish):
        if self.busy:
            return False
        self.busy = True
        self.stop.clear()
        queue = Queue()

        def ask(dialog):
            answered = Event()
            answer = []
            queue.put(("question", (dialog, answer, answered)))
            while not answered.wait(0.05):
                if self.stop.is_set():
                    return "skip"
            return answer[0]

        def run():
            try:
                queue.put(("done", work(self.stop.is_set, self.report, ask)))
            except Exception as exc:
                queue.put(("error", exc))

        def poll():
            with self.lock:
                update, self.latest = self.latest, None
            if update is not None:
                self.progress(*update)
            try:
                kind, value = queue.get_nowait()
            except Empty:
                self.root.after(25, poll)
                return
            if kind == "question":
                dialog, answer, answered = value
                try:
                    answer.append("skip" if self.stop.is_set() else dialog())
                except Exception as exc:
                    answer.append("skip")
                    self.stop.set()
                    self.on_error(exc)
                finally:
                    answered.set()
                self.root.after(10, poll)
                return
            self.busy = False
            if kind == "error":
                self.on_error(value)
            else:
                finish(value, self.stop.is_set())

        Thread(target=run, daemon=False).start()
        self.root.after(10, poll)
        return True


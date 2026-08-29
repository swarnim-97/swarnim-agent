from collections.abc import Callable, Iterable, Iterator
from queue import Queue
from threading import Thread


_STOP = object()


class BackgroundWorker:
    """Process queued text on one managed background thread."""

    def __init__(
        self,
        input_queue: Queue[object],
        process: Callable[[str], Iterable[str]],
        on_line: Callable[[str], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self._input_queue = input_queue
        self._process = process
        self._on_line = on_line
        self._on_error = on_error
        self._thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the processing thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the processing loop."""
        if self._thread is not None:
            raise RuntimeError("Background worker has already been started")

        self._thread = Thread(
            target=self._process_loop,
            name="swarnim-agent-worker",
            daemon=False,
        )
        self._thread.start()

    def stop(self) -> None:
        """Request a graceful stop and wait for the thread to finish."""
        if self._thread is None:
            return

        self._input_queue.put(_STOP) # “After processing earlier items, exit your processing loop.”
        self._thread.join() # This blocks the thread executing stop() until the worker thread has completely exited.
        self._thread = None

    def _process_loop(self) -> None:
        while True:
            item = self._input_queue.get()

            try:
                if item is _STOP:
                    return

                if not isinstance(item, str):
                    self._on_error(
                        TypeError("Background worker accepts only text input")
                    )
                    continue

                self._publish_lines(item)
            finally:
                self._input_queue.task_done() # “The item previously taken using get() has now finished processing.”

    def _publish_lines(self, text: str) -> None:
        """Publish each valid line while isolating processor failures."""
        try:
            lines = self._process(text)
            if isinstance(lines, str):
                raise TypeError(
                    "Background processor must return an iterable of lines, "
                    "not a string"
                )
            iterator: Iterator[str] = iter(lines)
        except Exception as error:
            self._on_error(error)
            return

        while True:
            try:
                line = next(iterator)
            except StopIteration:
                return
            except Exception as error:
                self._on_error(error)
                return

            if not isinstance(line, str):
                self._on_error(
                    TypeError("Background processor must yield only text lines")
                )
                return

            self._on_line(line)

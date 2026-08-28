from collections.abc import Callable
from queue import Queue
from threading import Thread


_STOP = object()


class BackgroundWorker:
    """Process queued text on one managed background thread."""

    def __init__(
        self,
        input_queue: Queue[object],
        process: Callable[[str], str],
        on_result: Callable[[str], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self._input_queue = input_queue
        self._process = process
        self._on_result = on_result
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

                try:
                    result = self._process(item)
                except Exception as error:
                    self._on_error(error)
                else: # Call _on_result(result) only when _process(text) completes successfully.
                    self._on_result(result)
            finally:
                self._input_queue.task_done() # “The item previously taken using get() has now finished processing.”

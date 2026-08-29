from collections.abc import Iterator
from queue import Queue
from threading import Event

from swarnim_agent.processing.worker import BackgroundWorker


def test_worker_streams_lines_on_background_thread() -> None:
    input_queue: Queue[object] = Queue()
    lines: list[str] = []
    errors: list[Exception] = []
    completed = Event()

    def on_line(line: str) -> None:
        lines.append(line)
        if len(lines) == 2:
            completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: ("Calculating...", str(len(text))),
        on_line=on_line,
        on_error=errors.append,
    )

    worker.start()
    try:
        input_queue.put("hello")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert lines == ["Calculating...", "5"]
    assert errors == []
    assert worker.is_running is False


def test_worker_preserves_fifo_order() -> None:
    input_queue: Queue[object] = Queue()
    lines: list[str] = []
    completed = Event()

    def process(text: str) -> tuple[str, str]:
        return f"{text}: started", f"{text}: finished"

    def on_line(line: str) -> None:
        lines.append(line)
        if len(lines) == 6:
            completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=process,
        on_line=on_line,
        on_error=lambda error: None,
    )

    worker.start()
    try:
        input_queue.put("first")
        input_queue.put("second")
        input_queue.put("third")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert lines == [
        "first: started",
        "first: finished",
        "second: started",
        "second: finished",
        "third: started",
        "third: finished",
    ]


def test_worker_reports_partial_stream_error_and_continues_processing() -> None:
    input_queue: Queue[object] = Queue()
    lines: list[str] = []
    errors: list[Exception] = []
    completed = Event()

    def process(text: str) -> Iterator[str]:
        if text == "bad":
            yield "bad: started"
            raise ValueError("bad input")
        yield text.upper()

    def on_line(line: str) -> None:
        lines.append(line)
        if line == "GOOD":
            completed.set()

    def on_error(error: Exception) -> None:
        errors.append(error)

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=process,
        on_line=on_line,
        on_error=on_error,
    )

    worker.start()
    try:
        input_queue.put("bad")
        input_queue.put("good")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)
    assert str(errors[0]) == "bad input"
    assert lines == ["bad: started", "GOOD"]


def test_worker_reports_error_before_first_line() -> None:
    input_queue: Queue[object] = Queue()
    lines: list[str] = []
    errors: list[Exception] = []
    completed = Event()

    def process(text: str) -> Iterator[str]:
        raise ValueError("could not start")
        yield text

    def on_error(error: Exception) -> None:
        errors.append(error)
        completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=process,
        on_line=lines.append,
        on_error=on_error,
    )

    worker.start()
    try:
        input_queue.put("hello")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert lines == []
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)
    assert str(errors[0]) == "could not start"


def test_worker_rejects_plain_string_as_line_stream() -> None:
    input_queue: Queue[object] = Queue()
    errors: list[Exception] = []
    completed = Event()

    def on_error(error: Exception) -> None:
        errors.append(error)
        completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: text.upper(),
        on_line=lambda line: None,
        on_error=on_error,
    )

    worker.start()
    try:
        input_queue.put("hello")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert len(errors) == 1
    assert isinstance(errors[0], TypeError)
    assert str(errors[0]) == (
        "Background processor must return an iterable of lines, not a string"
    )


def test_worker_rejects_non_string_line() -> None:
    input_queue: Queue[object] = Queue()
    lines: list[str] = []
    errors: list[Exception] = []
    completed = Event()

    def on_error(error: Exception) -> None:
        errors.append(error)
        completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: ("valid", 5),
        on_line=lines.append,
        on_error=on_error,
    )

    worker.start()
    try:
        input_queue.put("hello")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert lines == ["valid"]
    assert len(errors) == 1
    assert isinstance(errors[0], TypeError)
    assert str(errors[0]) == "Background processor must yield only text lines"


def test_worker_stop_drains_queued_streams() -> None:
    input_queue: Queue[object] = Queue()
    lines: list[str] = []
    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: (f"{text}: started", f"{text}: finished"),
        on_line=lines.append,
        on_error=lambda error: None,
    )

    worker.start()
    input_queue.put("first")
    input_queue.put("second")
    worker.stop()

    assert lines == [
        "first: started",
        "first: finished",
        "second: started",
        "second: finished",
    ]
    assert input_queue.unfinished_tasks == 0
    assert worker.is_running is False


def test_worker_rejects_second_start() -> None:
    input_queue: Queue[object] = Queue()
    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: (text,),
        on_line=lambda line: None,
        on_error=lambda error: None,
    )

    worker.start()
    try:
        try:
            worker.start()
        except RuntimeError as error:
            assert str(error) == "Background worker has already been started"
        else:
            raise AssertionError("Expected a second start to fail")
    finally:
        worker.stop()

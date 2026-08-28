from queue import Queue
from threading import Event

from swarnim_agent.processing.worker import BackgroundWorker


def test_worker_processes_text_on_background_thread() -> None:
    input_queue: Queue[object] = Queue()
    results: list[str] = []
    errors: list[Exception] = []
    completed = Event()

    def on_result(result: str) -> None:
        results.append(result)
        completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: str(len(text)),
        on_result=on_result,
        on_error=errors.append,
    )

    worker.start()
    try:
        input_queue.put("hello")
        assert completed.wait(timeout=1)
    finally:
        worker.stop()

    assert results == ["5"]
    assert errors == []
    assert worker.is_running is False


def test_worker_preserves_fifo_order() -> None:
    input_queue: Queue[object] = Queue()
    results: list[str] = []
    completed = Event()

    def on_result(result: str) -> None:
        results.append(result)
        if len(results) == 3:
            completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=str.upper,
        on_result=on_result,
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

    assert results == ["FIRST", "SECOND", "THIRD"]


def test_worker_reports_error_and_continues_processing() -> None:
    input_queue: Queue[object] = Queue()
    results: list[str] = []
    errors: list[Exception] = []
    completed = Event()

    def process(text: str) -> str:
        if text == "bad":
            raise ValueError("bad input")
        return text.upper()

    def on_result(result: str) -> None:
        results.append(result)
        completed.set()

    worker = BackgroundWorker(
        input_queue=input_queue,
        process=process,
        on_result=on_result,
        on_error=errors.append,
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
    assert results == ["GOOD"]


def test_worker_rejects_second_start() -> None:
    input_queue: Queue[object] = Queue()
    worker = BackgroundWorker(
        input_queue=input_queue,
        process=lambda text: text,
        on_result=lambda result: None,
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

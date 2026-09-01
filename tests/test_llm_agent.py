from collections.abc import Iterable
from types import SimpleNamespace

import pytest

from swarnim_agent.agents.llm import LLMAgent
from swarnim_agent.transports.chat_completions import ChatCompletionsTransport
from swarnim_agent.transports.errors import ProviderResponseError


class FakeExecutor:
    def __init__(self, chunks: Iterable[object]) -> None:
        self.chunks = chunks
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.chunks


def create_chunk(
    content: str | None,
    finish_reason: str | None = None,
) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=None,
    )


def create_agent(executor) -> LLMAgent:
    return LLMAgent(
        model="model-id",
        max_tokens=256,
        transport=ChatCompletionsTransport(),
        executor=executor,
    )


def test_llm_agent_streams_complete_lines_and_final_partial_text() -> None:
    executor = FakeExecutor(
        [
            create_chunk("First li"),
            create_chunk("ne\n\nSecond"),
            create_chunk(" line"),
            create_chunk(None, finish_reason="stop"),
        ]
    )
    agent = create_agent(executor)

    lines = list(agent.run("hello"))

    assert lines == [
        "Waiting for model response...",
        "First line",
        "",
        "Second line",
    ]
    assert executor.requests[0].parameters["messages"] == [
        {"role": "user", "content": "hello"}
    ]
    assert executor.requests[0].parameters["stream"] is True


def test_llm_agent_ignores_empty_chunks() -> None:
    executor = FakeExecutor(
        [
            create_chunk(None),
            create_chunk("Result\n"),
            create_chunk(""),
        ]
    )

    assert list(create_agent(executor).run("hello")) == [
        "Waiting for model response...",
        "Result",
    ]


def test_llm_agent_rejects_successful_stream_without_text() -> None:
    agent = create_agent(FakeExecutor([create_chunk(None, "stop")]))
    lines = agent.run("hello")

    assert next(lines) == "Waiting for model response..."
    with pytest.raises(ProviderResponseError, match="no text content"):
        next(lines)


def test_llm_agent_propagates_executor_failure_after_status_line() -> None:
    class FailingExecutor:
        def execute(self, request):
            raise RuntimeError("network failed")

    lines = create_agent(FailingExecutor()).run("hello")

    assert next(lines) == "Waiting for model response..."
    with pytest.raises(RuntimeError, match="network failed"):
        next(lines)


def test_llm_agent_preserves_completed_lines_but_not_partial_text_on_failure() -> None:
    def failing_chunks():
        yield create_chunk("Completed\npartial")
        raise RuntimeError("stream failed")

    lines = create_agent(FakeExecutor(failing_chunks())).run("hello")

    assert next(lines) == "Waiting for model response..."
    assert next(lines) == "Completed"
    with pytest.raises(RuntimeError, match="stream failed"):
        next(lines)


def test_llm_agent_propagates_chunk_normalization_failure() -> None:
    invalid_chunk = SimpleNamespace(usage=None)
    lines = create_agent(FakeExecutor([invalid_chunk])).run("hello")

    assert next(lines) == "Waiting for model response..."
    with pytest.raises(ProviderResponseError, match="no choices field"):
        next(lines)

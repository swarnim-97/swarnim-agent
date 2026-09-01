from types import SimpleNamespace

import pytest

from swarnim_agent.transports.chat_completions import ChatCompletionsTransport
from swarnim_agent.transports.errors import ProviderResponseError
from swarnim_agent.transports.types import ChatMessage, Usage


def test_transport_builds_streaming_request() -> None:
    transport = ChatCompletionsTransport()

    request = transport.build_request(
        model="model-id",
        messages=[ChatMessage(role="user", content="hello")],
        max_tokens=256,
    )

    assert request.api_mode == "chat_completions"
    assert request.parameters == {
        "model": "model-id",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 256,
        "stream": True,
    }


def test_transport_normalizes_text_chunk() -> None:
    transport = ChatCompletionsTransport()
    raw_chunk = SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content="partial text"),
                finish_reason=None,
            )
        ],
        usage=None,
    )

    chunk = transport.normalize_chunk(raw_chunk)

    assert chunk.text == "partial text"
    assert chunk.finish_reason is None
    assert chunk.usage is None


def test_transport_normalizes_finish_and_usage_chunk() -> None:
    transport = ChatCompletionsTransport()
    raw_chunk = SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=3,
            completion_tokens=4,
            total_tokens=7,
        ),
    )

    chunk = transport.normalize_chunk(raw_chunk)

    assert chunk.text == ""
    assert chunk.finish_reason == "stop"
    assert chunk.usage == Usage(
        input_tokens=3,
        output_tokens=4,
        total_tokens=7,
    )


def test_transport_accepts_usage_only_chunk_with_empty_choices() -> None:
    transport = ChatCompletionsTransport()
    raw_chunk = SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(
            prompt_tokens=2,
            completion_tokens=5,
            total_tokens=7,
        ),
    )

    chunk = transport.normalize_chunk(raw_chunk)

    assert chunk.text == ""
    assert chunk.finish_reason is None
    assert chunk.usage == Usage(
        input_tokens=2,
        output_tokens=5,
        total_tokens=7,
    )


def test_transport_ignores_incomplete_usage() -> None:
    transport = ChatCompletionsTransport()
    raw_chunk = SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(
            prompt_tokens=2,
            completion_tokens=None,
            total_tokens=2,
        ),
    )

    chunk = transport.normalize_chunk(raw_chunk)

    assert chunk.usage is None


def test_transport_rejects_chunk_without_choices_field() -> None:
    transport = ChatCompletionsTransport()
    raw_chunk = SimpleNamespace(usage=None)

    with pytest.raises(ProviderResponseError, match="no choices field"):
        transport.normalize_chunk(raw_chunk)


def test_transport_rejects_non_text_delta() -> None:
    transport = ChatCompletionsTransport()
    raw_chunk = SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=[{"type": "text"}]),
                finish_reason=None,
            )
        ],
        usage=None,
    )

    with pytest.raises(ProviderResponseError, match="non-text"):
        transport.normalize_chunk(raw_chunk)

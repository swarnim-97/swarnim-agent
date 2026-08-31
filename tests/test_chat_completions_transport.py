from types import SimpleNamespace

import pytest

from swarnim_agent.transports.chat_completions import ChatCompletionsTransport
from swarnim_agent.transports.errors import ProviderResponseError
from swarnim_agent.transports.types import ChatMessage, Usage


def test_transport_builds_non_streaming_request() -> None:
    transport = ChatCompletionsTransport()

    request = transport.build_request(
        model="openai/gpt-oss-20b",
        messages=[ChatMessage(role="user", content="hello")],
        max_tokens=256,
    )

    assert request.api_mode == "chat_completions"
    assert request.parameters == {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 256,
        "stream": False,
    }


def test_transport_normalizes_provider_response() -> None:
    transport = ChatCompletionsTransport()
    raw_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="First line\nSecond line"),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=3,
            completion_tokens=4,
            total_tokens=7,
        ),
    )

    response = transport.normalize_response(raw_response)

    assert response.content == "First line\nSecond line"
    assert response.finish_reason == "stop"
    assert response.usage == Usage(
        input_tokens=3,
        output_tokens=4,
        total_tokens=7,
    )


def test_transport_rejects_empty_response() -> None:
    transport = ChatCompletionsTransport()
    raw_response = SimpleNamespace(choices=[])

    with pytest.raises(ProviderResponseError, match="no choices"):
        transport.normalize_response(raw_response)

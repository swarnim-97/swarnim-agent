from unittest.mock import MagicMock

import pytest

from swarnim_agent.execution.openai_chat import OpenAIChatExecutor
from swarnim_agent.transports.types import ProviderRequest


def test_executor_calls_openai_compatible_client() -> None:
    client = MagicMock()
    expected_stream = iter([object(), object()])
    client.chat.completions.create.return_value = expected_stream
    executor = OpenAIChatExecutor(
        base_url="https://example.com/v1",
        api_key="secret-key",
        client=client,
    )
    request = ProviderRequest(
        api_mode="chat_completions",
        parameters={"model": "model-id", "messages": [], "stream": True},
    )

    stream = executor.execute(request)

    assert stream is expected_stream
    client.chat.completions.create.assert_called_once_with(
        model="model-id",
        messages=[],
        stream=True,
    )


def test_executor_rejects_other_api_modes() -> None:
    executor = OpenAIChatExecutor(
        base_url="https://example.com/v1",
        api_key="secret-key",
        client=MagicMock(),
    )
    request = ProviderRequest(api_mode="responses", parameters={})

    with pytest.raises(ValueError, match="responses"):
        executor.execute(request)

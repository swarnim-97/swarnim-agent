from types import SimpleNamespace

import pytest

from swarnim_agent.agents.llm import LLMAgent
from swarnim_agent.transports.chat_completions import ChatCompletionsTransport


class FakeExecutor:
    def __init__(self, response: object) -> None:
        self.response = response
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return self.response


def create_response(content: str) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason="stop",
            )
        ],
        usage=None,
    )


def test_llm_agent_builds_executes_and_yields_complete_lines() -> None:
    executor = FakeExecutor(create_response("First line\n\nSecond line"))
    agent = LLMAgent(
        model="model-id",
        max_tokens=256,
        transport=ChatCompletionsTransport(),
        executor=executor,
    )

    lines = list(agent.run("hello"))

    assert lines == [
        "Waiting for model response...",
        "First line",
        "Second line",
    ]
    assert executor.requests[0].parameters["messages"] == [
        {"role": "user", "content": "hello"}
    ]


def test_llm_agent_propagates_executor_failure_after_status_line() -> None:
    class FailingExecutor:
        def execute(self, request):
            raise RuntimeError("network failed")

    agent = LLMAgent(
        model="model-id",
        max_tokens=256,
        transport=ChatCompletionsTransport(),
        executor=FailingExecutor(),
    )
    lines = agent.run("hello")

    assert next(lines) == "Waiting for model response..."
    with pytest.raises(RuntimeError, match="network failed"):
        next(lines)

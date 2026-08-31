from dataclasses import dataclass
from queue import Queue

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import Layout
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.agents.base import Agent
from swarnim_agent.agents.llm import LLMAgent
from swarnim_agent.cli.controller import CLIController
from swarnim_agent.cli.keybindings import create_key_bindings
from swarnim_agent.configuration.errors import ConfigurationError
from swarnim_agent.configuration.loader import load_secrets, load_settings
from swarnim_agent.execution.openai_chat import OpenAIChatExecutor
from swarnim_agent.processing.worker import BackgroundWorker
from swarnim_agent.providers.runtime import resolve_provider_runtime
from swarnim_agent.transports.chat_completions import ChatCompletionsTransport


@dataclass(frozen=True)
class CLIRuntime:
    """Components whose lifecycles are managed while the CLI is running."""

    application: Application[None]
    worker: BackgroundWorker


# Wires UI, worker, and model dependencies without moving behavior into main.py.
def create_runtime() -> CLIRuntime:
    """Construct and connect the CLI application and background worker."""
    prompt_text = "> "
    agent = _create_agent()
    input_queue: Queue[object] = Queue()
    input_area = TextArea(
        prompt=prompt_text,
        multiline=False,
        height=1,
    )
    controller = CLIController(
        input_area=input_area,
        prompt_text=prompt_text,
        submit_text=input_queue.put,
    )
    worker = BackgroundWorker(
        input_queue=input_queue,
        process=agent.run,
        on_line=controller.render_line,
        on_error=controller.render_error,
    )

    application: Application[None] = Application(
        layout=Layout(input_area),
        key_bindings=create_key_bindings(controller),
        full_screen=False,
    )
    return CLIRuntime(application=application, worker=worker)


def run_cli() -> None:
    """Display startup guidance and run the terminal event loop."""
    try:
        runtime = create_runtime()
    except ConfigurationError as error:
        print_formatted_text(f"Configuration error: {error}")
        return

    print_formatted_text(HTML("<b>Swarnim Agent</b> — NVIDIA LLM CLI"))
    print_formatted_text(
        "Type a message and press Enter. Use /exit or Ctrl+C to quit."
    )
    runtime.worker.start()

    try:
        with patch_stdout():
            runtime.application.run()
    finally:
        runtime.worker.stop()


# Resolves configuration once and injects provider dependencies into the agent.
def _create_agent() -> Agent:
    settings = load_settings()
    secret_names = {
        provider.api_key_env
        for provider in settings.providers.values()
    }
    secrets = load_secrets(secret_names)
    runtime = resolve_provider_runtime(settings, secrets)
    transport = ChatCompletionsTransport()
    if runtime.api_mode != transport.api_mode:
        raise ConfigurationError(
            f"No transport is available for API mode '{runtime.api_mode}'"
        )
    executor = OpenAIChatExecutor(
        base_url=runtime.base_url,
        api_key=runtime.api_key,
    )
    return LLMAgent(
        model=runtime.model,
        max_tokens=runtime.max_tokens,
        transport=transport,
        executor=executor,
    )

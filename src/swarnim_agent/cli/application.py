from dataclasses import dataclass
from queue import Queue

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import Layout
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.controller import CLIController
from swarnim_agent.cli.handlers import text_length_lines
from swarnim_agent.cli.keybindings import create_key_bindings
from swarnim_agent.processing.worker import BackgroundWorker


@dataclass(frozen=True)
class CLIRuntime:
    """Components whose lifecycles are managed while the CLI is running."""

    application: Application[None]
    worker: BackgroundWorker


def create_runtime() -> CLIRuntime:
    """Construct and connect the CLI application and background worker."""
    prompt_text = "> "
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
        process=text_length_lines,
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
    print_formatted_text(HTML("<b>Swarnim Agent</b> — background processing CLI"))
    print_formatted_text("Type a message and press Enter. Use /exit or Ctrl+C to quit.")
    runtime = create_runtime()
    runtime.worker.start()

    try:
        with patch_stdout():
            runtime.application.run()
    finally:
        runtime.worker.stop()

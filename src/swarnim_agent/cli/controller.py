from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.handlers import echo_text, should_exit


class CLIController:
    """Handle terminal events and coordinate updates to CLI components."""

    def __init__(self, input_area: TextArea) -> None:
        self.input_area = input_area

    def handle_submit(self, event: KeyPressEvent) -> None:
        """Read submitted input, exit when requested, or echo the text."""
        submitted_text = self.input_area.text
        self.input_area.buffer.reset()

        if should_exit(submitted_text):
            event.app.exit()
            return

        run_in_terminal(
            lambda: print_formatted_text(echo_text(submitted_text))
        )

    def handle_exit(self, event: KeyPressEvent) -> None:
        """Close the terminal application."""
        event.app.exit()

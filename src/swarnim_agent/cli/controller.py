from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.handlers import echo_text, should_exit


class CLIController:
    """Handle terminal events and coordinate updates to CLI components."""

    def __init__(self, input_area: TextArea, prompt_text: str) -> None:
        self.input_area = input_area
        self.prompt_text = prompt_text

    def handle_submit(self, event: KeyPressEvent) -> None:
        """Read submitted input, exit when requested, or echo the text."""
        submitted_text = self.input_area.text
        self.input_area.buffer.reset()

        if should_exit(submitted_text):
            event.app.exit()
            return

        run_in_terminal(lambda: self._render_transcript(submitted_text))

    def handle_exit(self, event: KeyPressEvent) -> None:
        """Close the terminal application."""
        event.app.exit()

    def _render_transcript(self, submitted_text: str) -> None:
        """Print submitted input and its echo above the active prompt."""
        transcript = (
            f"{self.prompt_text}{submitted_text}\n"
            f"{echo_text(submitted_text)}"
        )
        print_formatted_text(transcript)

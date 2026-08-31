from collections.abc import Callable

from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.handlers import should_exit


# Keeps prompt-toolkit events and terminal redraw coordination out of agents.
class CLIController:
    """Handle terminal events and coordinate updates to CLI components."""

    def __init__(
        self,
        input_area: TextArea,
        prompt_text: str,
        submit_text: Callable[[str], None],
    ) -> None:
        self.input_area = input_area
        self.prompt_text = prompt_text
        self._submit_text = submit_text

    def handle_submit(self, event: KeyPressEvent) -> None:
        """Read submitted input, handle exit, or enqueue the text."""
        submitted_text = event.current_buffer.text
        self.input_area.buffer.reset()

        if should_exit(submitted_text):
            event.app.exit()
            return

        run_in_terminal(
            lambda: self._render_submission_and_enqueue(submitted_text)
        )

    def handle_exit(self, event: KeyPressEvent) -> None:
        """Close the terminal application."""
        event.app.exit()

    def render_line(self, line: str) -> None:
        """Print one background result line above the active prompt."""
        print_formatted_text(line)

    def render_error(self, error: Exception) -> None:
        """Print a background-processing error above the active prompt."""
        print_formatted_text(f"Error: {error}")

    def _render_submission_and_enqueue(self, submitted_text: str) -> None:
        """Persist submitted input before handing it to the worker."""
        print_formatted_text(f"{self.prompt_text}{submitted_text}")
        self._submit_text(submitted_text)

from prompt_toolkit.application import Application, run_in_terminal
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.handlers import echo_text, should_exit
from swarnim_agent.cli.keybindings import create_key_bindings


def create_application() -> Application[None]:
    """Build the prompt-toolkit application used by the echo CLI."""
    input_area = TextArea(
        prompt="> ",
        multiline=False,
    )

    def handle_submit(event: KeyPressEvent) -> None:
        submitted_text = input_area.text
        input_area.buffer.reset()

        if should_exit(submitted_text):
            event.app.exit()
            return

        run_in_terminal(lambda: print_formatted_text(echo_text(submitted_text)))

    application: Application[None] = Application(
        layout=Layout(input_area),
        key_bindings=create_key_bindings(handle_submit),
        full_screen=False,
    )
    return application


def run_cli() -> None:
    """Display startup guidance and run the terminal event loop."""
    print_formatted_text(HTML("<b>Swarnim Agent</b> — echo CLI"))
    print_formatted_text("Type a message and press Enter. Use /exit or Ctrl+C to quit.")
    create_application().run()

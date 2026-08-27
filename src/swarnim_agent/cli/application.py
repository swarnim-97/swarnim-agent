from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import Layout
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.controller import CLIController
from swarnim_agent.cli.keybindings import create_key_bindings


def create_application() -> Application[None]:
    """Build the prompt-toolkit application used by the echo CLI."""
    prompt_text = "> "
    input_area = TextArea(
        prompt=prompt_text,
        multiline=False,
        height=1,
    )
    controller = CLIController(input_area, prompt_text)

    application: Application[None] = Application(
        layout=Layout(input_area),
        key_bindings=create_key_bindings(controller),
        full_screen=False,
    )
    return application


def run_cli() -> None:
    """Display startup guidance and run the terminal event loop."""
    print_formatted_text(HTML("<b>Swarnim Agent</b> — echo CLI"))
    print_formatted_text("Type a message and press Enter. Use /exit or Ctrl+C to quit.")
    create_application().run()

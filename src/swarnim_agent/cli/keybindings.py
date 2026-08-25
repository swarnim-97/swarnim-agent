from prompt_toolkit.key_binding import KeyBindings

from swarnim_agent.cli.controller import CLIController


def create_key_bindings(controller: CLIController) -> KeyBindings:
    """Create the keyboard shortcuts used by the terminal application."""
    bindings = KeyBindings()

    bindings.add("enter")(controller.handle_submit)
    bindings.add("c-c")(controller.handle_exit)

    return bindings

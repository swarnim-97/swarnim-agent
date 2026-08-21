from collections.abc import Callable

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent


def create_key_bindings(on_submit: Callable[[KeyPressEvent], None]) -> KeyBindings:
    """Create the keyboard shortcuts used by the terminal application."""
    bindings = KeyBindings()

    bindings.add("enter")(on_submit)

    @bindings.add("c-c")
    def exit_application(event: KeyPressEvent) -> None:
        event.app.exit()

    return bindings

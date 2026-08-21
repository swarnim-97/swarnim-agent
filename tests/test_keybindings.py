from prompt_toolkit.keys import Keys

from swarnim_agent.cli.keybindings import create_key_bindings


def test_expected_key_bindings_are_registered() -> None:
    bindings = create_key_bindings(lambda event: None)
    registered_keys = {binding.keys for binding in bindings.bindings}

    assert (Keys.ControlM,) in registered_keys
    assert (Keys.ControlC,) in registered_keys

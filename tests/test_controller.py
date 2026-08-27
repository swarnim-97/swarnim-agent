from unittest.mock import MagicMock, patch

from prompt_toolkit.widgets import TextArea

from swarnim_agent.cli.controller import CLIController


def test_handle_submit_clears_and_echoes_input() -> None:
    input_area = TextArea(text="hello", multiline=False, height=1)
    controller = CLIController(input_area, prompt_text="> ")
    event = MagicMock()

    with patch("swarnim_agent.cli.controller.run_in_terminal") as run_in_terminal:
        controller.handle_submit(event)

    assert input_area.text == ""
    event.app.exit.assert_not_called()
    run_in_terminal.assert_called_once()

    render_output = run_in_terminal.call_args.args[0]
    with patch("swarnim_agent.cli.controller.print_formatted_text") as print_text:
        render_output()

    print_text.assert_called_once_with("> hello\nhello")


def test_handle_submit_exits_for_exit_command() -> None:
    input_area = TextArea(text=" /EXIT ", multiline=False, height=1)
    controller = CLIController(input_area, prompt_text="> ")
    event = MagicMock()

    with patch("swarnim_agent.cli.controller.run_in_terminal") as run_in_terminal:
        controller.handle_submit(event)

    assert input_area.text == ""
    event.app.exit.assert_called_once_with()
    run_in_terminal.assert_not_called()


def test_handle_exit_closes_application() -> None:
    controller = CLIController(
        TextArea(multiline=False, height=1),
        prompt_text="> ",
    )
    event = MagicMock()

    controller.handle_exit(event)

    event.app.exit.assert_called_once_with()

# Repository Instructions

## Project purpose

This is a learning-oriented Python CLI project inspired by the terminal
architecture explored in Hermes Agent. Build it incrementally so each new
concept can be understood before the project becomes more extensive.

When discussing or changing the project:

- Explain what is being added, why it is needed, and where it belongs.
- Surface reasonable alternatives and tradeoffs before choosing an approach.
- Keep explanations tied to the actual execution flow and source files.
- Do not silently add abstractions, dependencies, or functionality outside the
  requested scope.
- Implement only after the user asks for implementation; conceptual questions
  do not authorize code changes.

## Environment and commands

- Use Python 3.11 or newer. The current development environment uses Python
  3.11.9 in `.venv`.
- Use the `src/` package layout and import through `swarnim_agent`.
- Install the project and test dependencies with:

  ```bash
  .venv/bin/python -m pip install -e ".[test]"
  ```

- Run the CLI in a real terminal with:

  ```bash
  .venv/bin/python -m swarnim_agent
  ```

- Run tests with:

  ```bash
  .venv/bin/python -m pytest -q
  ```

## Current product scope

The current application is an interactive echo CLI:

- Accept text from a terminal input area.
- Submit on Enter and print the submitted text unchanged.
- Exit with `/exit` or Ctrl+C.

Do not add an LLM, agent loop, provider, queue, worker thread, tool system,
database, memory, configuration framework, or full-screen interface unless the
user explicitly expands the scope.

## Architecture decisions

Preserve these responsibility boundaries:

- `src/swarnim_agent/__main__.py` supports `python -m swarnim_agent` and
  delegates immediately to `main()`.
- `src/swarnim_agent/main.py` is a thin entry point and delegates to `run_cli()`.
- `src/swarnim_agent/cli/application.py` is the composition root. It constructs
  prompt-toolkit components, creates the controller, attaches key bindings, and
  starts the application.
- The input `TextArea` is single-line: use `multiline=False` for submit behavior
  and `height=1` to prevent the layout from occupying extra terminal rows.
- `src/swarnim_agent/cli/controller.py` owns prompt-toolkit callbacks and
  coordinates UI state. It explicitly reads the known `TextArea`, clears its
  buffer after submission, exits when requested, and delegates pure behavior.
- Use prompt-toolkit's `run_in_terminal()` when printing while the interactive
  application is active so output and prompt redraws are coordinated.
- `src/swarnim_agent/cli/keybindings.py` only maps keys to controller methods.
  `create_key_bindings()` accepts the controller directly so adding a binding
  does not expand a callback argument list. Do not put application behavior in
  the key-binding module.
- `src/swarnim_agent/cli/handlers.py` contains pure application behavior such as
  echoing input and recognizing `/exit`. Keep prompt-toolkit objects out of this
  module.

When adding a new keyboard action:

1. Put prompt-toolkit event handling and UI coordination on `CLIController`.
2. Register the controller method in `create_key_bindings()`.
3. Put reusable business behavior in a pure handler function when appropriate.
4. Add focused tests for both behavior and binding registration.

## Coding conventions

- Prefer small modules with one clear responsibility.
- Use type hints for public functions and callback parameters.
- Add concise docstrings that explain responsibility rather than restating the
  implementation.
- Prefer explicit dependencies and readable control flow over hidden global
  state.
- Avoid speculative abstractions for functionality that does not exist yet.
- Preserve unrelated user changes and inspect the working tree before editing.
- Never commit secrets, credentials, virtual environments, caches, or IDE state.

## Testing and terminal verification

- Add or update unit tests whenever callback behavior, handlers, or key
  registration changes.
- Keep pure behavior tests independent of a real terminal.
- Mock prompt-toolkit rendering boundaries in controller unit tests where
  appropriate.
- After changing interactive behavior, also verify the CLI in a real PTY; unit
  tests alone do not validate cursor movement or redraw behavior.
- PyCharm's Terminal panel and terminal-enabled Debug mode are valid interactive
  environments. Its Run output console may display prompt-toolkit redraws as
  blank lines or duplicate prompts even when the application works correctly.
  Do not add console-specific application behavior without explicit approval.

## Change handoff

After implementation, report:

- What behavior or responsibility changed.
- Which files own the new behavior.
- What tests and interactive checks were run.
- Any remaining limitation or environment-specific behavior.

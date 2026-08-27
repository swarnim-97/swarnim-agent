# Interactive CLI Input Flow

These notes collect the questions asked while building the prompt-toolkit
input, callback, and transcript flow in Swarnim Agent.

## Current implementation note

The terminal flow does not depend on what the pure handler returns. At the time
of writing, `echo_text()` in `cli/handlers.py` returns `len(text)`. Therefore,
submitting `hello` currently produces:

```text
> hello
5
>
```

If `echo_text()` returns the input unchanged, the same terminal flow produces:

```text
> hello
hello
>
```

## Execution overview

```text
User types in TextArea
        ↓
User presses Enter
        ↓
prompt-toolkit finds the Enter key binding
        ↓
CLIController.handle_submit(event) is invoked
        ↓
The submitted text is copied from TextArea
        ↓
The editable buffer is cleared
        ↓
/exit is handled, or run_in_terminal() is requested
        ↓
The submitted input and handler result are printed
        ↓
prompt-toolkit redraws a fresh empty prompt
```

## 1. What happens when Enter is pressed?

`create_key_bindings()` maps Enter to the controller method:

```python
bindings.add("enter")(controller.handle_submit)
```

`handle_submit` is the callback. It does not receive another callback.
Prompt-toolkit invokes it and supplies a `KeyPressEvent`:

```python
def handle_submit(self, event: KeyPressEvent) -> None:
    ...
```

Example:

```text
Enter key
    → KeyBindings
    → controller.handle_submit(event)
```

The event provides access to the active prompt-toolkit application through
`event.app`.

## 2. Is reading `input_area.text` the right approach?

Yes. The controller receives the known `TextArea` as an explicit dependency:

```python
controller = CLIController(input_area, prompt_text)
```

It can therefore read that specific component:

```python
submitted_text = self.input_area.text
```

Another valid approach is:

```python
submitted_text = event.current_buffer.text
```

The tradeoff is:

- `self.input_area.text` explicitly reads the component owned by this
  controller.
- `event.current_buffer.text` reads whichever buffer currently has focus.

With one input area, both refer to the same buffer. Explicitly reading the
known `TextArea` remains clear if the interface later contains other focusable
components.

## 3. What clears the submitted input?

The controller clears it explicitly:

```python
self.input_area.buffer.reset()
```

`run_in_terminal()` does not clear the buffer.

The submitted value remains available because it was copied first:

```python
submitted_text = self.input_area.text
self.input_area.buffer.reset()
```

After these lines:

```text
submitted_text contains "hello"
TextArea buffer contains ""
```

Python strings are immutable values, so clearing the TextArea does not change
the previously assigned `submitted_text` variable.

## 4. What does `run_in_terminal()` do?

Prompt-toolkit owns the active prompt line, cursor position, and screen redraw.
Printing normally while that interface is active can corrupt the prompt.

`run_in_terminal()` coordinates the operation:

```text
Temporarily hide or erase the interactive interface
        ↓
Run the supplied synchronous callable
        ↓
Allow its output to enter terminal scrollback
        ↓
Render the interactive prompt again
```

The controller uses it like this:

```python
run_in_terminal(lambda: self._render_transcript(submitted_text))
```

It does not open a new terminal, start another process, or clear the input
buffer.

## 5. Why was the original typed line not shown permanently?

While the user is typing, `> hello` is part of prompt-toolkit's temporary UI.
It is not yet normal terminal scrollback.

When Enter is pressed, the application clears the buffer and prompt-toolkit
erases the temporary editable line before printing output. If the application
prints only the handler result, the terminal retains only that result:

```text
5
>
```

To create transcript-style output, the application reconstructs and prints the
submitted prompt line as permanent output:

```text
> hello
5
>
```

## 6. How is transcript-style output created?

The application defines the prompt text once and gives the same value to the
`TextArea` and controller:

```python
prompt_text = "> "
input_area = TextArea(prompt=prompt_text, ...)
controller = CLIController(input_area, prompt_text)
```

The controller constructs one transcript string:

```python
transcript = (
    f"{self.prompt_text}{submitted_text}\n"
    f"{echo_text(submitted_text)}"
)
```

For `hello`, with the current length-returning handler, this becomes:

```text
> hello
5
```

The complete string is sent to one `print_formatted_text()` call. Using one
print operation prevents an unnecessary prompt redraw between the submitted
input line and its result.

## 7. Did `_render_transcript()` replace `print_formatted_text()`?

No. `_render_transcript()` is an internal method written for this project.
`print_formatted_text()` still performs the actual terminal output:

```text
run_in_terminal()
    → coordinates access to the active terminal

_render_transcript()
    → constructs the complete transcript

print_formatted_text()
    → writes that transcript
```

The leading underscore in `_render_transcript` indicates that it is an
internal controller helper rather than a public callback.

## 8. Why are callbacks placed on `CLIController`?

The project separates three responsibilities:

```text
application.py
    → constructs and connects components

keybindings.py
    → maps keys to controller callbacks

controller.py
    → handles prompt-toolkit events and coordinates UI state

handlers.py
    → contains pure application behavior
```

Keeping callbacks on the controller prevents `create_application()` from
growing into a mixture of component construction and event behavior.

It also makes callbacks easier to test without running a real terminal.

## 9. Why does `create_key_bindings()` accept the controller?

An earlier form accepted every callback separately:

```python
create_key_bindings(
    on_submit=controller.handle_submit,
    on_exit=controller.handle_exit,
)
```

That is explicit and works well for a small number of callbacks. However, its
argument list grows whenever a keyboard action is added.

The current form accepts the controller once:

```python
create_key_bindings(controller)
```

The key-binding module then performs only the mappings:

```python
bindings.add("enter")(controller.handle_submit)
bindings.add("c-c")(controller.handle_exit)
```

Tradeoff:

- Individual callback arguments make `keybindings.py` independent of the
  concrete controller.
- Passing the controller keeps construction compact but couples the key-binding
  module to the controller interface.

For this project, passing the controller was chosen because all terminal event
callbacks intentionally belong to `CLIController`.

## 10. Why did the prompt occupy many blank terminal rows?

`multiline=False` controls submission behavior: Enter submits instead of
inserting a newline. It does not by itself guarantee that the widget occupies
one visible row.

The input component therefore also uses:

```python
TextArea(
    prompt=prompt_text,
    multiline=False,
    height=1,
)
```

`height=1` prevents the root `TextArea` from stretching into unused terminal
rows.

PyCharm's Run output console may still display prompt-toolkit cursor redraws
as blank lines or duplicate prompts. The PyCharm Terminal panel and a
terminal-enabled Debug session provide behavior closer to a real PTY.

## Complete example

Suppose the user types `hello`:

```text
1. TextArea buffer becomes "hello".
2. Enter invokes CLIController.handle_submit(event).
3. submitted_text receives "hello".
4. buffer.reset() clears the editable TextArea.
5. should_exit("hello") returns False.
6. run_in_terminal() temporarily hides the prompt UI.
7. _render_transcript("hello") builds "> hello\n5".
8. print_formatted_text() writes both lines.
9. prompt-toolkit redraws a fresh "> " prompt.
```

Visible result with the current handler:

```text
> hello
5
>
```

## Related source files

- `src/swarnim_agent/cli/application.py`
- `src/swarnim_agent/cli/controller.py`
- `src/swarnim_agent/cli/keybindings.py`
- `src/swarnim_agent/cli/handlers.py`
- `tests/test_controller.py`
- `tests/test_keybindings.py`

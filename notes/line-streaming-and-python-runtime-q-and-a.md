# Line Streaming and Python Runtime Q&A

This note records questions about the current line-streaming implementation,
prompt-toolkit's application lifecycle, Python standard streams and context
managers, and generator iteration.

The examples correspond to the current code in:

```text
src/swarnim_agent/cli/application.py
src/swarnim_agent/cli/controller.py
src/swarnim_agent/cli/handlers.py
src/swarnim_agent/processing/worker.py
```

## 1. Why was line-based streaming chosen after the initial background-worker milestone?

The first worker contract produced one complete string:

```python
Callable[[str], str]
```

That established the queue, worker thread, result callback, error callback,
and shutdown lifecycle. The next narrow step was allowing one input to produce
more than one complete output line:

```python
Callable[[str], Iterable[str]]
```

The flow changed from:

```text
input → worker → one result
```

to:

```text
input → worker → line 1 → line 2 → stream ends
```

Complete lines were chosen before token-by-token output because each call to
`print_formatted_text()` can finish with a newline and prompt-toolkit can safely
redraw the prompt. This teaches incremental results without yet adding
same-line cursor management, an output queue, an LLM, or artificial delays.

## 2. How does `render_line()` print the value stored in its `line` parameter?

The controller method is:

```python
def render_line(self, line: str) -> None:
    print_formatted_text(line)
```

When the worker calls:

```python
self._on_line("5")
```

`self._on_line` refers to `controller.render_line`, so the call is effectively:

```python
controller.render_line("5")
```

Inside the method, the parameter has this value:

```python
line == "5"
```

The print call is therefore equivalent to:

```python
print_formatted_text("5")
```

`print_formatted_text()` converts the value into formatted-text fragments,
adds a newline by default, writes those fragments to the terminal output, and
returns `None`.

## 3. How do `print_formatted_text(line)` and `patch_stdout()` work together to print a worker result above the active prompt?

They solve related problems, but the installed prompt-toolkit implementation
does not require `patch_stdout()` in order for `print_formatted_text()` itself
to print safely.

When an `Application` is active, `print_formatted_text()` finds its event loop,
schedules `run_in_terminal()`, prints above the application, and lets the
application redraw. This also works when `render_line()` is called from the
worker thread because scheduling is thread-safe.

`patch_stdout()` has a broader responsibility. It temporarily redirects
ordinary writes to `sys.stdout` and `sys.stderr`, including code such as:

```python
print("ordinary output")
sys.stderr.write("diagnostic output\n")
```

Its proxy arranges for those writes to appear above the active prompt instead
of corrupting it.

In the current application:

```text
print_formatted_text(line)
    → has its own active-application coordination

ordinary print()/stdout/stderr output
    → is protected by patch_stdout()
```

Keeping `patch_stdout()` around the whole interactive run protects output from
other code that may use normal Python printing, even though `render_line()`
uses prompt-toolkit's own printing helper.

## 4. Why is the existing prompt erased and redrawn below the newly printed line?

The active prompt is temporary UI managed by prompt-toolkit. It is not a fixed
line that can safely be left in place while unrelated text is written at the
cursor.

If the terminal currently shows:

```text
> 
```

and the worker publishes `"5"`, prompt-toolkit coordinates this sequence:

```text
temporarily erase or hide the prompt
        ↓
print "5" followed by a newline
        ↓
redraw the prompt at the new cursor position
```

The final display becomes:

```text
5
> 
```

The old prompt was not physically pushed down. It was removed from the
temporary rendering area and drawn again after the permanent output.

## 5. What are `sys.stdout` and `sys.stderr`?

Python processes normally have three standard streams:

```text
sys.stdin   → standard input
sys.stdout  → normal output
sys.stderr  → error and diagnostic output
```

`print()` writes to `sys.stdout` by default:

```python
print("Application started")
```

This is similar to:

```python
sys.stdout.write("Application started\n")
```

An error message can be written separately:

```python
print("Processing failed", file=sys.stderr)
```

The objects are file-like streams. They provide methods such as `write()` and
`flush()`, but the destination does not have to be a physical file. It is
usually the terminal unless something redirects it.

## 6. How does `patch_stdout()` temporarily replace and later restore `sys.stdout` and `sys.stderr`?

On entry, `patch_stdout()` saves the original stream objects and installs a
prompt-toolkit `StdoutProxy`:

```text
before
sys.stdout → original output
sys.stderr → original error output

inside the context
sys.stdout → StdoutProxy
sys.stderr → the same StdoutProxy
```

The proxy collects output and coordinates it with the running application's
event loop. When the context ends, the saved objects are restored:

```text
after
sys.stdout → original output
sys.stderr → original error output
```

The restoration happens in a `finally` block inside `patch_stdout()`, so it
also happens if the application raises an exception.

## 7. What is a context-manager object?

A context manager is an object that defines setup and cleanup around a block
of code. It follows this lifecycle:

```text
enter context
    → perform setup

run indented block

exit context
    → perform cleanup
```

Common context managers include open files, locks, database transactions, and
temporary output redirection.

For example, the object returned by `open()` manages an open file:

```python
with open("message.txt") as file:
    content = file.read()
```

The file is closed automatically after the indented block ends.

## 8. What do the `__enter__()` and `__exit__()` methods do?

Class-based context managers implement two special methods:

```python
class Door:
    def __enter__(self):
        print("Opening")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        print("Closing")
```

`__enter__()` runs before the block and may return a value for an `as`
variable. `__exit__()` runs when the block finishes and receives information
about any exception raised inside it.

Using the class:

```python
with Door() as door:
    print("Walking through")
```

produces:

```text
Opening
Walking through
Closing
```

`patch_stdout()` is implemented with Python's `@contextmanager` helper rather
than a handwritten class, but Python still returns an object that provides the
same context-manager protocol.

## 9. How does Python's `with` statement work?

The statement:

```python
with Door() as door:
    use(door)
```

is roughly equivalent to:

```python
manager = Door()
door = manager.__enter__()

try:
    use(door)
finally:
    manager.__exit__(None, None, None)
```

The actual language behavior also passes exception details to `__exit__()`.
The important property is guaranteed cleanup when control leaves the block,
whether it leaves normally or because an exception was raised.

Only the indented code is inside the context:

```python
with patch_stdout():
    run_interactive_code()  # stdout is patched here

print("finished")           # original stdout is restored here
```

## 10. Why must `runtime.application.run()` remain inside the `with patch_stdout():` block?

`runtime.application.run()` blocks for the lifetime of the interactive
session. While it is active, key handlers run and the worker may write output.

Putting it inside the block keeps standard output patched for that entire
period:

```text
enter patch_stdout
        ↓
start application.run()
        ↓
handle input and worker output
        ↓
application exits
        ↓
application.run() returns
        ↓
leave patch_stdout and restore streams
```

If `application.run()` were placed after the block, stdout would already be
restored before the interactive application started:

```python
with patch_stdout():
    pass

runtime.application.run()  # no longer protected by that context
```

## 11. What does the prompt-toolkit `Application` object represent?

The object represents one configured interactive terminal UI. It knows how to
coordinate:

- the layout and input area;
- keyboard input and key bindings;
- the active buffer and cursor;
- rendering and redraws;
- terminal input/output state;
- the application event loop;
- application exit.

The current construction is:

```python
Application(
    layout=Layout(input_area),
    key_bindings=create_key_bindings(controller),
    full_screen=False,
)
```

This tells prompt-toolkit what to display, how to respond to registered keys,
and to use the normal terminal rather than a full-screen interface.

It does not own the background-processing algorithm. The `BackgroundWorker`
and pure processor remain separate objects.

## 12. What does `runtime.application.run()` do?

`run()` starts the configured interactive application and does not return
until the application exits.

Conceptually it:

```text
prepares terminal input mode
        ↓
renders the layout
        ↓
waits for keyboard or scheduled events
        ↓
updates buffers or invokes key bindings
        ↓
redraws when necessary
        ↓
repeats until app.exit() is requested
        ↓
restores terminal state and returns
```

For example, Enter matches the registered submit binding, which calls
`controller.handle_submit(event)`. Calling `event.app.exit()` for `/exit` or
Ctrl+C tells the running loop to finish, allowing `run()` to return.

## 13. What is an event loop, and does `application.run()` continuously consume CPU?

An event loop repeatedly waits for events and dispatches work when an event is
available:

```text
wait for event
    → key press arrives
    → process key press
    → redraw if needed
    → wait again
```

It is conceptually loop-shaped, but it is not normally a busy loop that checks
the keyboard as fast as the CPU allows. While there is nothing to do, the
underlying event system waits efficiently for input or scheduled callbacks.

`application.run()` blocks the main thread because that thread remains inside
the event loop until exit. Blocking here means the next statement in
`run_cli()` cannot execute yet; it does not mean the CPU is constantly busy.

## 14. How do the prompt-toolkit main thread and background-worker thread operate at the same time?

The main thread runs prompt-toolkit:

```text
Main thread
    → application event loop
    → keyboard input
    → controller callbacks
    → terminal redraws
```

The worker has its own thread:

```text
Worker thread
    → input_queue.get()
    → processor iteration
    → on_line callback
    → input_queue.task_done()
```

Submitting input connects them through a thread-safe queue:

```text
main thread: input_queue.put("hello")
        ↓
worker thread: input_queue.get()
```

When the worker calls `render_line()`, `print_formatted_text()` schedules the
terminal operation on the running application's loop. This avoids requiring
the worker to take direct ownership of prompt-toolkit's rendering lifecycle.

## 15. What does `text_length_lines(text: str) -> Iterator[str]` mean?

The signature is:

```python
def text_length_lines(text: str) -> Iterator[str]:
```

It declares:

```text
text: str
    → accept one string

Iterator[str]
    → return an iterator that produces strings
```

The current body is:

```python
yield "Calculating character count..."
yield text_length(text)
```

For `"hello"`, the iterator produces:

```text
Calculating character count...
5
```

It does not return both strings as one combined value.

## 16. What is a generator function?

Any function containing `yield` is a generator function. Calling it creates a
generator object instead of executing the whole body immediately:

```python
lines = text_length_lines("hello")
```

At this point, `lines` is ready to produce values, but execution has not yet
reached the first `yield`. A generator is also an iterator, so values can be
requested with `next()` or consumed with a `for` loop.

Each call creates a separate, single-use generator with its own paused
execution state.

## 17. What does `yield` do, and how does it pause and resume a generator?

`yield` sends one value to the caller and saves the generator's current
execution position.

```python
def steps() -> Iterator[str]:
    yield "first"
    yield "second"
```

The sequence is:

```text
next(generator)
    → run until yield "first"
    → return "first"
    → pause after that yield

next(generator)
    → resume after the first yield
    → run until yield "second"
    → return "second"
    → pause again
```

This differs from `return`, which sends a final value and ends the function.
After a generator executes `return` or reaches the end of its body, it cannot
yield another value.

## 18. What is an iterator?

An iterator is an object that produces one value at a time and remembers its
current position.

```python
iterator = iter(["first", "second"])

next(iterator)  # "first"
next(iterator)  # "second"
```

The iterator has now consumed both values. Asking again signals that it has
finished:

```python
next(iterator)  # raises StopIteration
```

Iterators are stateful and normally single-use. To iterate over a reusable
collection again, obtain a new iterator from that collection.

## 19. What is the difference between an iterable and an iterator?

An iterable is an object from which an iterator can be obtained:

```python
values = ["first", "second"]  # iterable
iterator = iter(values)        # iterator
```

An iterator is the active object that supports `next()` and keeps its current
position.

```text
Iterable
    → can create an iterator with iter()

Iterator
    → returns the next value with next()
    → remembers progress
    → raises StopIteration when finished
```

Every iterator is also iterable because `iter(iterator)` returns the iterator
itself. Not every iterable is an iterator: a list can be used in a `for` loop,
but `next(a_list)` is invalid.

## 20. What does `Iterator[str]` mean as a type hint?

```python
Iterator[str]
```

means an iterator whose yielded values are expected to be strings.

For example:

```python
def words() -> Iterator[str]:
    yield "hello"
    yield "world"
```

The annotation documents the contract for developers, PyCharm, and static
type checkers. It does not make Python automatically check every value at
runtime. That is why the worker also performs an explicit `isinstance()` check
before publishing a yielded line.

## 21. What does `iterator: Iterator[str] = iter(lines)` mean?

The statement combines a variable annotation and an assignment:

```python
iterator: Iterator[str] = iter(lines)
```

Breaking it down:

```text
iterator
    → variable name

Iterator[str]
    → expected variable type

iter(lines)
    → obtain an iterator from lines
```

The annotation does not perform the conversion. `iter(lines)` performs it.
The resulting iterator is stored in `iterator`, ready for `next(iterator)`.

## 22. Why does the worker call `iter(lines)` instead of calling `next(lines)` directly?

The processor is allowed to return any `Iterable[str]`, including a list,
tuple, or generator:

```python
["starting", "5"]
("starting", "5")
text_length_lines("hello")
```

A list is iterable but is not itself an iterator:

```python
next(["starting", "5"])  # TypeError
```

Converting first gives the worker one consistent interface:

```python
iterator = iter(lines)
line = next(iterator)
```

If `lines` is already a generator iterator, `iter(lines)` normally returns the
same object rather than creating a second stream.

## 23. What do `next(iterator)` and `StopIteration` mean?

`next(iterator)` requests the iterator's next value:

```python
line = next(iterator)
```

An iterator communicates normal completion by raising `StopIteration`. The
worker handles that separately from processing failures:

```python
try:
    line = next(iterator)
except StopIteration:
    return
```

Here, `return` ends `_publish_lines()` because there are no more output lines.
`StopIteration` is not rendered as an error; it is the standard iterator
completion signal used internally by Python `for` loops as well.

## 24. Why does the worker reject a plain string as a line stream?

A Python string is itself iterable:

```python
list("hello")
# ["h", "e", "l", "l", "o"]
```

If a processor accidentally returned:

```python
return "hello"
```

the worker could otherwise interpret it as five streamed lines, one character
at a time. The explicit check catches this common contract mistake:

```python
if isinstance(lines, str):
    raise TypeError(
        "Background processor must return an iterable of lines, not a string"
    )
```

A valid processor must wrap complete lines in another iterable or yield them:

```python
return ("hello",)
```

or:

```python
yield "hello"
```

## 25. Why does the worker validate every yielded value as a string?

Type hints do not enforce values at runtime. A processor could be annotated as
returning strings but accidentally produce an integer:

```python
def invalid_lines(text: str) -> Iterator[str]:
    yield "starting"
    yield 5  # incorrect runtime value
```

The worker validates each value before calling the controller:

```python
if not isinstance(line, str):
    self._on_error(
        TypeError("Background processor must yield only text lines")
    )
    return
```

This keeps the rendering boundary predictable: `render_line()` always
receives a string. Lines yielded before an invalid value remain published, the
error callback reports the failure, and iteration for that input stops. The
worker then calls `task_done()` in its outer `finally` block and can continue
with the next queued input.

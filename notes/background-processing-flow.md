# Background Processing Flow

These notes describe the first background-processing milestone. The project
still has no agent, LLM, provider, streaming response, tool system, database,
or conversation memory.

## Why this milestone exists

Prompt-toolkit runs an interactive event loop that owns keyboard input, cursor
movement, the input buffer, and terminal redraws. Long processing inside an
Enter callback would block that event loop and make the interface appear
frozen.

The project now separates those responsibilities:

```text
UI thread
    → reads and clears TextArea
    → prints the permanent submitted-input line
    → puts text into a synchronized queue
    → returns to prompt-toolkit

Worker thread
    → waits for queued text
    → calls the pure text processor
    → publishes the result or error
```

## Current observable behavior

The pure processor returns the number of submitted characters as text:

```python
def text_length(text: str) -> str:
    return str(len(text))
```

Example:

```text
> hello
5
>
```

The different input and output make the processing boundary visible without
requiring an LLM.

## Source ownership

```text
cli/application.py
    → creates and connects UI, queue, controller, and worker
    → starts and stops the worker

cli/controller.py
    → owns prompt-toolkit callbacks
    → records submitted input and enqueues it
    → renders worker results and errors

cli/handlers.py
    → contains the pure text_length() operation

processing/worker.py
    → owns the worker thread and processing loop
    → consumes the synchronized queue
    → reports results and errors

cli/keybindings.py
    → maps Enter and Ctrl+C to controller callbacks
```

## Complete submission flow

Suppose the user enters `hello`:

```text
1. TextArea contains "hello".
2. Enter invokes CLIController.handle_submit(event).
3. The controller copies "hello" into submitted_text.
4. buffer.reset() clears the editable input.
5. should_exit("hello") returns False.
6. run_in_terminal() temporarily hides the active prompt.
7. The controller prints the permanent line "> hello".
8. The controller puts "hello" into the input queue.
9. The prompt-toolkit event callback finishes.
10. The worker's blocking queue.get() receives "hello".
11. The worker calls text_length("hello").
12. text_length() returns "5".
13. The worker calls controller.render_result("5").
14. patch_stdout schedules the output safely above the active prompt.
15. The prompt is redrawn for the next input.
```

## Why `queue.Queue` is used

`queue.Queue` is synchronized for communication between threads. `put()` and
`get()` coordinate access using internal locks and condition variables.

```text
UI thread calls put("hello")
        ↓
Queue stores the item and notifies a waiting consumer
        ↓
Worker wakes from get()
        ↓
Worker removes "hello"
```

One worker consumes one item at a time, so submissions retain FIFO order.

The worker calls `task_done()` for every item, including its private shutdown
signal, so queue accounting remains balanced.

## Why processing is injected

The worker receives a function with this contract:

```python
Callable[[str], str]
```

It does not import or know about `text_length()` specifically. The composition
root connects them:

```text
BackgroundWorker(process=text_length)
```

This means a later deterministic processor or agent interface can replace
`text_length()` without rewriting queue and thread management.

## Why the controller prints the input before enqueuing

The original editable input line is temporary prompt-toolkit UI. The
controller permanently prints the submitted line before calling `put()`:

```text
print "> hello"
        ↓
enqueue "hello"
```

Doing both inside the same `run_in_terminal()` callable guarantees that the
submitted line is recorded before a fast worker can publish its result.

## How worker output reaches the terminal

Normal printing from a worker thread could conflict with prompt-toolkit's
active prompt. `run_cli()` therefore runs the application inside
`patch_stdout()`.

The stdout proxy:

```text
receives a complete line from the worker
        ↓
finds the running prompt-toolkit application loop
        ↓
schedules run_in_terminal() on that loop
        ↓
writes the result above the prompt
        ↓
allows prompt-toolkit to redraw
```

This is the first-stage output handoff. A future streaming milestone may use an
explicit result queue, but adding threads, result polling, and asyncio together
would obscure the concepts being learned here.

## Error behavior

The worker catches exceptions raised by the pure processor:

```text
processor succeeds
    → on_result(result)

processor raises
    → on_error(exception)
```

After reporting a processing error, the loop waits for the next item instead
of silently terminating the worker thread.

The controller currently renders errors as:

```text
Error: processing failed
```

## Worker lifecycle

The worker is managed rather than abandoned as a daemon:

```text
run_cli()
    → start worker
    → run prompt-toolkit application
    → application exits
    → finally: stop worker
```

`stop()` puts a unique private object into the queue. It does not use a string
such as `"STOP"`, because a user might legitimately submit that text.

```text
worker receives normal string
    → process it

worker receives private stop object
    → leave loop
    → thread finishes
```

The main thread joins the worker so process shutdown is explicit.

## Current limitations

- There is one worker and no parallel processing.
- Shutdown waits for previously queued work before reaching the FIFO stop
  signal.
- There is no cancellation for an item already being processed.
- Results are complete strings rather than streaming chunks.
- Output uses prompt-toolkit's stdout proxy rather than a dedicated result
  queue.
- There is no job identifier because one FIFO worker preserves result order.

These are intentional boundaries for this milestone, not hidden agent
features.

## Related files

- `src/swarnim_agent/cli/application.py`
- `src/swarnim_agent/cli/controller.py`
- `src/swarnim_agent/cli/handlers.py`
- `src/swarnim_agent/cli/keybindings.py`
- `src/swarnim_agent/processing/worker.py`
- `tests/test_controller.py`
- `tests/test_handlers.py`
- `tests/test_worker.py`

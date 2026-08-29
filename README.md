# Swarnim Agent

This learning-oriented CLI accepts terminal input and processes it on a managed
background thread. Its current deterministic processor streams complete output
lines ending with the submitted text's character count, allowing the input and
output paths to remain visibly different before an agent or LLM is introduced.

## Setup

```bash
python -m pip install -e ".[test]"
```

## Run

```bash
swarnim-agent
```

You can also run the package directly:

```bash
python -m swarnim_agent
```

Press `Enter` to submit text. Type `/exit` or press `Ctrl+C` to close the CLI.

Example:

```text
> hello
Calculating character count...
5
>
```

The prompt-toolkit UI thread records and enqueues input. A background worker
consumes queued text in FIFO order and prints each processed line safely above
the active prompt.

# Swarnim Agent

This learning-oriented CLI accepts terminal input and sends it to an
OpenAI-compatible model on a managed background thread. Its architecture is
split into configuration, runtime resolution, request/response transport,
network execution, and agent orchestration so each responsibility can be
learned independently.

## Setup

```bash
python -m pip install -e ".[test]"
```

## Configure the provider

The repository contains non-secret provider settings in `config.yaml`. The
current development configuration uses a local OpenAI-compatible endpoint:

```yaml
model:
  provider: ollama
  name: qwen3.5:cloud
  max_tokens: 1024

providers:
  ollama:
    api_mode: chat_completions
    base_url: http://127.0.0.1:11434/v1
    api_key_env: OLLAMA_API_KEY
```

Copy the safe secret template into the project root if `.env` does not exist:

```bash
cp .env.example .env
```

The local endpoint requires no real API key, but the OpenAI SDK and current
runtime require a non-empty placeholder:

```dotenv
OLLAMA_API_KEY=ollama
```

Non-secret model and provider settings belong in `config.yaml`. Credentials
belong in the ignored project-root `.env` or the process environment and must
not be committed.

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
> Explain Python generators briefly.
Waiting for model response...
A generator produces values lazily and pauses at each yield.
>
```

The prompt-toolkit UI thread records and enqueues input. A background worker
consumes queued text in FIFO order and calls the LLM agent. The transport builds
and normalizes streaming Chat Completions chunks, while a separate executor owns
the actual OpenAI-compatible network call. A pure line buffer combines partial
text deltas and renders output only when a complete line is available, flushing
the final unterminated line when the stream finishes successfully.

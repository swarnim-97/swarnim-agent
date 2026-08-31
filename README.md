# Swarnim Agent

This learning-oriented CLI accepts terminal input and sends it to an NVIDIA
hosted model on a managed background thread. Its provider architecture is split
into configuration, runtime resolution, request/response transport, network
execution, and agent orchestration so each responsibility can be learned
independently.

## Setup

```bash
python -m pip install -e ".[test]"
```

## Configure NVIDIA

The repository contains the non-secret provider settings in `config.yaml`.
Choose the NVIDIA model there:

```yaml
model:
  provider: nvidia
  name: deepseek-ai/deepseek-v4-pro-0813
  max_tokens: 1024
```

Copy the safe secret template into the project root if `.env` does not exist:

```bash
cp .env.example .env
```

Then replace its placeholder:

```dotenv
NVIDIA_API_KEY=your-key
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
and normalizes Chat Completions data, while a separate executor owns the actual
OpenAI-compatible network call. The first NVIDIA milestone waits for a complete
response and then renders it as complete lines; token streaming is intentionally
postponed.

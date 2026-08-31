# Provider Architecture and Execution Q&A

This note records questions about agent boundaries, the provider architecture
studied in Hermes Agent, configuration and secrets, transport normalization,
network execution, and the current model-call flow.

Relevant project areas:

```text
src/swarnim_agent/agents/
src/swarnim_agent/configuration/
src/swarnim_agent/execution/
src/swarnim_agent/providers/
src/swarnim_agent/transports/
src/swarnim_agent/cli/application.py
src/swarnim_agent/processing/worker.py
```

## 1. What is a deterministic agent interface, and what responsibility does it own?

The first agent boundary used a deterministic implementation so the
architecture could be learned without a remote model. Its shared contract was:

```python
class Agent(Protocol):
    def run(self, text: str) -> Iterable[str]:
        ...
```

An agent receives submitted text, coordinates its processing and produces
complete output lines. It does not own terminal rendering or worker-thread
lifecycle.

A deterministic implementation always produces predictable output:

```python
def run(self, text: str) -> Iterator[str]:
    yield "Calculating character count..."
    yield str(len(text))
```

The current `LLMAgent` satisfies the same interface but coordinates a
transport and executor instead of calculating the result itself.

## 2. How does Hermes separate provider configuration, runtime resolution, client construction, transport conversion and agent orchestration?

Hermes treats them as separate responsibilities:

```text
Provider profile
    → provider metadata and request quirks

Runtime resolver
    → provider, credential, endpoint and API mode

Client router
    → SDK client or compatibility adapter

Provider transport
    → request conversion and response normalization

AIAgent
    → conversation orchestration, streaming, retries and tools
```

This prevents the agent loop from containing every provider's URL,
credential rules and data formats.

## 3. Does Hermes use one simple `ModelProvider` interface?

No. An interface such as this would combine too many responsibilities:

```python
class ModelProvider(Protocol):
    def stream(self, prompt: str) -> Iterable[str]:
        ...
```

Hermes instead uses cooperating boundaries. `ProviderTransport` owns data
conversion, while other modules own profiles, credentials, client construction
and execution.

## 4. What is Hermes's `ProviderTransport` abstraction?

It is an abstract base class that converts between Hermes's internal data and
a provider protocol:

```text
internal messages and tools
        ↓
ProviderTransport
        ↓
provider-ready request

raw provider response
        ↓
ProviderTransport
        ↓
normalized response
```

Transports are selected by API mode rather than always by vendor name.

## 5. What methods does Hermes's `ProviderTransport` define?

Its required surface is approximately:

```python
class ProviderTransport(ABC):
    @property
    @abstractmethod
    def api_mode(self) -> str: ...

    @abstractmethod
    def convert_messages(self, messages, **kwargs): ...

    @abstractmethod
    def convert_tools(self, tools): ...

    @abstractmethod
    def build_kwargs(self, model, messages, tools=None, **params): ...

    @abstractmethod
    def normalize_response(self, response, **kwargs): ...
```

Our reduced interface currently needs only `api_mode`, `build_request()` and
`normalize_response()`.

## 6. Why does the Hermes transport not own client construction, streaming, credentials, retries or interrupts?

Those behaviours change for reasons unrelated to data format:

- credentials may come from API keys, OAuth or pools;
- clients may be rebuilt after credential refresh;
- retries belong to the complete operation;
- interrupts belong to the agent turn;
- streaming coordinates callbacks and connection health.

Our project applies the same separation:

```text
ChatCompletionsTransport → request and response format
OpenAIChatExecutor       → SDK client and network call
LLMAgent                 → orchestration
BackgroundWorker         → thread lifecycle
```

## 7. What is the difference between a provider identity and an API mode?

A provider identity names who serves the model:

```text
provider = provider-name
```

An API mode names the wire protocol:

```text
api_mode = chat_completions
```

Several providers can expose the same API mode, so `ProviderRuntime` stores
both values.

## 8. Why can multiple providers reuse the same Chat Completions transport?

They can share it when they accept the same request and response shapes.

```json
{
  "model": "model-id",
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 1024,
  "stream": false
}
```

The provider-specific URL, key and model name are injected separately through
the runtime and executor, so the protocol conversion does not need to be
duplicated.

## 9. What is a normalized provider response, and why is it useful?

A normalized response exposes fields the rest of the application can rely on:

```python
@dataclass(frozen=True)
class NormalizedResponse:
    content: str
    finish_reason: str
    usage: Usage | None = None
```

Only the transport reads SDK-specific paths. The agent reads
`response.content` regardless of the raw SDK object's structure.

## 10. Which Hermes architectural responsibilities should our smaller project follow?

We preserve these boundaries:

- configuration loading is separate from execution;
- secrets are separate from non-secret settings;
- runtime resolution combines them once;
- transports own protocol conversion;
- executors own network calls;
- agents coordinate dependencies;
- workers own queues and threads;
- controllers own terminal integration;
- `application.py` composes everything.

## 11. Which Hermes implementation details should our project deliberately avoid copying?

We currently do not need:

- plugin discovery or a transport registry;
- multiple API modes;
- OAuth and credential pools;
- fallback chains and provider-specific retries;
- tool-call normalization;
- prompt-cache management;
- a large agent class with many provider branches.

Hermes needs these because of its scale. Adding them now would hide the core
learning flow.

## 12. Does Hermes store provider credentials directly in `config.yaml`?

Normally, no. Its intended separation is:

```text
config.yaml → provider, model, endpoint and behavioural settings
.env/auth   → API keys and tokens
```

Some specialized or legacy paths may accept key-like values, but credentials
are not intended to be ordinary shareable configuration.

## 13. What belongs in `config.yaml`, and what belongs in `.env`?

Non-secret settings belong in `config.yaml`:

```yaml
model:
  provider: provider-name
  name: model-name
  max_tokens: 1024

providers:
  provider-name:
    api_mode: chat_completions
    base_url: https://example.com/v1
    api_key_env: PROVIDER_API_KEY
```

The actual secret belongs in `.env`:

```dotenv
PROVIDER_API_KEY=secret-value
```

The YAML stores only the credential variable's name.

## 14. What happens when Hermes starts and combines provider configuration with credentials?

Its simplified startup flow is:

```text
load secret sources
    → load config.yaml
    → read selected provider and model
    → resolve credentials, endpoint and API mode
    → construct client
    → construct AIAgent
```

The saved sources allow a new terminal session to reconstruct the runtime
without asking the user to enter every setting again.

## 15. Why does our project load configuration and secrets into explicit objects instead of relying on global environment state?

Direct environment reads hide dependencies:

```python
api_key = os.environ["PROVIDER_API_KEY"]
```

Our flow makes them explicit:

```python
settings = load_settings()
secrets = load_secrets(secret_names)
runtime = resolve_provider_runtime(settings, secrets)
```

Environment values can override `.env`, but the loader copies only declared
credential names rather than passing the entire process environment around.

## 16. What does `ProviderRuntime` represent?

It is the fully resolved in-memory dependency needed for execution:

```python
ProviderRuntime(
    provider="provider-name",
    model="model-name",
    api_mode="chat_completions",
    base_url="https://example.com/v1",
    api_key="resolved-secret",
    max_tokens=1024,
)
```

It is created after validation and secret resolution. It does not read files
or perform a network call.

## 17. Why is the API key excluded from `ProviderRuntime.__repr__()`?

Dataclasses normally display every field in their representation. Without
protection, debugging could expose:

```text
ProviderRuntime(..., api_key='secret-value', ...)
```

The field therefore uses:

```python
api_key: str = field(repr=False)
```

The object still contains the key, but ordinary `repr()` output omits it. This
reduces accidental disclosure; it is not encryption.

## 18. Why did we move `config.yaml` and `.env` into the project directory?

During the learning phase, keeping them beside the source makes the active
configuration easy to find:

```text
swarnim-agent/
├── config.yaml
├── .env
├── pyproject.toml
└── src/
```

`config.yaml` is non-secret and trackable. `.env` is ignored by Git. A packaged
application may later move user settings to an operating-system-appropriate
directory because installed packages should not normally write into their
source directory.

## 19. How does the loader find the project root without depending on `Path.cwd()`?

It derives the root from the loader's own source path:

```python
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

For the current layout:

```text
project root/src/swarnim_agent/configuration/loader.py
```

three parents above the package source reaches the project root. This avoids
failures when PyCharm or a shell starts with another working directory. The
tradeoff is that this default depends on the current `src/` layout.

## 20. What does `max_tokens: 1024` mean?

It sets the maximum number of output tokens the model may generate for one
response:

```yaml
max_tokens: 1024
```

The transport sends:

```python
"max_tokens": 1024
```

It is a ceiling, not an exact requested length. A response may finish after 50
tokens. A token is a model-specific text unit, not exactly one word or
character. As a rough English estimate, 1,024 tokens can correspond to about
700-800 words, but tokenization varies.

## 21. What is the difference between input tokens, output tokens and the model context window?

Input tokens represent content sent to the model. Output tokens are generated
by the model:

```text
input tokens:   100
output tokens:  300
total tokens:   400
```

`max_tokens` limits generated output. The context window limits how much total
context the model can handle, generally including the input and room for
output:

```text
input context + generated output ≤ context-window limit
```

Reasoning-token accounting can vary by model and provider.

## 22. What responsibility does `ChatCompletionsTransport` own?

It owns the OpenAI-compatible Chat Completions data format.

Request direction:

```text
ChatMessage objects
    → role/content dictionaries
    → ProviderRequest parameters
```

Response direction:

```text
raw SDK response
    → content, finish reason and optional usage
    → NormalizedResponse
```

It does not know the API key, create the SDK client, make a network call, own a
thread or print to the terminal.

## 23. What responsibility does `OpenAIChatExecutor` own?

It owns the configured SDK client and one network-call operation:

```python
OpenAI(base_url=base_url, api_key=api_key)
```

Its executor method returns the raw response:

```python
def execute(self, request: ProviderRequest) -> object:
    return self._client.chat.completions.create(
        **dict(request.parameters)
    )
```

It does not decide which messages to send or interpret the response content.

## 24. Why are request construction and network execution separate?

They can be tested and changed independently.

Transport test:

```python
request = transport.build_request(...)
assert request.parameters["model"] == "model-id"
```

Executor test:

```python
executor.execute(request)
client.chat.completions.create.assert_called_once()
```

Combining them would couple message conversion to SDK construction and network
mocking.

## 25. What responsibility does `LLMAgent` own?

It coordinates one model operation:

```text
submitted text
    → create ChatMessage
    → transport.build_request()
    → executor.execute()
    → transport.normalize_response()
    → yield complete lines
```

The constructor receives its dependencies explicitly:

```python
LLMAgent(
    model=runtime.model,
    max_tokens=runtime.max_tokens,
    transport=transport,
    executor=executor,
)
```

This allows tests to inject a fake executor without a network call.

## 26. How does the complete configuration-to-terminal execution flow work?

```text
config.yaml → load_settings()
.env/process environment → load_secrets()
        ↓
resolve_provider_runtime()
        ↓
construct transport, executor and LLMAgent
        ↓
user presses Enter
        ↓
CLIController enqueues text
        ↓
BackgroundWorker calls LLMAgent.run()
        ↓
transport builds request
        ↓
executor performs network call
        ↓
transport normalizes response
        ↓
controller renders output lines
```

Each boundary owns one part of the operation instead of placing everything in
the entry point or controller.

## 27. What does `self._client.chat.completions.create(**dict(request.parameters))` do?

It performs the actual Chat Completions request through the configured SDK
client.

If the parameters are:

```python
{
    "model": "model-id",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 1024,
    "stream": False,
}
```

the call is equivalent to:

```python
self._client.chat.completions.create(
    model="model-id",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1024,
    stream=False,
)
```

It waits for a complete response because streaming is false, then returns the
raw SDK object.

## 28. What do `.chat`, `.completions` and `.create()` represent?

They form an SDK resource hierarchy:

```text
self._client  → configured API client
.chat         → chat resource group
.completions  → Chat Completions resource
.create()     → create one completion request
```

Conceptually, the final call sends:

```text
POST <base_url>/chat/completions
```

The SDK handles headers, JSON serialization, HTTP execution and conversion of
the JSON response into Python objects.

## 29. Why is `request.parameters` converted using `dict()`?

`ProviderRequest.parameters` is typed as:

```python
Mapping[str, object]
```

A mapping is dictionary-like but is not necessarily a concrete `dict`.
Calling:

```python
dict(request.parameters)
```

creates a regular dictionary for keyword unpacking. If the mapping is already
a dictionary, this creates a shallow copy.

## 30. What does `**` keyword-argument unpacking mean?

Given:

```python
parameters = {
    "model": "model-id",
    "stream": False,
}
```

this:

```python
create(**parameters)
```

is equivalent to:

```python
create(model="model-id", stream=False)
```

Dictionary keys become keyword names and values become their arguments. The
keys must therefore be strings accepted by the called function.

## 31. On which thread does the model network request execute?

It runs on the managed background-worker thread:

```text
Main thread
    → prompt-toolkit event loop and terminal interaction

Worker thread
    → queued text
    → LLMAgent.run()
    → executor.execute()
    → wait for network response
```

The blocking request does not run on prompt-toolkit's main thread, so the
terminal event loop can continue processing input. There is one worker, so
model requests are processed in FIFO order rather than in parallel.

## 32. How do executor errors reach the terminal without terminating the worker?

```text
executor.execute() raises
        ↓
exception leaves LLMAgent iterator
        ↓
BackgroundWorker._publish_lines() catches processor failure
        ↓
on_error(exception)
        ↓
CLIController.render_error()
        ↓
"Error: ..." is printed
```

The outer worker loop still calls `task_done()` in `finally`, then waits for the
next queue item. Rendering-callback errors are not misclassified as processor
errors because the line callback remains outside the processor-iteration
exception block.

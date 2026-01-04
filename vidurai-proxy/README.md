# ⚠️ STATUS: PROTOTYPE
> This component is an experimental API interceptor. Not for production use in v2.2.0.

# Vidurai LLM Proxy

A transparent HTTP proxy for injecting Vidurai context into OpenAI-compatible API calls.

## Functionality
Intercepts outbound API requests to inject `system` messages containing the current SF-V2 project gist.

## Middleware Pipeline
1.  **Intercept:** Captures `POST /v1/chat/completions`.
2.  **Analyze:** Identifies the target project ID from the request metadata.
3.  **Retrieve:** Fetches the compressed context from the Vidurai Daemon.
4.  **Inject:** Prepends context to the `messages` array.
5.  **Forward:** Sends the modified payload to the upstream provider (OpenAI/Anthropic).

## Configuration
* `UPSTREAM_BASE_URL`: The target API (e.g., `https://api.openai.com/v1`).
* `CONTEXT_MODE`: `headers` (inject via HTTP headers) or `body` (inject via JSON body).

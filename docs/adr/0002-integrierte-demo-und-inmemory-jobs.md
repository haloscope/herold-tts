# ADR 0002: Integrated static demo page and in-memory job tracking

**Status:** Accepted (2026-08-03)

## Context

The roadmap calls for an example web service showing how to use Herold-TTS after the CLI and REST API. The v0.3.x API was not sufficient: rendering and conversion were fire-and-forget background tasks (HTTP 202 without a job reference). There was no way to determine completion or failure or retrieve generated audio over HTTP. Options for the demo included (a) a static HTML page served by FastAPI, (b) Gradio (already installed as a `qwen-tts` dependency), and (c) a separate frontend container. Options for tracking included an in-memory registry, file polling, and a persistent queue.

## Decision

1. **Embed a self-contained static demo in FastAPI** (`herold/static/index.html`, mounted at `/demo`; `/` redirects there). One container, one port, no CDN dependencies. The page uses only the public REST API, so it also serves as an integration example. Gradio was rejected because it bypasses the API; a separate frontend was unnecessary for a demo.
2. **Track jobs in memory** in `herold/api.py` (dictionary plus `threading.Lock`; `job_id` in the HTTP 202 response; `GET /api/jobs/{id}`). Exceptions raised by `render_batch` or `batch_convert` are recorded as `failed` with an error message.
3. **Expose results through file endpoints** (`GET /api/files` and `GET /api/files/{dir}/{name}`), reusing `convert.validate_filename_stem` and allowlists for directories and extensions.

## Consequences

- Job states do not survive restarts or synchronize between instances. This is acceptable for a demo or single instance. Multi-instance production or guaranteed job recovery would require a persistent queue (for example Redis) and a new ADR.
- No authentication or rate limiting is provided. Operate the API behind a trusted network boundary, not on the open Internet.
- Both Dockerfiles already copy `herold/`, so the demo is included without an additional build step.

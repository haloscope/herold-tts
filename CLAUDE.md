# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Herold-TTS (package `herold`, version in `herold/__init__.py`) renders pre-produced German/English phone and voicemail announcements with **one consistent voice**, using Qwen3-TTS (1.7B, MIT-licensed) voice cloning. It's a batch pipeline + REST API, not a live/streaming TTS service. The stack targets an NVIDIA Blackwell GPU (CUDA 12.8+) with a CPU fallback path (`docker/Dockerfile.cpu`).

Communication with the user is in German. Builds and end-to-end tests run on a separate Windows(WSL)/Debian machine (RTX 5090); this Mac has no Python toolchain — only editing, tests-in-container, and git happen here.

## Commands

```bash
# Build & start (GPU host) — compose up starts the API on port 8000
docker compose build
docker compose up -d          # → http://localhost:8000/ (Demo) · /docs (Swagger UI)
docker compose --profile cpu up -d   # CPU-Variante → Port 8001

# Blackwell/CUDA check after build
docker compose exec herold-tts-gpu python -c \
  "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
# expect: 2.x.x+cu128 ... 12.8 ... <GPU name>

# Pipeline (run in order, inside the container)
docker compose exec herold-tts-gpu python -m herold.audition  # candidate voices → data/audition/*.wav
docker compose exec herold-tts-gpu python -m herold.render    # ansagen.yaml → data/renders/*.wav
docker compose exec herold-tts-gpu python -m herold.convert   # WAV → AAC+MP3 (loudness norm) → data/final/

# Tests (no GPU/model needed — qwen_tts is mocked in tests/conftest.py — but torch
# and pytest must be installed: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
pytest
pytest tests/test_render.py                                    # one file
pytest tests/test_render.py::TestValidateText::test_valid_text # one test
pytest --cov=herold                                            # with coverage
```

There is no lint config and no pyproject.toml/pytest.ini — pytest discovery relies on `tests/__init__.py` + `tests/conftest.py`.

## Architecture

Three separate stages that hand off files on disk (no in-process chaining), plus a thin API wrapper. The whole design exists to satisfy one constraint: the same voice across German and English, via Qwen3-TTS VoiceClone (decision log in README.md).

1. **`audition.py`** — one-time voice exploration: CustomVoice presets, VoiceDesign (voice-by-text-description), and a "design-then-clone" workflow (needed because none of the 9 CustomVoice presets is a German native). A human picks the favorite; that file becomes `config.ref_audio_file`.
2. **`render.py`** — production batch step. Loads the reference audio once, builds a single `voice_clone_prompt`, then per entry in `resources/ansagen.yaml` (`id`, `text_de`, `text_en`) synthesizes **only two** clips (EN, DE) and derives `<id>_multiversion.wav` (EN + 2 s silence + DE) by concatenation — deliberately not a third synthesis (50% render-time saving). Preserve this when touching render logic. Output: `data/renders/<id>_{en,de,multiversion}.wav`, 24 kHz WAV master.
3. **`convert.py`** — converts every WAV in `renders_dir` to `.m4a` (AAC 192k) and `.mp3` (VBR ~192k) in parallel (`ThreadPoolExecutor`, 2 ffmpeg subprocesses per file) with EBU R128 loudness normalization (`loudnorm=I=-23:TP=-1.5:LRA=11`). Requires `ffmpeg` on PATH.

**`api.py`** — FastAPI wrapper around `render_batch`/`batch_convert`: validates synchronously, hands work to `BackgroundTasks`, returns 202 with a `job_id`. An in-memory job registry (`jobs` dict + lock; lost on restart, single-instance by design — ADR 0002) backs `GET /api/jobs/{id}`; `GET /api/files` + `GET /api/files/{dir}/{name}` list/serve results (path-safe via `convert.validate_filename_stem`). `/demo` (and `/` via redirect) serves `herold/static/index.html`, a self-contained example web frontend that uses only the public API.

**`config.py`** — single source of truth: module-level `config` singleton (`TTSConfig` dataclass) for paths, device, dtype, audio and codec parameters. Add new tunables here, don't hardcode them in scripts. `get_device()` honors the `TTS_DEVICE` env var first (compose sets `cuda:0`; the CPU image sets `cpu`), then CUDA-if-available.

**`logger.py`** — use `setup_logger(name)` per module (not `logging.getLogger` directly) for consistent formatting.

**Validation** lives next to its consumer, isolated and unit-testable without the model: `render.validate_text`/`AnsageEntry` (length ≤ 5000, non-empty; DoS protection) and `convert.validate_filename_stem` (alphanumeric/underscore/hyphen; path-traversal protection). Keep new validation similarly isolated. Tests mock the entire `qwen_tts` module in `tests/conftest.py`; model-calling code (`render_batch`, audition runs) is not covered.

## Signature voice

`data/audition/reference_design_de.wav` is the **signature voice** — the VoiceClone reference every render depends on. It is deliberately committed (`.gitignore` exception; all other `data/` outputs stay ignored) and **must be preserved**. Never delete, regenerate, or "clean up" this file; without it no render is reproducible.

## Docker

Both Dockerfiles are multi-stage (builder venv → slim runtime) and drop to a non-root user (uid 999: `oskar` in GPU image, `herold` in CPU image):

- `docker/Dockerfile` — GPU, `nvidia/cuda:12.8.1-runtime-ubuntu24.04`. CUDA 12.8+ is a hard requirement for Blackwell (sm_120); older bases fail with "no kernel image available". Don't downgrade without re-checking.
- `docker/Dockerfile.cpu` — `ubuntu:24.04`, `TTS_DEVICE=cpu`, thread caps via `OMP_NUM_THREADS`/`MKL_NUM_THREADS` (`TORCH_NUM_THREADS` is a no-op — that was bug v0.3.3).

`docker-compose.yml` starts the GPU service (`herold-tts-gpu`, port 8000) by default; the CPU service (`herold-tts-cpu`, port 8001) is behind the compose profile `cpu`.

## Gotchas

- `qwen-tts` is intentionally **not** in `requirements.txt`: its dependency resolution pulls an incompatible torchaudio. The Dockerfiles install it with `--no-deps` plus explicitly pinned deps; `torch`/`torchaudio` are a matched cu128 pair — always upgrade them together.
- Non-root container user: `HF_HOME=/app/.cache/huggingface` (no real `$HOME`) and `NUMBA_CACHE_DIR=/tmp/numba_cache` are load-bearing — removing them breaks model download / librosa import. The HF cache is not volume-mounted, so image rebuilds re-download ~3.8–11 GB (see docs/HARDWARE.md).
- Host-side bind-mount dirs (`data/{audition,renders,final}`) must be writable by uid 999, or WAV writes fail with a generic `LibsndfileError` (see docs/DEPLOYMENT.md "Volume Permissions").
- `render_batch`/`audition.get_model` don't fully release GPU memory on exception paths — mind VRAM when adding model-loading code.
- Measured performance/disk numbers live in docs/HARDWARE.md; old README/DEPLOYMENT estimates were superseded.
- Branch `backup/main-v0.3.0` preserves the pre-v0.3.3 main; `origin/patch-03520` was the test-env transfer branch (contains runtime artifacts and a 13 MB zip in history — don't merge it).

## Working Guidelines

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.
Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

Touch only what you must. Clean up only your own mess.
When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

Define success criteria. Loop until verified.
Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

### 5. Document Decisions (ADR) and Work (AAR)

Development work must be documented continuously, in German, in two forms:

- **ADR** (Architecture Decision Record) — `docs/adr/NNNN-<slug>.md`, sequentially numbered.
  Write one whenever a decision shapes architecture, tooling, or process (engine choice, branch
  strategy, format decisions, …). Sections: Status / Kontext / Entscheidung / Konsequenzen.
  Never rewrite an accepted ADR — supersede it with a new one and link both.
- **AAR** (After Action Review) — `docs/aar/YYYY-MM-DD-<slug>.md`. Write one after significant
  work sessions, releases, or incidents. Sections: Ziel / Was geschah / Gelernt / Offene Punkte.

CHANGELOG.md records *what* changed per version; ADRs record *why* decisions were made; AARs
record *how* the work went. Keep all three current — undocumented decisions are the failure mode
this exists to prevent (e.g. the v0.1.0 production runs on the test machine were never recorded).

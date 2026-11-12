# Changelog

## v0.4.4 — English Documentation & Localization

**Release Date:** 2026-11-12

### 🌍 Localization and documentation

- Standardized the project's documentation, comments, runtime diagnostics, CI messages, and demo interface in **English**. Existing German announcement data (`text_de`), voice-reference audio, API field names, and stable file paths are intentionally unchanged.
- Updated the README for the current application, correcting the version summary and published-release history, documenting the supported GPU and CPU commands, asynchronous REST jobs, audio retrieval, and security limitations.
- Translated the historical changelog, ADRs, AARs, acceptance checklist, backlog, and deployment documentation without changing the recorded outcomes or uncompleted test items.
- Updated the software bill of materials against the declared dependencies and documented its scope: it is a source/manifest inventory, not a generated SPDX or CycloneDX dependency lockfile.

### 🧪 Validation

- The source-tree audit returned **zero German prose findings** after excluding the intentionally German speech fields. The existing **41 unit/API tests passed** in the preparation environment. The same checks should be rerun after applying the patch in the target checkout.
- No GPU synthesis, CPU model inference, or complete audio end-to-end validation is claimed for this documentation/localization release.

### ⚠️ Compatibility

- No intended changes to REST routes, request/response field names, audio codecs, file naming, or speech content.
- The browser demo's interface language changes from German to English; intentionally German sample announcement content stays German.

---

## v0.4.3

**Release Date:** 2026-08-07

### 🔒 Security

- **SAST and secret detection restored:** GitLab security templates (`Security/SAST.gitlab-ci.yml` and `Security/Secret-Detection.gitlab-ci.yml`) run again in the `test` stage of each pipeline. They were part of the original pipeline on 2026-06-25 but had been removed with the old `.gitlab-ci.yml` during restructuring on 2026-07-06. Automated changelog generation from the old CI was deliberately *not* restored: since v0.3.x, changelog entries have been maintained manually with the ADR/AAR process.
- **Container vulnerability scanning with Trivy:** a new `container-scan` job runs in the `scan` stage on `main`, inspecting newly built GPU and CPU images for HIGH and CRITICAL CVEs. It is initially report-only (`allow_failure`), with JSON artifacts. GitLab's official container-scanning template requires an Ultimate subscription and therefore was not used.
- **JUnit test reports:** the `test` job uploads `pytest-report.xml` as a JUnit report, making test outcomes visible in the GitLab pipeline interface.

### 🔧 Maintenance

- Introduced factual English Conventional Commit messages and rewrote history accordingly (ADR 0004). Author and committer timestamps were normalized to a clearly synthetic 12:00 UTC to reduce the disclosure of personal working patterns.

---

## v0.4.2

**Release Date:** 2026-08-03

### ✨ Features

- **CI pipeline (`.gitlab-ci.yml`, ADR 0003):** runs pytest on every push using CPU PyTorch wheels with a mocked model. On `main`, it also builds and pushes GPU and CPU Docker images to the GitLab registry under both versioned and `latest` tags (`…/gpu:<version|latest>` and `…/cpu:<version|latest>`). The version is read from `herold/__init__.py`. The cleanup job retains only the current and preceding version tag per image (`keep_n=2`) while preserving `latest`.
- Target machines can pull ready-made images instead of building locally. Local builds remain documented as a fallback in `docs/DEPLOYMENT.md`.

### ⚙️ One-time setup

- Enable the project container registry.
- Configure `REGISTRY_CLEANUP_TOKEN` as a masked CI/CD variable backed by a Maintainer-role Project Access Token with the `api` scope. Without it, only the cleanup job fails; that job intentionally has `allow_failure`.

---

## v0.4.1

**Release Date:** 2026-08-03

### 🐛 Bug fixes

- **Reduced unnecessary CUDA dependencies in the CPU image:** `docker/Dockerfile.cpu` installs torch and torchaudio explicitly from the PyTorch CPU-wheel index (`download.pytorch.org/whl/cpu`) before resolving `requirements.txt`. Default PyPI wheels had bundled a full CUDA runtime (measured in the earlier arm64 build: 9.8 GB image and approximately 70-minute build time), which was unnecessary for CPU-only use.
- **Repaired health checks for both images:** previously, checking health every 30 seconds imported the entire torch/qwen-tts stack. This was CPU-intensive and could exceed the 10-second timeout on slower hosts, incorrectly marking healthy containers `unhealthy`, as observed in the Mac smoke test. The check now uses a lightweight HTTP request to `/api/status`, and `start-period=180s` allows for slow initial API imports. Containers started without the API (for example `docker run … bash`) will report `unhealthy`; this is an expected cosmetic side effect.

### ✅ Verification (partial Apple Silicon Mac test)

- The CPU image **before** the CUDA fix built natively for `linux/arm64`; dependencies provided aarch64 wheels. The container passed smoke checks for `/api/status` (`device=cpu`, v0.4.0), `/` → `/demo/`, the demo page, `/api/files`, and 404/400 error handling.
- A complete end-to-end run (render, conversion, Hugging Face cache persistence) and a build of the corrected images were **not yet verified** on the test machine. The Mac test was stopped because of heavy system load, and the test resources were removed.

---

## v0.4.0

**Release Date:** 2026-08-03

### ✨ Features

- **Job status API:** `POST /api/render` and `POST /api/convert` now return a `job_id`; `GET /api/jobs/{job_id}` reports `queued`, `running`, `done`, or `failed`, including failure details. Jobs are stored in memory by design, for a single instance (see ADR 0002).
- **File endpoints:** `GET /api/files` lists files from `data/renders/` and `data/final/`; `GET /api/files/{dir}/{name}` streams or downloads results, with path traversal protection through the existing `validate_filename_stem` and directory/extension allowlists.
- **Example demo web service:** a self-contained HTML/JS page at `/demo` (with `/` redirecting there) provides text entry → rendering → job polling → audio playback → AAC/MP3 conversion → downloads. It uses only the public REST API and illustrates integration patterns.
- **CPU variant as a Compose profile:** the CPU container `herold-tts-cpu` is available under profile `cpu` on port 8001, with the same mounts as the GPU container. The default GPU service remains enabled; on CPU-only hosts explicitly start `herold-tts-cpu` to avoid also starting the GPU service.

### ✅ Verification

- **41 tests passed:** 28 previous tests plus 13 new API cases covering path traversal, job lifecycle with a mocked model, file listing/downloads, and demo serving. Added `httpx` to `requirements.txt` for FastAPI `TestClient`.
- Both Docker Compose configurations were validated with `docker compose config`. A complete GPU/CPU hardware end-to-end test on the test machine was still pending.

### 📝 Documentation

- Corrected obsolete Docker build/start commands in `DEPLOYMENT.md` (Dockerfile paths and `python -m herold.api` rather than `cd work`) and documented the new routes and demo.
- Added ADR 0002 for the integrated demo and in-memory jobs; updated README quick start and CLAUDE.md.

---

## v0.3.5

**Release Date:** 2026-08-03

### 🔧 Maintenance

- **HuggingFace model cache persisted:** `docker-compose.yml` now mounts `./data/hf-cache` to
  `HF_HOME` (`/app/.cache/huggingface`), so Qwen3-TTS model weights (~3.8–11 GB) survive image
  rebuilds and container recreates instead of being re-downloaded on every `audition`/`render`
  run (open point from AAR 2026-08-03 / docs/HARDWARE.md). `data/hf-cache/` is gitignored;
  the setup instructions in docs/DEPLOYMENT.md ("Volume Permissions") and the cache note in
  docs/HARDWARE.md were updated accordingly.

---

## v0.3.4

**Release Date:** 2026-08-03

### 🔧 Maintenance

- **v0.3.3 cleanly adopted onto `main`:** the tested state from the `patch-03520` transfer branch
  was taken over file-by-file instead of merged, keeping `.gitignore`/`.dockerignore` intact and
  excluding runtime artifacts (`data/renders`, `data/final`, `tests/__pycache__`) and the 13 MB
  transfer zip from `main`'s history. The previous `main` (v0.3.0) is preserved as branch
  `backup/main-v0.3.0`.
- **Signature voice preserved in repo:** `data/audition/reference_design_de.wav` — the VoiceClone
  reference every render depends on — is now committed with an explicit `.gitignore` exception.
  Previously it existed only on the test machine and in the transfer branch; without it no render
  is reproducible.
- **README:** stale `docker compose exec qwen3-tts …` commands updated to the actual Compose
  service name `herold-tts-gpu` (7 occurrences)
- **`CLAUDE.md` added:** merged from the two independent drafts (main working guidelines +
  patch-03520 architecture notes), with updated commands matching the v0.3.3 Compose setup

---

## v0.3.3

**Release Date:** 2026-07-07

### 🐛 Bug Fixes

- **`docker/Dockerfile.cpu` thread limit silently ignored:** the image set `TORCH_NUM_THREADS=4`
  to cap CPU inference threads, but this is not an environment variable PyTorch (or OpenMP/MKL)
  actually reads — it was a no-op. On a 24-core test machine, PyTorch defaulted to using all
  available cores instead of the intended 4. Replaced with the environment variables PyTorch's
  threading backends actually respect: `OMP_NUM_THREADS=4` and `MKL_NUM_THREADS=4`.

### ✅ Verified

- Built `herold-tts:cpu` from `docker/Dockerfile.cpu` with all v0.3.2 fixes applied: `import
  qwen_tts` clean as non-root, `python -m herold.api` starts, `GET /api/status` → 200
  (`"device":"cpu"`, `"version":"0.3.3"`), `GET /` → 307 to `/docs`
- Rendered the shortest `ansagen.yaml` entry (`unavailable`, 99+153 chars) end-to-end via
  `POST /api/render` against the CPU image with the existing `reference_design_de.wav` mounted
  in — produced `_en.wav`, `_de.wav`, `_multiversion.wav` with no errors. Wall-clock time for the
  full request (model load + voice-clone-prompt + both syntheses + combine) was ~2 min 39 sec,
  not the 10-15x-slower-than-GPU figure `docs/DEPLOYMENT.md` documents for smaller (8-core)
  machines — this test ran on a 24-core host, and the `TORCH_NUM_THREADS` no-op above meant
  PyTorch used far more parallelism than the image intended prior to this fix

---

## v0.3.2

**Release Date:** 2026-07-06

Deployment/build fixes found while getting v0.3.1 running end-to-end in Docker for the first
time — no application logic changed, only the container build, Compose config, and API wiring.

### 🐛 Bug Fixes

- **Docker build failure:** `docker-compose.yml` referenced `Dockerfile`/`Dockerfile.cpu` at the
  repo root; both actually live under `docker/` — fixed the `dockerfile:` paths (build context
  stays `.` since `COPY herold/`/`COPY resources/` are root-relative)
- **`qwen_tts` missing at runtime:** the package was never installed — added to the Docker build
  (via `--no-deps` plus its actual dependencies, installed separately to avoid a transitive
  `torchaudio` upgrade that would break the pinned cu128 torch/torchaudio pair; see the
  "PyTorch dependency conflict" note in the v0.1 README)
- **API startup crash:** `Path(config.renders_dir/final_dir).mkdir(exist_ok=True)` failed with
  `FileNotFoundError` on a fresh container because `/app/data` didn't exist yet — added
  `parents=True`
- **`numba` cache permission error:** `librosa` (a transitive `qwen_tts` dependency) crashed on
  import as the non-root container user because `numba` tried to write its JIT cache next to the
  installed package files under `/opt/venv`, which only `root` owns — set `NUMBA_CACHE_DIR=/tmp/numba_cache`
- **`herold/api.py` couldn't start via `python -m herold.api`:** `uvicorn.run("api:app", ...)`
  referenced a bare top-level module name instead of `herold.api:app`, so the documented
  `python -m herold.api` startup path always failed with "Could not import module 'api'"
- **`http://localhost:8000/` returned 404:** added a `GET /` → `/docs` redirect so the API root
  actually shows the Swagger UI, matching user expectation
- **`docker-compose up herold-tts-gpu` didn't start anything usable:** the service had no
  `command:` (fell back to the image's default `CMD ["/bin/bash"]`) and no `ports:` mapping —
  added `command: ["python", "-m", "herold.api"]` and `ports: ["8000:8000"]` so the documented
  quick-start (`docker-compose up herold-tts-gpu` → `http://localhost:8000/docs`) actually works
- **HuggingFace model download crashed with `PermissionError: /home/oskar`:** `audition.py`/
  `render.py` download Qwen3-TTS model weights via `huggingface_hub`, which defaults to caching
  under `$HOME/.cache/huggingface`. The container's non-root user (`oskar`/`herold`) is created
  via `useradd -r` (a system account, no `-m`), so `$HOME=/home/oskar` points at a directory that
  was never created — every model download failed immediately. Fixed by setting
  `HF_HOME=/app/.cache/huggingface` (inside the already-`chown`'d `/app` tree) in both Dockerfiles.
- **Volume-mounted data directories (`data/audition`, `data/renders`, `data/final`) not writable
  by the container:** these paths are bind-mounted from the host into `docker-compose.yml`. Docker
  auto-creates missing bind-mount source directories on the **host** as `root:root` (mode 755).
  Since the container runs as non-root (`oskar`, uid 999), every `sf.write(...)` into these
  directories failed with `LibsndfileError: ... System error.` (the underlying `EACCES` is masked
  by libsndfile's generic error message). Fixed for this environment by running
  `docker compose exec --user root herold-tts-gpu chown -R oskar:oskar /app/data` once, which
  reaches through the bind mount and fixes ownership on the host side too (container root has
  host-root file permissions here since no user-namespace remapping is configured). This is a
  one-time manual fix, not a code change — a fresh clone / fresh host will need the same `chown`
  (or `mkdir -p data/{audition,renders,final} && chown -R 999:999 data/` on the host) before the
  first `audition`/`render`/`convert` run. Documented in `docs/DEPLOYMENT.md`.
- **API version drifted from `herold.__version__`:** `herold/api.py` hardcoded `"0.2.0"` in two
  places (`FastAPI(version=...)` and `StatusResponse.version` default) instead of reading the
  package version — both now import `__version__` from `herold/__init__.py` so `/api/status` and
  `/docs` can't fall out of sync with the package version again

### ✅ Verified

- Full pipeline run end-to-end against real hardware (RTX 5090): `audition.py` → voice reference
  generated, `render.py` → all 3 `ansagen.yaml` entries rendered (9 WAV files), `convert.py` → 18
  AAC/MP3 files produced
- `docker compose up -d herold-tts-gpu` → container reports `healthy`, `GET /api/status` → 200,
  `GET /` → 307 to `/docs`

---

## v0.3.1

**Release Date:** 2026-07-06

### 🔨 Refactor

Restructure project to production-ready layout. Reorganize codebase from ad-hoc `work/`
structure to professional Python package layout (`herold/`), improving maintainability,
testability, and deployment clarity.

- Rename `work/` → `herold/` (Python package with `__init__.py`)
- Create `resources/` for input data (`ansagen.yaml`)
- Create `data/` for runtime outputs (`renders/`, `final/`, `audition/`)
- Create `docker/` for containerization (`Dockerfile`, `Dockerfile.cpu`)
- Create `docs/` for documentation (`DEPLOYMENT.md`)
- Update all Python imports to use relative module paths (`.logger`, `.config`)
- Update test imports to use package namespace (`herold.render`, `herold.convert`)
- Centralize config paths in `config.py` (`PROJECT_ROOT` resolution)
- Update `docker-compose.yml` volume mounts to new directory layout
- Update Dockerfiles to `COPY` from new package structure
- Add comprehensive `.gitignore` with Python + project-specific rules
- Remove obsolete files (`.reviews/`, `.gitlab-ci.yml`, testfile)

All 25 unit tests passing. Imports and config paths verified working.

**Breaking change:** Python scripts now require `python -m herold.render` instead of
`cd work && python render.py`. Module import paths changed to relative (use `from herold.config`
not `from config`).

Refs: v0.3.0 production readiness

---

## v0.3.0

**Release Date:** 2026-07-06

### 🔒 Security Fixes

- **Path traversal (convert.py):** Fixed — `validate_filename_stem()` now restricts WAV filename
  stems to alphanumeric/underscore/hyphen before they're used to build output paths
- **Text DoS (render.py):** Fixed — `validate_text()` enforces `MAX_TEXT_LENGTH` and non-empty
  input on all `ansagen.yaml`/API text fields via the `AnsageEntry` dataclass
- Both fixes are covered by dedicated unit tests (`tests/test_convert.py`, `tests/test_render.py`)

### 🚀 New Features

- **REST API** (`herold/api.py`): FastAPI service with `POST /api/render`, `POST /api/convert`,
  `GET /api/status`; render/convert run as background tasks and return `202 Accepted`
- **CPU-only Docker image** (`docker/Dockerfile.cpu`): runs without a GPU via `TTS_DEVICE=cpu`,
  as previously flagged as a future release in v0.2.0
- **Centralized configuration** (`herold/config.py`): single `TTSConfig` dataclass for device,
  dtype, paths, audio, and codec settings, auto-detecting CUDA vs CPU via `TTS_DEVICE`
- **Centralized logging** (`herold/logger.py`): consistent `[LEVEL] module — message` format
  across all scripts

### 🧪 Testing

- Added `tests/` suite (`test_render.py`, `test_convert.py`) covering the new validation logic,
  with `qwen_tts` mocked in `conftest.py` so tests run without a GPU or model download
- `pytest-cov` added to `requirements.txt`

### 🔧 Technical Notes

- Both Docker images (GPU and CPU) now use non-root users and multi-stage builds
- Minimum Python 3.9+ required
- All code follows MIT license terms

---

## v0.2.0

**Release Date:** 2026-06-26

### 🔍 Code Review & Quality Assurance

- **Comprehensive codebase audit** completed covering security, performance, and maturity
- **Security Review:** 5 findings identified (2 critical, 3 high/medium) — fixes planned for v0.3.0
- **Performance Analysis:** Identified optimization opportunities (parallelization, caching)
- **Maturity Assessment:** Code score 5.2/10 → Roadmap for Production-Ready status by Q3 2026

### 🚀 Improvements

- **GitLab CI/CD Pipeline:** Added automatic changelog generation on SemVer tag releases
- **Error Handling:** Improved error output and debugging visibility in changelog pipeline
- **Logging:** Added progress indicators in CI/CD jobs for better observability

### 📚 Documentation

- Comprehensive `.reviews/` structure created with detailed findings and recommendations
- Security review documented with actionable fixes
- Performance optimization roadmap documented

### ⚠️ Known Issues

- **2 Critical Security Findings** pending implementation (v0.3.0):
  - Path traversal in convert.py
  - Text DoS vulnerability in render.py
- See `.reviews/` for full audit details and fix recommendations

### 🔧 Technical Notes

- Minimum Python 3.9+ required
- CUDA 12.8 for GPU, CPU-only fallback supported (future release)
- All code follows MIT license terms

---

## v0.1

Initial release with core TTS rendering pipeline.

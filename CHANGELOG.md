# Changelog

## v0.4.3

**Release Date:** 2026-08-07

### 🔒 Security

- **SAST + Secret Detection reaktiviert:** Die GitLab-Security-Templates
  (`Security/SAST.gitlab-ci.yml`, `Security/Secret-Detection.gitlab-ci.yml`) laufen wieder
  in der test-Stage jeder Pipeline. Sie waren Teil der ursprünglichen CI (2026-06-25),
  wurden aber beim Restrukturierungs-Commit am 2026-07-06 mitsamt der alten
  `.gitlab-ci.yml` entfernt und fehlten seither. Die automatische Changelog-Generierung
  der alten CI wird bewusst **nicht** reaktiviert — das CHANGELOG wird seit v0.3.x manuell
  und kuratiert gepflegt (ADR/AAR-Prozess)
- **Container-CVE-Scan (Trivy):** neuer `container-scan`-Job (Stage `scan`, nur auf `main`)
  prüft die frisch gebauten gpu/cpu-Images auf HIGH/CRITICAL-CVEs — report-only
  (`allow_failure`), JSON-Reports als Artefakte. GitLabs offizielles
  Container-Scanning-Template ist Ultimate-only und daher ungeeignet
- **JUnit-Testreport:** `test`-Job lädt `pytest-report.xml` als JUnit-Report hoch —
  Testergebnisse erscheinen direkt in der GitLab-Pipeline-Ansicht

### 🔧 Maintenance

- Commit-Konventionen eingeführt und Historie entsprechend umgeschrieben (ADR 0004):
  Messages einheitlich englisch-sachlich, Zeitstempel aller Commits auf 12:00 UTC
  anonymisiert

---

## v0.4.2

**Release Date:** 2026-08-03

### ✨ Features

- **CI-Pipeline (`.gitlab-ci.yml`, ADR 0003):** pytest bei jedem Push (CPU-torch, Modell
  gemockt); auf `main` zusätzlich Build + Registry-Push beider Images
  (`…/gpu:<version|latest>`, `…/cpu:<version|latest>`, Version aus `herold/__init__.py`);
  Cleanup-Job hält pro Image nur aktuelle + Vorgänger-Version in der Registry (`keep_n=2`,
  `latest` bleibt)
- Zielmaschinen können damit fertige Images pullen statt selbst zu bauen; lokales Bauen
  bleibt als Fallback dokumentiert (docs/DEPLOYMENT.md)

### ⚙️ Setup-Hinweise (einmalig)

- Container Registry im Projekt aktivieren
- CI/CD-Variable `REGISTRY_CLEANUP_TOKEN` anlegen (Project Access Token, Rolle Maintainer,
  Scope `api`, masked) — ohne sie schlägt nur der Cleanup-Job fehl (`allow_failure`)

---

## v0.4.1

**Release Date:** 2026-08-03

### 🐛 Bug Fixes

- **CPU-Image um ~4 GB CUDA-Ballast erleichtert:** `docker/Dockerfile.cpu` installiert
  torch/torchaudio jetzt explizit aus dem CPU-Wheel-Index (`download.pytorch.org/whl/cpu`),
  bevor `requirements.txt` aufgelöst wird. Die Standard-PyPI-Wheels bündeln die komplette
  CUDA-Runtime (gemessen beim arm64-Testbuild: 9,8 GB Image, ~70 min Build) — im CPU-Image
  totes Gewicht
- **Healthcheck beider Images repariert:** statt alle 30 s den kompletten torch/qwen-tts-Stack
  zu importieren (CPU-intensiv, riss auf langsameren Hosts das 10-s-Timeout → Container
  dauerhaft fälschlich `unhealthy`, beobachtet beim Mac-Smoke-Test) jetzt eine leichte
  HTTP-Probe gegen `/api/status`; `start-period=180s` deckt den langsamen Erstimport der API.
  Hinweis: Container, die ohne API laufen (z. B. `docker run … bash`), melden nun `unhealthy` —
  kosmetisch

### ✅ Verified (Teiltest, Apple-Silicon-Mac)

- CPU-Image (noch vor dem CUDA-Fix) baute nativ für linux/arm64 — alle Abhängigkeiten haben
  aarch64-Wheels; Smoke-Check gegen den laufenden Container grün: `/api/status`
  (`device=cpu`, v0.4.0), `/` → `/demo/`, Demo-Seite, `/api/files`, 404-/400-Absicherung
- Voller End-to-End-Lauf (Render + Konvertierung + HF-Cache-Persistenz) sowie Build der
  gefixten Images stehen weiter für die Testmaschine aus; der Mac-Test wurde wegen
  Systemlast abgebrochen und vollständig zurückgebaut

---

## v0.4.0

**Release Date:** 2026-08-03

### ✨ Features

- **Job-Status-API:** `POST /api/render` und `POST /api/convert` geben jetzt eine `job_id`
  zurück; `GET /api/jobs/{job_id}` liefert `queued | running | done | failed` inkl. Fehlertext.
  In-Memory-Registry, Single-Instance by design (siehe `docs/adr/0002`)
- **Datei-Endpoints:** `GET /api/files` (Listing von `data/renders/` und `data/final/`) und
  `GET /api/files/{dir}/{name}` (Download/Streaming, Path-Traversal-sicher über das vorhandene
  `validate_filename_stem` plus Verzeichnis-/Extension-Whitelist)
- **Exemplarischer Demo-Webservice:** selbst-enthaltene HTML/JS-Seite unter `/demo`
  (Root `/` leitet dorthin um): Ansage eingeben → rendern → Job-Polling → Audio-Player →
  AAC/MP3-Konvertierung → Downloads. Nutzt ausschließlich die öffentliche REST-API
  (Integrations-Blaupause)
- **CPU-Variante als Compose-Profil:** `docker compose --profile cpu up -d` startet
  `herold-tts-cpu` (Port 8001) mit denselben Mounts wie der GPU-Service; Standardverhalten
  unverändert

### ✅ Verified

- 41 Tests grün (28 bestehende + 13 neue API-Tests: Path-Traversal, Job-Lebenszyklus mit
  gemocktem Modell, Datei-Listing/-Download, Demo-Auslieferung); `httpx` für den FastAPI
  `TestClient` zu `requirements.txt` hinzugefügt
- `docker compose config` für beide Profile validiert; End-to-End-Lauf (GPU + CPU) auf der
  Testmaschine steht aus

### 📝 Docs

- DEPLOYMENT.md: veraltete Build-/Startbeispiele korrigiert (`docker/Dockerfile`-Pfade,
  `python -m herold.api` statt `cd work`), neue Endpoints und Demo dokumentiert
- ADR 0002 (integrierte Demo + In-Memory-Jobs), README-Schnellstart, CLAUDE.md aktualisiert

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
  "torch-Konflikt-Risiko" note in `README.md`)
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

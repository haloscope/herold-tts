# Herold-TTS

**Self-hosted, bilingual text-to-speech for pre-rendered telephone and voicemail announcements.**

[![MIT License](https://img.shields.io/github/license/haloscope/herold-tts)](LICENSE)
[![Latest GitHub release](https://img.shields.io/github/v/release/haloscope/herold-tts?label=release)](https://github.com/haloscope/herold-tts/releases)
[![Git tags](https://img.shields.io/github/v/tag/haloscope/herold-tts?label=latest%20tag)](https://github.com/haloscope/herold-tts/tags)
[![Last commit](https://img.shields.io/github/last-commit/haloscope/herold-tts)](https://github.com/haloscope/herold-tts/commits/main)
[![Application version](https://img.shields.io/badge/application%20version-0.4.4-blue)](CHANGELOG.md)

Herold-TTS generates German and English announcements in a **consistent, custom-designed voice** using [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS). It combines a reproducible batch-rendering pipeline with a REST API and a small demo web interface. Audio is generated on your own infrastructure; after the models have been downloaded, synthesis does not require a hosted TTS API.

The project is designed for **pre-rendering**, not real-time or streaming speech synthesis. The application code is licensed under MIT; third-party dependencies and models retain their own licenses.

## Versions and releases

Version **0.4.4** standardizes the documentation and interface language based on the v0.4.3 application. A source version, an annotated Git tag, and a published GitHub Release are **separate**: a version number in the code does not by itself imply that the corresponding tag or release has been published.

| Version | Highlights | Release |
|---|---|---|
| `0.4.4` | English documentation, demo UI, diagnostics, and SBOM refresh | [Release 0.4.4](https://github.com/haloscope/herold-tts/releases/tag/0.4.4) |
| `0.4.3` | GitLab security scans, JUnit reports, and CI hardening | [Release 0.4.3](https://github.com/haloscope/herold-tts/releases/tag/0.4.3) |
| `0.4.2` | GitLab CI/CD builds and container registry publication | [Release 0.4.2](https://github.com/haloscope/herold-tts/releases/tag/0.4.2) |
| `0.4.1` | CPU-image dependencies and HTTP health checks | [Release 0.4.1](https://github.com/haloscope/herold-tts/releases/tag/0.4.1) |
| `0.4.0` | Asynchronous jobs, file endpoints, and demo frontend | [Release 0.4.0](https://github.com/haloscope/herold-tts/releases/tag/0.4.0) |
| `0.3.5` | Persistent Hugging Face model cache | [Release 0.3.5](https://github.com/haloscope/herold-tts/releases/tag/0.3.5) |
| `0.3.4` | Version consolidation and reproducible voice reference | [Release 0.3.4](https://github.com/haloscope/herold-tts/releases/tag/0.3.4) |
| `0.3.3` | CPU inference and Docker runtime fixes | [Release 0.3.3](https://github.com/haloscope/herold-tts/releases/tag/0.3.3) |

Earlier releases and historical tag names are available from [GitHub Releases](https://github.com/haloscope/herold-tts/releases) and [all Git tags](https://github.com/haloscope/herold-tts/tags). The historical tags intentionally use several conventions (`0.1`, `0.1.0`, `v0.2.0`, `0.3.0`, etc.); do not rewrite old tags to standardize their spelling. The [changelog](CHANGELOG.md) records the detailed changes and outstanding validation limits.

## Features

- **One voice across two languages:** German and English announcements use the same voice reference.
- **Voice exploration and reuse:** audition `CustomVoice` presets and `VoiceDesign` candidates, then reuse a selected reference with `VoiceClone`.
- **Three audio variants per announcement:** English, German, and a combined English → 2-second pause → German version.
- **Efficient batch rendering:** only the English and German clips are synthesized; the combined version is assembled from those recordings.
- **Ready-to-use formats:** 24 kHz WAV masters, AAC (`.m4a`) and MP3, with EBU R128 loudness normalization to **−23 LUFS**.
- **REST API:** asynchronous render and conversion jobs, status polling, file listing, and downloads.
- **Integration example:** a browser-based demo that communicates through the public REST API.
- **Docker deployment:** NVIDIA GPU image and a separate CPU-only image, with persistent output and Hugging Face model-cache mounts.
- **Automated tests:** pytest-based tests for the application logic.

## Requirements

| Mode | Requirements | Web interface / API |
| --- | --- | --- |
| NVIDIA GPU | Docker and NVIDIA Container Toolkit; a compatible CUDA GPU (12 GB VRAM is a practical starting point, with more headroom for voice audition) | `http://localhost:8000/` |
| CPU-only | Docker; **32 GB RAM recommended** and a capable multicore CPU | `http://localhost:8001/` |

The GPU image uses the CUDA 12.8 stack and is intended for compatible NVIDIA hardware, including Blackwell. CPU rendering is available but considerably slower. Model weights are fetched on first use, so allow several gigabytes of free disk space. See [Hardware Requirements & Performance](docs/HARDWARE.md) for measured results and disk usage.

> **Note:** The provided Compose services are intended as separate deployment options. When running on a CPU-only machine, explicitly select `herold-tts-cpu` as shown below; simply enabling the `cpu` profile without selecting a service also selects the default GPU service.

## Quick start

### 1. Clone and prepare the data directories

```bash
git clone https://github.com/haloscope/herold-tts.git
cd herold-tts
mkdir -p data/audition data/renders data/final data/hf-cache
```

The containers run with UID `999`. On Linux hosts, ensure the directories mounted from `./data/` are writable by that UID; the [deployment guide](docs/DEPLOYMENT.md#volume-permissions-required-before-first-run) explains the permissions and recovery commands.

### 2A. Start with an NVIDIA GPU

```bash
docker compose build herold-tts-gpu
docker compose up -d herold-tts-gpu
```

- Demo: <http://localhost:8000/>
- API documentation (Swagger): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/status>

Verify GPU visibility from inside the container:

```bash
docker compose exec herold-tts-gpu python -c \
  "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
```

### 2B. Start without an NVIDIA GPU (CPU-only)

Run **instead of** the GPU commands:

```bash
docker compose --profile cpu build herold-tts-cpu
docker compose --profile cpu up -d herold-tts-cpu
```

- Demo: <http://localhost:8001/>
- API documentation: <http://localhost:8001/docs>
- Health check: <http://localhost:8001/api/status>

The following API examples use port `8000`; substitute `8001` for CPU-only deployments.

## REST API

The API accepts requests asynchronously. Rendering or converting audio returns **HTTP 202 Accepted** with a `job_id`; poll the job-status endpoint to determine whether processing has finished.

### Check service health

```bash
curl http://localhost:8000/api/status
```

### Render an announcement

```bash
curl -X POST http://localhost:8000/api/render \
  -H 'Content-Type: application/json' \
  -d '{
    "ansagen": [
      {
        "id": "welcome",
        "text_de": "Willkommen!",
        "text_en": "Welcome!"
      }
    ]
  }'
```

Example accepted response (the job ID will be different):

```json
{
  "status": "accepted",
  "message": "Rendering started",
  "job_id": "3f2a9c1d40be",
  "count": 1,
  "output_dir": "/app/data/renders"
}
```

### Poll job status

```bash
curl http://localhost:8000/api/jobs/3f2a9c1d40be
```

Possible job states: `queued`, `running`, `done`, and `failed`. Job state is held **in memory**, so it is lost when the API process restarts and is not shared across instances.

### Convert WAV files to AAC and MP3

Once rendering has completed:

```bash
curl -X POST http://localhost:8000/api/convert \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Conversion also returns a `job_id`, which can be checked using the same job-status endpoint. The current implementation processes the WAV files in the configured renders directory; the optional `filter_pattern` request field is defined in the API model but is not currently applied by the conversion handler.

### List and download audio files

```bash
curl http://localhost:8000/api/files
curl -O http://localhost:8000/api/files/renders/welcome_en.wav
curl -O http://localhost:8000/api/files/final/welcome_en.mp3
```

The demo page at <http://localhost:8000/> provides a render form, job polling, audio playback, conversion and downloads. It is intended as an **integration blueprint**, not as a substitute for securing the API before exposing it to untrusted networks.

For full endpoint documentation and examples, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Batch rendering workflow

The original command-line workflow is available alongside the REST API. The examples below use the GPU container; replace `herold-tts-gpu` with `herold-tts-cpu` for CPU-only deployment.

### 1. Audition voices (optional)

```bash
docker compose exec herold-tts-gpu python -m herold.audition
```

This creates candidate WAV recordings under `data/audition/` for voice comparison. The production configuration uses a selected German reference recording, `data/audition/reference_design_de.wav`, as the voice-cloning reference. Voice audition is optional if the required reference file is already available.

### 2. Edit the announcements

Edit [`resources/ansagen.yaml`](resources/ansagen.yaml). Each entry supplies a stable ID and separate German and English texts:

```yaml
ansagen:
  - id: welcome
    text_en: "Welcome to our service."
    text_de: "Willkommen bei unserem Dienst."
```

### 3. Render WAV masters

```bash
docker compose exec herold-tts-gpu python -m herold.render
```

Each entry generates:

```text
data/renders/
├── welcome_en.wav            # English only
├── welcome_de.wav            # German only
└── welcome_multiversion.wav  # English + 2 s silence + German
```

The pipeline synthesizes two clips per announcement and assembles the third, combined variant without a third model invocation. WAV masters are produced at **24 kHz**.

### 4. Convert and normalize

```bash
docker compose exec herold-tts-gpu python -m herold.convert
```

Converted files are placed in `data/final/`:

```text
data/final/
├── welcome_en.m4a
├── welcome_en.mp3
├── welcome_de.m4a
├── welcome_de.mp3
├── welcome_multiversion.m4a
└── welcome_multiversion.mp3
```

Audio conversion uses FFmpeg, with EBU R128 loudness normalization targeting **−23 LUFS**; output formats are AAC and variable-bitrate MP3.

## Architecture and design decisions

Herold-TTS separates voice exploration, synthesis and conversion into independent file-based stages, with FastAPI as a lightweight API layer:

```text
Voice exploration (optional)
  CustomVoice / VoiceDesign → selected reference audio
                                  ↓
Announcement texts (EN + DE) → Qwen3-TTS VoiceClone
                                  ↓
                 EN WAV + DE WAV (24 kHz)
                                  ↓
        Combined EN + pause + DE WAV
                                  ↓
                  FFmpeg conversion
                                  ↓
                 AAC (.m4a) + MP3
```

**Why this design?**

- **Qwen3-TTS 1.7B:** chosen to provide bilingual voice consistency and a reusable voice reference.
- **Design-then-clone:** `VoiceDesign` is used to develop the desired voice, while `VoiceClone` keeps the chosen voice consistent across announcements.
- **WAV masters:** conversion can be repeated without resynthesizing the announcement.
- **Combined bilingual version:** assembled from the language-specific clips instead of synthesizing it separately.
- **Self-hosted processing:** model inference takes place locally after the required models have been downloaded.

The main modules are `herold/audition.py`, `herold/render.py`, `herold/convert.py`, `herold/api.py`, and `herold/config.py`.

## Configuration and data

| Path / variable | Purpose |
| --- | --- |
| `resources/ansagen.yaml` | Batch announcement IDs and bilingual text |
| `data/audition/` | Voice comparison samples and reference audio |
| `data/renders/` | Generated WAV masters |
| `data/final/` | Converted AAC and MP3 files |
| `data/hf-cache/` | Persistent Hugging Face model cache |
| `TTS_DEVICE` | Execution device, such as `cuda:0` or `cpu` |
| `herold/config.py` | Central configuration for paths, codecs, audio and rendering settings |

The Docker Compose file mounts the data directories and model cache so output and downloaded model files can survive container recreation. The reference announcement file is mounted read-only.

## Language policy and compatibility

The user-facing UI, API diagnostics, code comments, and project documentation are written in **English**. The application intentionally generates **German and English speech**: `text_de` values, `config.ref_text_de`, the demonstration German speech text, and `reference_design_de.wav` remain German. These are data and stable interface identifiers, not untranslated interface strings.

The localization release does not change the REST JSON field names (`ansagen`, `text_de`, `text_en`), endpoints, audio filename conventions, or reference-audio path, so existing integrations remain compatible.

## Testing and CI

Run the unit tests in an environment with the required Python dependencies installed:

```bash
python -m pip install -r requirements.txt
pytest
# Optional coverage report:
pytest --cov=herold
```

The tests mock Qwen-TTS where applicable; passing them does **not** constitute a complete GPU inference or end-to-end audio-quality test.

The repository includes a **GitLab CI** configuration (`.gitlab-ci.yml`) for tests, image builds and security checks. GitHub migration does not automatically convert this pipeline into GitHub Actions, and no GitHub Actions workflow is claimed here. CI credentials and registry destinations must be reviewed before enabling CI in a new environment.

## Documentation

- [Deployment guide and REST API](docs/DEPLOYMENT.md)
- [Hardware requirements and measured performance](docs/HARDWARE.md)
- [Changelog](CHANGELOG.md)
- [Software Bill of Materials](SBOM.md)
- [License](LICENSE)

## License and third-party components

**Herold-TTS application code is distributed under the [MIT License](LICENSE).** Preserve the copyright and license notice when redistributing the project.

The Qwen3-TTS models and related upstream software have their **own licenses** (including Apache-2.0 for Qwen3-TTS models). NVIDIA CUDA/cuDNN are proprietary components, while system utilities such as FFmpeg and SoX have their respective open-source license obligations. See [SBOM.md](SBOM.md) and [SBOM.csv](SBOM.csv) for the refreshed source-level dependency inventory. This is not a complete resolved/image SBOM. Verify the applicable licenses before redistributing models, audio references, or bundled binaries and container images.

*Documentation updated from the v0.4.3 source archive for v0.4.4 on November 12, 2026. Hardware end-to-end validation remains outstanding where noted.*

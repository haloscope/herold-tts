# Herold-TTS — Software Bill of Materials (source inventory)

**Project:** Open Source Communication Platform Architecture (OSKAR)
**Inventory refreshed:** 2026-11-12 for Herold-TTS 0.4.4
**Sources:** [`requirements.txt`](requirements.txt), [`docker/Dockerfile`](docker/Dockerfile), [`docker/Dockerfile.cpu`](docker/Dockerfile.cpu), and [`LICENSE`](LICENSE)
**Machine-readable summary:** [`SBOM.csv`](SBOM.csv)

> **Scope and limitations:** This is a maintained **source-level dependency inventory**, not a fully resolved build SBOM. It does **not** record transitive dependencies, installed package hashes, exact versions selected by pip, per-layer container contents, or a complete SPDX/CycloneDX document. To obtain a release-grade SBOM, build the target image and generate an SBOM from the resulting image/installed environment, then review its licenses and vulnerabilities.

## Project overview

Herold-TTS is a self-hosted pipeline for pre-rendered telephone and voicemail announcements in **German and English**, using a consistent cloned voice. It includes optional voice audition, WAV synthesis, AAC/MP3 conversion, a REST API, and an example browser demo.

The **Herold-TTS application code** is published under the [MIT License](LICENSE). This license does not relicense any upstream library, model, CUDA component, or external utility.

## Base images and operating-system components

| Component | Declared version/source | Licensing notes |
|---|---|---|
| Ubuntu | 24.04 LTS | Distribution contains packages under multiple licenses; see [Ubuntu legal information](https://ubuntu.com/legal). |
| Python | 3.12 | Python Software Foundation License. |
| NVIDIA CUDA runtime (GPU image) | `nvidia/cuda:12.8.1-runtime-ubuntu24.04` | NVIDIA proprietary license terms; [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit). |
| cuDNN and other GPU libraries | Resolved through image/PyTorch dependencies | Versions and distribution obligations must be verified on the actual image. |
| FFmpeg | Installed by apt in both runtime images | License depends on the binary configuration and enabled codecs (LGPL/GPL possibilities). Verify the installed build. |
| ca-certificates | Installed by apt | Certificate bundle and distribution licensing must be reviewed per package. |
| git, compiler and development packages | Installed in builder stage only | May not be present in the final runtime image. |

**Image layouts:** The GPU and CPU Dockerfiles use multi-stage builds. The GPU runtime is based on NVIDIA CUDA 12.8.1; the CPU runtime uses Ubuntu 24.04 without an NVIDIA CUDA base image. Both run the application as an unprivileged user.

## Python dependencies declared in requirements.txt

These are **minimum constraints, not installed versions**. Installing without a lockfile may resolve newer releases.

| Package | Declared constraint | Usage | License verification |
|---|---|---|---|
| `torch` | `>=2.9.0` | Model inference | PyTorch license and version in resolved environment |
| `torchaudio` | `>=2.9.0` | Audio support | TorchAudio license and resolved version |
| `numpy` | `>=1.24.0` | Audio arrays | NumPy license |
| `PyYAML` | `>=6.0` | Announcement configuration | MIT |
| `soundfile` | `>=0.12.1` | WAV read/write | SoundFile license; check bundled/linked libsndfile |
| `fastapi` | `>=0.104.0` | REST API | FastAPI upstream license |
| `uvicorn` | `>=0.24.0` | ASGI server | Uvicorn upstream license |
| `pydantic` | `>=2.0.0` | Request validation | Pydantic upstream license |
| `pytest` | `>=9.1.0` | Test environment | Pytest upstream license |
| `pytest-cov` | `>=7.1.0` | Test coverage | pytest-cov upstream license |
| `httpx` | `>=0.27.0` | API tests (`TestClient`) | HTTPX upstream license |

**CPU wheel policy:** `docker/Dockerfile.cpu` first installs `torch` and `torchaudio` from `https://download.pytorch.org/whl/cpu` to avoid unnecessary CUDA dependencies. The GPU Dockerfile resolves its dependencies separately. Validate wheel/platform compatibility on the build host.

## Additional packages installed by Dockerfiles

| Package | Declared constraint | Purpose |
|---|---|---|
| `qwen-tts` | Unpinned; installed with `--no-deps` | Qwen3 TTS library |
| `transformers` | `==4.57.3` | Model implementation |
| `accelerate` | `==1.12.0` | Device/model loading |
| `gradio` | Unpinned | Upstream model/demo dependency |
| `librosa` | Unpinned | Audio processing |
| `onnxruntime` | Unpinned | Runtime dependency |
| `einops` | Unpinned | Tensor operations |
| `sox` | Unpinned Python package | Audio utility integration; distinct from the system `sox` executable |

The Dockerfiles install `qwen-tts` with `--no-deps` and list additional dependencies explicitly to avoid overwriting the selected PyTorch/TorchAudio pair. The full transitive package tree must be captured from a built environment.

## Qwen3-TTS model artifacts

| Model repository | Typical use | License notice |
|---|---|---|
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | Voice audition with named presets | Check the model repository's license and applicable use conditions. |
| `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | Voice audition and reference creation | Check the model repository's license and applicable use conditions. |
| `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | Production voice cloning | Check the model repository's license and applicable use conditions. |

The original project inventory identified Apache-2.0 for the Qwen3 models. **Verify the actual model-card license** when distributing models or a pre-populated cache. Model weights are downloaded into `data/hf-cache/` when required; their presence and exact revision are not recorded here.

## Project-owned files

| File or path | Role | License |
|---|---|---|
| `herold/audition.py` | Voice audition and reference generation | Project MIT |
| `herold/render.py` | Bilingual WAV synthesis | Project MIT |
| `herold/convert.py` | AAC/MP3 conversion | Project MIT |
| `herold/api.py` and `herold/static/index.html` | REST API and demo interface | Project MIT |
| `docker/Dockerfile*`, `docker-compose.yml` | Container build and orchestration | Project MIT; base images and contents remain separately licensed |
| `resources/ansagen.yaml` | Example input data (EN and DE speech) | Treat included text as project data; review permission before reuse in other contexts |
| `data/audition/reference_design_de.wav` | Signature voice sample required for cloning | The MIT license on code does not by itself establish consent or rights for reusing a recorded voice; review the reference recording's provenance before redistribution |

## Licensing and redistribution considerations

- **MIT does not mean zero obligations:** the project license includes copyright and license notice preservation. Apache-2.0 and other licenses may impose additional notice or redistribution conditions.
- **GPL/LGPL require specific review:** do not assume that including FFmpeg, SoX, libsndfile, or other binaries in a container has no copyleft or source-distribution obligations. Requirements depend on the exact binaries, codecs, linking, modifications, and how the container is distributed.
- **NVIDIA components remain proprietary:** using the toolkit may be allowed under its license, but redistribution and deployment rights are governed by NVIDIA's terms.
- **Third-party dependency and model licenses are independent:** verify current licenses and model cards, rather than treating this document as a legal determination.
- **Runtime security:** update and scan images periodically. The CI Trivy job was initially configured as report-only; a passing pipeline does not establish that the image is vulnerability-free.

## Generating a reproducible release SBOM

For a publishable container release, build the exact GPU/CPU images, freeze installed package versions, and generate a standard CycloneDX or SPDX SBOM for **each** image. Attach it to the corresponding GitHub Release or link it from the release notes. The source inventory in `SBOM.csv` is only a starting point and should not be relabeled as an SPDX or CycloneDX document.

---

This documentation is maintained under the Herold-TTS project's MIT license. It is an informational inventory, not legal advice or a substitute for reviewing upstream licenses.

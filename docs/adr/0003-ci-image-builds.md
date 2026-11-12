# ADR 0003: Build images on self-hosted GitLab runners; retain only two versions

**Status:** Accepted (2026-08-03)

## Context

Docker images had previously been built manually on the target machine. Two observations on 2026-08-03 argued against this approach: the development Mac (8 GB RAM) is not suitable for image builds (swapping, system hangs, interrupted builds; see the v0.4.0 AAR addendum), and the test machine should test rather than build. Self-hosted GitLab runners are available (Docker executor with access to the host Docker socket, Internet access, no restrictive runner policies). Container registry retention was also unresolved: the GPU images occupy about 15 GB (CUDA runtime base plus PyTorch CUDA stack). They should not accumulate indefinitely. The requirement is to retain only the current and preceding version.

## Decision

1. **Run `.gitlab-ci.yml` on self-hosted runners:**
   - `test`: run pytest on every branch push (`python:3.12-slim`, CPU-only PyTorch wheels, mocked model; no GPU required).
   - `build`: on `main`, build and push both GPU and CPU images to `<registry>/herold-tts/{gpu,cpu}:<version>` (version from `herold/__init__.py`) and `latest`. Using the host Docker socket provides a reusable image-layer cache, reducing subsequent build times when dependencies are unchanged.
   - `cleanup`: use the bulk-delete API with `keep_n=2` to retain only the two newest version tags per image repository while keeping `latest`.
2. **Target machines pull prebuilt images** (`docker pull …:latest` or a version tag) rather than building locally. Local builds remain documented as a fallback.

## Consequences

- Registry usage is bounded (approximately 2 × 15 GB GPU plus 2 × 3.5 GB CPU, with `latest` references).
- Cleanup needs a Project Access Token with `api` scope in `REGISTRY_CLEANUP_TOKEN`. Token expiration requires maintenance. The bulk-delete API is limited to one call per hour per repository, so the cleanup job uses `allow_failure`.
- GPU end-to-end validation remains manual on the test machine because no runner has a Blackwell GPU. CI verifies unit tests and image builds, not real speech synthesis.
- Image layers accumulate in the runner host's Docker daemon. Periodic `docker image prune` is an operator responsibility, intentionally not automated for a shared daemon.
- Older image versions may be irretrievable after cleanup. Rebuild them from `git checkout <tag>` if necessary.

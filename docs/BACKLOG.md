# Backlog

Open items across all work packages, consolidated from the AARs where the rationale is recorded. Remove completed tasks and document results in the changelog or an AAR.

## Open

- [ ] **Complete GPU/CPU end-to-end validation on Hive:** the acceptance checklist with checkboxes and measurements is in [`docs/abnahme/v0.4.3.md`](abnahme/v0.4.3.md). Execute it and record the results. Historical note: the v0.4.2 attempt failed with `[Errno 5]` during model loading; see troubleshooting in `docs/DEPLOYMENT.md`.
- [ ] **Update `HARDWARE.md`:** reported image sizes are outdated. The v0.4.1 CPU image is substantially smaller without the unnecessary CUDA libraries (previously documented at 9.8 GB). Measure current Hive images (`docker images`), VRAM, and v0.4.2 render times.
- [ ] **Verify registry access for the user account:** manual push/pull as `sorb` returned `denied`, while CI could push. Replacing the token fixed pull access; verify the push round trip with a small test image, or check the project role (Developer or higher required for pushing).
- [ ] **Monitor the `cleanup-registry` job:** GitLab's rate limit can cause failures when runs are less than one hour apart (intentional `allow_failure`). Verify that less frequent runs actually delete old tags, retaining the current and previous versions.
- [ ] **Add Ruff as a code-quality job** (step ③ from 2026-08-07): use `--output-format=gitlab` with `artifacts:reports:codequality`, after configuring Ruff and addressing the initial findings. The repository currently has no lint configuration.
- [ ] **Review the Trivy baseline:** inspect the first `container-scan` report, then decide whether to change the job from report-only to blocking (`--exit-code 1`).
- [ ] **Refresh SBOM:** `SBOM.md`/`SBOM.csv` date from June, omit `httpx` (test dependency added in v0.4.0), and contain outdated torch versions. Reconcile with `requirements.txt` and both Dockerfiles.
- [ ] **Replace `on_event` with FastAPI lifespan handlers** in `herold/api.py` to address deprecation warnings.
- [ ] **Report partial render failures accurately:** `render_batch` continues after per-item exceptions, so the API can report `done` despite failed announcements. Include per-item results or a failure count in job status (observed in mocked runs on 2026-08-04).
- [ ] **Consider slimming the GPU image (optional):** test `ubuntu:24.04` instead of a CUDA-runtime base, given that PyTorch bundles CUDA libraries. Potential savings are approximately 4 GB, but this must be validated on Hive and documented in an ADR because it changes the tested image.
- [ ] **Persistent job queue:** only when multi-instance operation is required (ADR 0002).
- [ ] **Devcontainer:** deferred by decision on 2026-08-03; reassess if a second developer joins or CI needs expand.

## Completed (reference)

- [x] CI pipeline with registry publishing and retention of two image versions (v0.4.2, ADR 0003).
- [x] Traefik `readTimeout` fix on Overmind for large registry layer pushes (2026-08-03 AAR, addendum 2026-08-04).
- [x] Hugging Face cache volume (v0.3.5); smaller CPU image and HTTP health check (v0.4.1).

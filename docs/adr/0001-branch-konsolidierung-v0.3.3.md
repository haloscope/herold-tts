# ADR 0001: Adopt v0.3.3 by copying files rather than merging; keep the signature voice in Git

**Status:** Accepted (2026-08-03)

## Context

The `patch-03520` branch contained the v0.3.3 state verified on the test machine (WSL/Debian, RTX 5090), but its ZIP-based transfer introduced Git hygiene problems: deleted `.gitignore`/`.dockerignore` files, approximately 30 committed runtime artifacts in `data/`, `tests/__pycache__`, and a 13 MB transfer ZIP in intermediate commit `2ecb921`. Merging would have permanently incorporated these artifacts into `main` history. At the same time, the signature voice (`reference_design_de.wav`) existed only on the test machine and in that branch. It was ignored on `main`, preventing reproducible builds from the repository alone.

## Decision

1. **Do not merge.** Copy the relevant paths (`docker/`, `docker-compose.yml`, `herold/api.py`, `herold/__init__.py`, `CHANGELOG.md`, `docs/`) with `git checkout origin/patch-03520 -- <paths>` into `main`, then commit the clean file snapshots.
2. Preserve the previous `main` state (v0.3.0) in `backup/main-v0.3.0`; delete `patch-03520` after pushing the consolidated changes.
3. **Commit the signature voice `data/audition/reference_design_de.wav` deliberately**, using an explicit `.gitignore` exception. Every VoiceClone render depends on this reference and it must remain available. Continue ignoring all other runtime outputs in `data/`.

## Consequences

- `main` history remains free of binary runtime artifacts and the transfer ZIP; clones stay small.
- The granular history from the test environment (v0.3.1 → v0.3.2 → v0.3.3) is lost. This is accepted because the changelog documents the individual fixes and their rationale.
- Audio rendering can be reproduced from the repository (voice reference, `ansagen.yaml`, and Docker).
- After deleting the transfer branch, generated files from `data/renders/` and `data/final/` remain only on the test machine.

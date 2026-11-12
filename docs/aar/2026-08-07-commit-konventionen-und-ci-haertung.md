# AAR 2026-08-07: Commit conventions (history rewrite) and CI hardening

## Objective

(1) Standardize commits with factual English messages and remove timestamps that reveal individual working patterns; (2) extend CI with security and quality checks.

## What happened

- **History rewrite (ADR 0004):** rewrote all 59 commits from both branches using `git filter-repo`: eight German messages translated, informal messages clarified based on actual changes, and all timestamps normalized to 12:00 UTC on their original dates. Deliberately rejected moving timestamps "outside working hours" as fabrication. Verified identical file contents (tree hashes) and kept a local pre-rewrite bundle.
- **Force push:** temporarily enabled “Allowed to force push” on protected `main`. GitLab initially rejected the push with `pre-receive hook declined` as expected.
- **CI hardening (v0.4.3):** restored SAST and secret detection templates that disappeared with the old pipeline during the 2026-07-06 restructure, added JUnit reports and Trivy container scans (report-only, since GitLab's official container-scanning template is Ultimate-only). Deliberately did not restore automated changelog generation: the changelog has been manually curated since v0.3.x.
- **Commit-time convention automation:** built and tested a post-commit hook and a CI guard but **rejected them by decision**. Instead, use environment variables for each commit (see CLAUDE.md) and aliases on working machines; occasional exceptions are accepted (for example commit `5708067` with its real timestamp).

## Lessons learned

- Protected branches block force pushes server-side. Enable “Allowed to force push” only temporarily for a history rewrite and disable it again immediately afterward.
- `git filter-repo` intentionally removes the `origin` remote. Restore it after rewriting. Comparing tree hashes before and after is a reliable content verification.
- Newer Git versions render UTC with `Z` instead of `+00:00` in `%aI`. Timestamp validators must accept both formats; this is why the rejected CI guard initially needed a correction.
- Old server-side objects with original timestamps can survive until housekeeping/GC. Pipeline keep-around refs can retain them. Complete removal may require deleting pipeline records (Delete on the pipeline detail page, not the list), then “Prune unreachable objects” in Settings → General → Advanced, possibly repeating after 24 hours.

## Open items

Tracked centrally in `docs/BACKLOG.md`, particularly v0.4.3 acceptance tests (`docs/abnahme/v0.4.3.md`), reviewing the Trivy baseline, the Ruff lint step, and SBOM updates.

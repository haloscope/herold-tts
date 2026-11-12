# ADR 0004: English commit conventions and timestamp normalization to 12:00 UTC

**Status:** Accepted (2026-08-07)

## Context

The commit history contained both German and English messages and precise timestamps from which individual working patterns could be inferred (daily schedules and working hours). To limit this disclosure before a possible public release or broader repository access, the team evaluated timestamp normalization. Deliberately moving commit times *outside* ordinary working hours was rejected because it would create a misleading account of when the work occurred. The chosen approach instead uses an obviously synthetic, neutral timestamp.

## Decision

1. **Use factual English Conventional Commit messages** (`feat:`, `fix:`, `docs:`, `chore:`). A history rewrite translated German messages and replaced informal messages (for example “late commit :D”, “readme”, and “housekeeping”) with precise descriptions of the corresponding changes.
2. **Normalize timestamps:** set both author and committer dates on every commit to **12:00:00 UTC on the original local commit date**. The calendar date is preserved, and every commit uses the same clearly synthetic time.
3. **Apply retrospectively and going forward:** rewrite all branches with `git filter-repo` on 2026-08-07. Future commits should use `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` set to `<today>T12:00:00Z` (see `CLAUDE.md`).

## Consequences

- **All commit hashes changed.** Hashes in older AAR and changelog entries refer to the pre-rewrite history and should be read as historical references rather than resolvable current commits.
- Existing clones require a one-time synchronization: `git fetch origin && git reset --hard origin/main` (destructive to uncommitted local changes).
- Old objects containing original timestamps may remain on GitLab until housekeeping/garbage collection or in pipeline keep-around refs. Full removal requires server-side cleanup. The rewrite primarily protects future readers.
- A local backup of the pre-rewrite history was stored outside the repository at `~/herold/herold-tts-pre-rewrite-*.bundle` and may be deleted after verification.
- Commits on the same day have identical timestamps. Their ordering remains defined by the Git graph, not the clock.

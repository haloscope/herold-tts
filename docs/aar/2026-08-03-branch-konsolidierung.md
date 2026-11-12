# AAR 2026-08-03: Branch consolidation v0.3.0 → v0.3.4

## Objective

Compare two divergent states (`main` v0.3.0, clean but unusable; `patch-03520` v0.3.3, tested but containing unwanted Git artifacts) and consolidate them into a clean, functional `main`. Additional goals: establish `CLAUDE.md` for Claude Code and preserve the signature voice.

## What happened

- Evaluated both branches and chose to copy selected files instead of merging; see [ADR 0001](../adr/0001-branch-konsolidierung-v0.3.3.md).
- Created `backup/main-v0.3.0`, then made four commits on `main`: v0.3.3 adoption (`d6fcede`); signature voice with a `.gitignore` exception (`cbee4ce`); v0.3.4 documentation combining the `CLAUDE.md` drafts and correcting README service names (`b07d313`); and removal of tracked `tests/__pycache__` (`a31a9af`).
- Initially, pushing and deleting `patch-03520` failed because macOS mDNSResponder retained a negative DNS cache entry for `git.lab` from before VPN connection. Direct DNS queries and port 443 worked, but the system resolver did not. Resolved using `sudo killall -HUP mDNSResponder`. GitLab was reachable on ports 443 (HTTPS) and 53 (DNS), so the remote was left on HTTPS rather than SSH.

## Lessons learned

- Transferring ZIPs from the test environment can damage Git hygiene (missing dotfiles, committed build outputs). Prefer committing and pushing a feature branch directly from the test machine.
- `tests/__pycache__` had been tracked since `9c9b0c0`. `.gitignore` does not affect already tracked files. Check `git ls-files` when changing ignore rules.
- Missing operational history becomes expensive later: the fact that v0.1.0 had generated the first production announcements on the test machine had never been recorded. ADR/AAR documentation is therefore mandatory going forward (CLAUDE.md, guideline 5).

## Follow-up items

- [x] `git push origin main backup/main-v0.3.0` — completed 2026-08-03 after resetting mDNSResponder.
- [x] `git push origin --delete patch-03520` — completed 2026-08-03.
- [x] Persist Hugging Face cache in `docker-compose.yml` — completed in v0.3.5 on 2026-08-03 (`./data/hf-cache` → `HF_HOME`); still not verified on the test machine at that time.

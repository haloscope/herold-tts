# AAR 2026-08-03: Branch-Konsolidierung v0.3.0 → v0.3.4

## Ziel

Die beiden divergierenden Stände (`main` v0.3.0, unbenutzbar aber sauber; `patch-03520` v0.3.3,
getestet aber git-hygienisch belastet) bewerten und zu einem sauberen, lauffähigen `main`
zusammenführen. Nebenziele: CLAUDE.md für Claude Code etablieren, Signature-Stimme sichern.

## Was geschah

- Bewertung beider Branches; Entscheidung Datei-Übernahme statt Merge → [ADR 0001](../adr/0001-branch-konsolidierung-v0.3.3.md)
- `backup/main-v0.3.0` angelegt, dann 4 Commits auf `main`:
  v0.3.3-Übernahme (`d6fcede`), Signature-Stimme mit gitignore-Ausnahme (`cbee4ce`),
  v0.3.4-Doku inkl. gemergter CLAUDE.md und README-Servicenamen-Fixes (`b07d313`),
  `tests/__pycache__` enttrackt (`a31a9af`)
- Push + Löschung von `patch-03520` zunächst an DNS gescheitert (`git.lab` nicht auflösbar);
  Hinweis: das GitLab ist nur über Port 443 (HTTPS) und 53 (DNS) erreichbar

## Gelernt

- Der Zip-Transfer-Workflow aus der Testumgebung erzeugt zuverlässig Git-Hygiene-Schäden
  (gelöschte Dotfiles, committete Artefakte). Künftig besser: auf der Testmaschine direkt auf
  einem Feature-Branch committen und pushen statt Zip entpacken.
- `tests/__pycache__` war seit `9c9b0c0` getrackt — `.gitignore` wirkt nicht auf bereits
  getrackte Dateien; bei neuen Ignore-Regeln immer `git ls-files` gegenprüfen.
- Undokumentierte Betriebshistorie fällt später auf die Füße: dass v0.1.0 auf der Testmaschine
  produktiv erste Ansagen erzeugte, war nirgends festgehalten → daher ab jetzt ADR/AAR-Pflicht
  (CLAUDE.md, Guideline 5).

## Offene Punkte

- [ ] `git push origin main backup/main-v0.3.0` (scheiterte an DNS; Netz/VPN nötig)
- [ ] `git push origin --delete patch-03520` (erst nach erfolgreichem Push von `main`)
- [ ] Optional: HF-Cache-Volume in `docker-compose.yml` (siehe docs/HARDWARE.md), um
      3.8–11 GB Re-Downloads nach Image-Rebuilds zu vermeiden

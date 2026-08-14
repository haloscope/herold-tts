# AAR 2026-08-07: Commit-Konventionen (History-Rewrite) & CI-Härtung

## Ziel

(1) Commit-Historie vereinheitlichen: englisch-sachliche Messages und keine ableitbaren
Arbeitszeitmuster (Privatsphäre); (2) Pipeline um Security- und Qualitäts-Checks erweitern.

## Was geschah

- **History-Rewrite (ADR 0004):** alle 59 Commits beider Branches per `git filter-repo`
  umgeschrieben — 8 deutsche Messages übersetzt, saloppe präzisiert (anhand des realen
  Commit-Inhalts), alle Zeitstempel auf 12:00 UTC des jeweiligen Datums normalisiert.
  Bewusst verworfen: Verschieben der Zeiten „außerhalb der Arbeitszeit" (wäre Fälschung).
  Inhalte bit-identisch (Tree-Hashes verifiziert). Vor-Rewrite-Backup als lokales Bundle.
- **Force-Push** erforderte temporäres „Allowed to force push" auf dem Protected Branch
  `main` (GitLab lehnte sonst mit `pre-receive hook declined` ab — Schutz funktionierte).
- **CI-Härtung (v0.4.3):** SAST + Secret Detection (GitLab-Templates, waren seit dem
  Restrukturierungs-Commit 2026-07-06 mitsamt der alten CI verschwunden), JUnit-Testreport,
  Trivy-Container-CVE-Scan (report-only; GitLabs offizielles Template ist Ultimate-only).
  Automatische Changelog-Generierung der alten CI bewusst nicht reaktiviert (manuell
  kuratiertes CHANGELOG seit v0.3.x).
- **Automatisierung der Zeitstempel-Konvention** (post-commit-Hook + CI-Wächter) wurde
  gebaut, getestet und auf Nutzerentscheid **verworfen** — pragmatische Regel stattdessen:
  Env-Variablen bei jedem Commit (CLAUDE.md), Alias auf den Arbeitsmaschinen, einzelne
  Ausreißer werden toleriert (z. B. Commit `5708067` mit echtem Zeitstempel).

## Gelernt

- Protected Branches blocken Force-Pushes serverseitig — für History-Rewrites den
  „Allowed to force push"-Schalter temporär setzen und **danach wieder deaktivieren**.
- `git filter-repo` löscht das `origin`-Remote absichtlich; nach dem Rewrite Remote neu
  anbinden. Tree-Hash-Vergleich vorher/nachher ist die schnellste Inhalts-Verifikation.
- Neuere git-Versionen rendern UTC in `%aI` als `Z` statt `+00:00` — Format-Prüfungen auf
  Zeitstempel müssen beide Varianten akzeptieren (Grund, warum der verworfene CI-Wächter
  vor einem Merge einen Fix gebraucht hätte).
- Alte Server-Objekte (echte Zeitstempel) überleben den Rewrite bis Housekeeping/GC;
  Pipelines pinnen sie über keep-around-Refs — volle Tilgung erfordert Pipeline-Löschung
  (Delete-Button auf der Pipeline-**Detailseite**, nicht in der Liste) + „Prune unreachable
  objects" (Settings → General → Advanced), ggf. mit 24-h-Wiederholung.

## Offene Punkte

→ zentral in docs/BACKLOG.md gepflegt; aus diesem Block insbesondere: Abnahme v0.4.3
(docs/abnahme/v0.4.3.md), Trivy-Baseline sichten, ruff-Schritt, SBOM-Aktualisierung.

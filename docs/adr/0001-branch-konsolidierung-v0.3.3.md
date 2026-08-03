# ADR 0001: Übernahme von v0.3.3 per Datei-Übernahme statt Merge; Signature-Stimme im Repo

**Status:** Akzeptiert (2026-08-03)

## Kontext

Der Branch `patch-03520` enthielt den auf der Testmaschine (WSL/Debian, RTX 5090) verifizierten
Stand v0.3.3, war aber durch den Zip-Transfer aus der Testumgebung belastet: gelöschte
`.gitignore`/`.dockerignore`, ~30 committete Runtime-Artefakte (`data/`), `tests/__pycache__`
sowie ein 13-MB-Transfer-Zip im Zwischencommit `2ecb921`. Ein Merge hätte all das dauerhaft in
die `main`-Historie übernommen. Gleichzeitig existierte die Signature-Stimme
(`reference_design_de.wav`) nur auf der Testmaschine und im Branch — auf `main` war sie
gitignored und damit nicht reproduzierbar gesichert.

## Entscheidung

1. **Kein Merge.** Die Datei-Stände der relevanten Pfade (`docker/`, `docker-compose.yml`,
   `herold/api.py`, `herold/__init__.py`, `CHANGELOG.md`, `docs/`) wurden per
   `git checkout origin/patch-03520 -- <pfade>` auf `main` übernommen und neu committet.
2. Der alte `main`-Stand (v0.3.0) wurde als Branch `backup/main-v0.3.0` gesichert;
   `patch-03520` wird nach dem Push gelöscht.
3. **Die Signature-Stimme `data/audition/reference_design_de.wav` wird bewusst committet**
   (`.gitignore`-Ausnahme). Sie ist die VoiceClone-Referenz, von der jedes Rendering abhängt,
   und muss dauerhaft erhalten bleiben. Alle übrigen `data/`-Outputs bleiben ignoriert.

## Konsequenzen

- `main`-Historie bleibt frei von Binär-Artefakten und dem Transfer-Zip; `git clone` bleibt schlank.
- Die granulare Commit-Historie der Testumgebung (v0.3.1→v0.3.2→v0.3.3) geht verloren —
  akzeptiert, da das CHANGELOG die Fixes einzeln und begründet dokumentiert.
- Renderings sind aus dem Repo allein reproduzierbar (Referenzstimme + `ansagen.yaml` + Docker).
- Fertige Render-Artefakte aus dem Branch (`data/renders`, `data/final`) liegen nach der
  Branch-Löschung nur noch auf der Testmaschine.

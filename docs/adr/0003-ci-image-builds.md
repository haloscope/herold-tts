# ADR 0003: Image-Builds auf eigenen GitLab-Runnern; Registry behält nur zwei Versionen

**Status:** Akzeptiert (2026-08-03)

## Kontext

Die Docker-Images wurden bisher manuell auf der Zielmaschine gebaut. Zwei Erfahrungen vom
2026-08-03 sprechen dagegen: Der Entwicklungs-Mac (8 GB RAM) ist für Builds ungeeignet
(Swapping, System-Hänger, Abbrüche — siehe AAR v0.4.0-Nachtrag), und die Testmaschine soll
testen, nicht bauen. Es existieren eigene GitLab-Runner (Docker-Executor mit durchgereichtem
Docker-Socket, Internetzugang, keine Policy-Beschränkungen). Zu klären war außerdem die
Registry-Aufbewahrung: GPU-Images sind ~15 GB (CUDA-Runtime-Base + torch-CUDA-Stack), sollen
also nicht unbegrenzt akkumulieren; Vorgabe des Nutzers: nur aktuelle + Vorgänger-Version.

## Entscheidung

1. **CI-Pipeline (`.gitlab-ci.yml`) auf den eigenen Runnern:**
   - Stage `test`: pytest bei jedem Branch-Push (python:3.12-slim, torch aus dem CPU-Wheel-Index,
     Modell gemockt — schnell und ohne GPU).
   - Stage `build`: GPU- und CPU-Image nur auf `main`, getaggt als
     `<registry>/herold-tts/{gpu,cpu}:<version>` (Version aus `herold/__init__.py`) plus `latest`,
     Push in die GitLab Container Registry. Der Socket-Executor nutzt den Layer-Cache des
     Runner-Hosts — Folgebuilds ohne Dependency-Änderung laufen in Minuten.
   - Stage `cleanup`: Bulk-Delete-API mit `keep_n=2` löscht pro Image-Repository alle
     Versions-Tags außer den zwei neuesten; `latest` bleibt.
2. **Die Zielmaschinen pullen künftig** (`docker pull …:latest` bzw. Versions-Tag) statt lokal
   zu bauen; lokales Bauen bleibt als Fallback dokumentiert.

## Konsequenzen

- Registry-Bedarf ist gedeckelt (~2×15 GB GPU + 2×3,5 GB CPU plus latest-Referenzen).
- Der Cleanup-Job braucht ein Project Access Token (Scope `api`) als CI-Variable
  `REGISTRY_CLEANUP_TOKEN` — Token-Ablauf ist ein Wartungspunkt. Die Bulk-Delete-API ist auf
  1 Aufruf/Stunde/Repository gedrosselt; der Job ist deshalb `allow_failure`.
- Der GPU-E2E-Test bleibt manuell auf der Testmaschine (kein Runner hat eine Blackwell-GPU) —
  CI verifiziert Bauen + Unit-Tests, nicht Rendern.
- Auf dem Runner-Host akkumulieren gebaute Images im lokalen Docker-Daemon; gelegentliches
  `docker image prune` auf dem Host ist Betreiber-Aufgabe (bewusst nicht automatisiert, da der
  Daemon geteilt ist).
- Alte Versions-Images sind nach dem Cleanup unwiederbringlich — Reproduktion notfalls über
  `git checkout <tag>` + Rebuild.

# Backlog

Offene Punkte über alle Arbeitsblöcke hinweg (konsolidiert aus den AARs; dort stehen die
Hintergründe). Erledigtes bitte streichen und im CHANGELOG bzw. AAR dokumentieren.

## Offen

- [ ] **GPU-E2E-Test auf Hive abschließen:** Render über die Demo-Seite (`http://hive:8000/`)
      mit v0.4.2 — zuletzt gescheitert mit `[Errno 5]` beim Modell-Load (Troubleshooting-Leitfaden:
      docs/DEPLOYMENT.md → „Errno 5"). Ursache auf Hive noch unklar (Platte/Cache/Hardware).
      Danach: Konvertierung, `healthy`-Check, HF-Cache-Persistenz (Rebuild ohne Re-Download)
- [ ] **HARDWARE.md aktualisieren:** Image-Größen sind veraltet — CPU-Image ist seit v0.4.1
      ohne CUDA-Ballast deutlich kleiner (dokumentiert: 9,8 GB). Neue Messwerte von Hive
      (`docker images`) eintragen; auch VRAM/Renderzeiten mit v0.4.2 gegenprüfen
- [ ] **Registry-Zugriff Nutzer-Account:** Push/Pull als `sorb` war `denied` (CI-Token pusht);
      Token-Tausch hat den Pull gefixt — Push-Roundtrip (hello-world) noch verifizieren,
      sonst Projekt-Rolle prüfen (Registry-Push braucht Developer+)
- [ ] **`cleanup-registry`-Job beobachten:** schlägt bei >1 Lauf/Stunde am GitLab-Rate-Limit
      fehl (gewollt, `allow_failure`) — prüfen, dass er bei ruhigem Pipeline-Takt wirklich
      löscht und nur aktuelle + Vorgänger-Version behält
- [ ] **`on_event` → Lifespan-Handler** in `herold/api.py` (FastAPI-Deprecation-Warnungen
      in der Testsuite)
- [ ] **Render-Job-Status ehrlicher machen:** `render_batch` schluckt Einzelfehler
      (`continue`), Job meldet `done` obwohl Ansagen fehlschlugen — Fehlerzähler/Items
      in den Job-Status aufnehmen (beobachtet beim Mock-Lauf 2026-08-04)
- [ ] **GPU-Image verschlanken (optional):** `ubuntu:24.04` statt CUDA-Runtime-Base prüfen —
      torch bringt seine CUDA-Libs selbst mit, potenziell ~4 GB Ersparnis; muss auf Hive
      verifiziert werden (ADR nötig, ändert getestetes Image)
- [ ] **Persistente Job-Queue** erst bei Multi-Instance-Bedarf (ADR 0002)
- [ ] **Devcontainer:** geklemmt (Entscheidung 2026-08-03); neu bewerten, wenn eine zweite
      Person aufs Repo kommt

## Erledigt (Referenz)

- [x] CI-Pipeline mit Registry-Push und keep-2-Cleanup (v0.4.2, ADR 0003)
- [x] Traefik-`readTimeout`-Fix auf Overmind — Registry-Pushes großer Layer (AAR 2026-08-03,
      Nachtrag 2026-08-04)
- [x] HF-Cache-Volume (v0.3.5), schlankes CPU-Image + HTTP-Healthcheck (v0.4.1)

# ADR 0002: Demo-Webservice als integrierte statische Seite; Job-Tracking in-memory

**Status:** Akzeptiert (2026-08-03)

## Kontext

Die Roadmap sieht nach CLI und REST-API einen exemplarischen Webservice vor, der zeigt, wie
man Herold-TTS nutzt. Die API v0.3.x war dafür unzureichend: Render/Convert liefen als
Fire-and-forget-Background-Tasks (202 ohne Job-Referenz), es gab weder einen Weg, Fertigstellung
oder Fehler zu erkennen, noch die erzeugten Audiodateien per HTTP abzurufen. Zur Auswahl standen
für die Demo: (a) statische HTML-Seite, ausgeliefert von der FastAPI-App selbst, (b) Gradio-UI
(bereits als qwen-tts-Abhängigkeit installiert), (c) separater Frontend-Container; fürs
Job-Tracking: In-Memory-Registry vs. reines Datei-Polling vs. persistente Queue.

## Entscheidung

1. **Demo als selbst-enthaltene statische Seite in der FastAPI-App** (`herold/static/index.html`,
   gemountet unter `/demo`, Root `/` leitet dorthin um). Ein Container, ein Port, keine
   CDN-Abhängigkeiten; die Seite nutzt ausschließlich die öffentliche REST-API und ist damit
   zugleich Integrations-Blaupause. Gradio verworfen (läuft an der API vorbei), separater
   Container verworfen (Mehraufwand ohne Demo-Nutzen).
2. **Job-Tracking als In-Memory-Registry** in `herold/api.py` (Dict + `threading.Lock`,
   `job_id` in der 202-Antwort, `GET /api/jobs/{id}`). Fehler aus `render_batch`/`batch_convert`
   werden als `failed` mit Fehlertext erfasst.
3. **Ergebnis-Zugriff über Datei-Endpoints** (`GET /api/files`, `GET /api/files/{dir}/{name}`),
   abgesichert durch Wiederverwendung von `convert.validate_filename_stem` plus
   Verzeichnis- und Extension-Whitelist.

## Konsequenzen

- Job-Status überlebt keinen Neustart und wird nicht zwischen Instanzen geteilt — für den
  Demo-/Single-Instance-Betrieb akzeptiert. Für Produktion mit mehreren Instanzen oder
  Restart-Garantien wäre eine persistente Queue (z. B. Redis) nötig → dann neues ADR.
- Kein Auth/Rate-Limiting: Die API ist für den Betrieb hinter einer vertrauenswürdigen
  Netzgrenze gedacht, nicht fürs offene Internet.
- Die Demo wird über die bestehenden `COPY herold/`-Zeilen der Dockerfiles automatisch
  mit ausgeliefert; kein zusätzlicher Build-Schritt.

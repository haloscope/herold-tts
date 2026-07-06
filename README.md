# Herold-TTS

Vorab gerenderte Telefon-/Voicemail-Ansagen in Deutsch und Englisch mit
**einer** konsistenten Stimme. Selbst-gehostet, MIT, kommerziell nutzbar.

Aktuell ist der Stack darauf ausgelegt eine NVIDIA Blackwell GPU für das Rendering der Audiofiles vorzusehen. Grundsätzlich sollte dies mit einer CPU oder anderen GPU gerendert werden können. Hierzu werden ggfs. Anpassungen erforderlich sein, wird sich aber in jedemfall auf die Renderzeit auswirken.

---

## Schnellstart — REST API

Starte den Service einfach mit Docker:

```bash
docker-compose up herold-tts-gpu
# oder: cd work && python api.py
```

Öffne http://localhost:8000/docs für interaktive API-Dokumentation (Swagger UI).

**Beispiel: Ansagen rendern**
```bash
curl -X POST http://localhost:8000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "ansagen": [{
      "id": "welcome",
      "text_de": "Willkommen!",
      "text_en": "Welcome!"
    }]
  }'
```

Mehr: [DEPLOYMENT.md](DEPLOYMENT.md)

---

## Warum dieser Stack? (Entscheidungslog)

| Frage | Optionen | Wahl + Begründung |
|---|---|---|
| Engine? | Kokoro / Piper / Chatterbox / **Qwen3-TTS** | Qwen3-TTS — einziges Modell, das *fertige Stimmen* **und** dieselbe Stimme über DE+EN **und** MIT (kommerziell) vereint. Kokoro: kein Deutsch. Piper: pro Sprache getrennte Stimmen. Chatterbox: braucht Referenzclip (war nicht vorhanden). |
| Modus? | CustomVoice / VoiceDesign / VoiceClone | Clone fällt raus (kein Sample). Audition testet **CustomVoice** (9 Presets) **und** **VoiceDesign** (Stimme per Text) gegeneinander. |
| Modellgröße? | 0.6B / **1.7B** | 1.7B — beste DE-Qualität; bei <10 Ansagen ist Renderzeit irrelevant. |
| Lizenz? | — | MIT → unbegrenzte kommerzielle Nutzung, keine Gebühren/Attribution. |
| Zielformat? | — | `.m4a` (AAC) + `.mp3` parallel, aus einem verlustfreien WAV-Master. |
| Multiversion? | Drei separate Renderings (EN, DE, EN+DE) / **Zwei Renderings + Kombination** | Zwei Synthesen pro Ansage (EN + DE), Multiversion (EN + 2s Pause + DE) wird kombiniert → **50% Render-Zeit-Ersparnis**. |

### Aufgefallen / Fallstricke
- **Blackwell (sm_120):** Benötigt CUDA **12.8+** und Blackwell-fähiges
  PyTorch (cu128). Ältere Images scheitern mit „no kernel image available".
- **Kein deutscher Native unter den 9 Presets:** Deutsch geht trotzdem; für deutschen Native-Klang nutzen wir **VoiceDesign**.
- **torch-Konflikt-Risiko (GELÖST):** `pip install qwen-tts` zieht inkompatible torchaudio nach. Lösung: torch + torchaudio als Paar aus cu128 instalieren.

---

## Setup (Schritt 1) - Docker Image erstellen und starten

```bash
# im Projektordner
docker compose build          # einmalig (zieht CUDA-Image + Torch + qwen-tts)
docker compose up -d
```

**Blackwell-Check direkt nach dem Build** (Pflicht):
```bash
docker compose exec qwen3-tts python -c \
  "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
# erwartet z.B.: 2.x.x+cu128 ... 12.8 ... NVIDIA GeForce XYZ
```

---

## Audition (Schritt 2) — Stimme auditieren

**Batch-Skript** (reproduzierbar, empfohlen)
```bash
docker compose exec qwen3-tts python /work/audition.py
# Ergebnis: ./audition/*.wav  (auf dem Host)
```

Erzeugt Samples für mehrere Preset-Stimmen und VoiceDesign-Beschreibungen.
→ Alle anhören, Favorit notieren.

---

## Sprachsynthese

Die Stimme wurde gewählt: **design_female_neutral via VoiceClone** (reference_design_de.wav).

### Schritt 3: ansagen.yaml editieren
Öffne `ansagen.yaml` und definiere deine Ansagen mit **separaten EN + DE Texten**:
```yaml
ansagen:
  - id: welcome
    text_en: "Hello, I'm delighted to welcome you to Oscar!..."
    text_de: "Hallo, ich freue mich Sie auf Oskar begrüßen zu dürfen!..."
  # Weitere Ansagen hier hinzufügen
```

### Schritt 4: Batch-Render (3 Versionen pro Ansage, aber nur 2 Synthesen!)
```bash
docker compose exec qwen3-tts python /work/render.py
```

Rendert für **jede Ansage automatisch 3 Versionen**:
- `<id>_en.wav` (nur Englisch)
- `<id>_de.wav` (nur Deutsch)  
- `<id>_multiversion.wav` (Englisch + 2s Pause + Deutsch)

**Render-Zeit-Ersparnis:** Die Multiversion wird aus EN+DE kombiniert (kein extra TTS-Rendering).

**Output:** `./renders/<id>_{en,de,multiversion}.wav` (24 kHz WAV-Master)

### Schritt 5: Konvertierung zu AAC + MP3
```bash
docker compose exec qwen3-tts python /work/convert.py
```

- Konvertiert **alle** WAV-Dateien (EN, DE, Multiversion)
- Loudness-Normalisierung (EBU R128: -23 LUFS)
- Beide Formate: `.m4a` (AAC) + `.mp3` (VBR ~192 kbps)

**Output:** `./final/<id>_{en,de,multiversion}.{m4a,mp3}`

Zugriff im Windows-Explorer:
```
\\wsl$\Debian\home\sorb\tts\work\final\
  ├── welcome_en.m4a / .mp3
  ├── welcome_de.m4a / .mp3
  ├── welcome_multiversion.m4a / .mp3
  └── ...
```

---

## Reproduzierbar von 0

1. Ordner mit Dateien anlegen:
   - `Dockerfile`, `docker-compose.yml`
   - `audition.py`, `render.py`, `convert.py`
   - `ansagen.yaml` (editieren!)

2. `docker compose build && docker compose up -d`

3. Blackwell-Check (oben)

4. **Audition** (optional): `docker compose exec qwen3-tts python /work/audition.py`

5. **Render**: `docker compose exec qwen3-tts python /work/render.py` → `renders/*.wav`

6. **Convert**: `docker compose exec qwen3-tts python /work/convert.py` → `final/*.m4a` + `final/*.mp3`

---

## Lizenzen & Compliance

Alle Komponenten unter permissiven Open-Source-Lizenzen. Siehe [SBOM.md](SBOM.md) für Details.

**Status:** ✅ Kommerziell nutzbar, keine Lizenzgebühren, keine Copyleft-Anforderungen (Projekt unter MIT).
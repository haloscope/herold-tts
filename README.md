# Qwen3-TTS Ansagen (DE + EN, eine Stimme)

Vorab gerenderte Telefon-/Voicemail-Ansagen in Deutsch und Englisch mit
**einer** konsistenten Stimme. Selbst-gehostet, Apache-2.0, kommerziell nutzbar.



## Warum dieser Stack? (Entscheidungslog)

| Frage | Optionen | Wahl + Begründung |
|---|---|---|
| Engine? | Kokoro / Piper / Chatterbox / **Qwen3-TTS** | Qwen3-TTS — einziges Modell, das *fertige Stimmen* **und** dieselbe Stimme über DE+EN **und** Apache-2.0 (kommerziell) vereint. Kokoro: kein Deutsch. Piper: pro Sprache getrennte Stimmen. Chatterbox: braucht Referenzclip (war nicht vorhanden). |
| Modus? | CustomVoice / VoiceDesign / VoiceClone | Clone fällt raus (kein Sample). Audition testet **CustomVoice** (9 Presets) **und** **VoiceDesign** (Stimme per Text) gegeneinander. |
| Modellgröße? | 0.6B / **1.7B** | 1.7B — beste DE-Qualität; bei <10 Ansagen ist Renderzeit irrelevant. |
| Lizenz? | — | Apache-2.0 → bezahlte Gigs unproblematisch (keine Gebühren/Attribution). |
| Zielformat? | — | `.m4a` (AAC) + `.mp3` parallel, aus einem verlustfreien WAV-Master. |

### Aufgefallen / Fallstricke
- **Blackwell (sm_120):** Benötigt CUDA **12.8+** und Blackwell-fähiges
  PyTorch (cu128). Ältere Images scheitern mit „no kernel image available".
  Deshalb Basis-Image `nvidia/cuda:12.8.1` + Torch von der cu128-Quelle.
- **Kein deutscher Native unter den 9 Presets** (5x CN, 2x EN, 1x JA, 1x KO).
  Deutsch geht trotzdem; für deutschen Native-Klang ohne Aufnahme ist
  **VoiceDesign** der bessere Hebel. Darum testet die Audition beides.
- **torch-Konflikt-Risiko (EINGETRETEN, gelöst):** `pip install qwen-tts`
  zieht `torchaudio` als Abhängigkeit nach — und zwar eine **CUDA-13**-Variante
  (`libcudart.so.13`), die nicht zur cu128-Torch (`libcudart.so.12`) passt →
  torchaudio crasht beim Laden. Lösung: `torch` **und** `torchaudio` als Paar
  aus der cu128-Quelle vorinstallieren, dann ist die Abhängigkeit erfüllt und
  qwen-tts zieht nichts Falsches nach. (Die `sox not found`-Warnung war nur
  Folgerauschen; SoX ist jetzt mit im Image.)

---

## Setup

```bash
# im Projektordner
docker compose build          # einmalig (zieht CUDA-Image + Torch + qwen-tts)
docker compose up -d
docker compose exec qwen3-tts bash
```

**Blackwell-Check direkt nach dem Build** (Pflicht, sonst rendert nichts):
```bash
docker compose exec qwen3-tts python -c \
  "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
# erwartet z.B.: 2.x.x+cu128 ... 12.8 ... NVIDIA GeForce RTX 5090
```
Zeigt das eine CPU-Torch oder cu124 → im Dockerfile bleibt die cu128-Zeile
maßgeblich; ggf. `pip install --force-reinstall torch --index-url
https://download.pytorch.org/whl/cu128` im Container nachschieben.

---

## Audition (Schritt 2) — Stimme wählen

**Variante 1: Batch-Skript** (reproduzierbar, empfohlen)
```bash
# audition.py liegt durch das ./work-Volume im Container unter /work
docker compose exec qwen3-tts python /work/audition.py
# Ergebnis: ./work/audition/*.wav  (auf dem Host)
```
Erzeugt denselben DE- und EN-Ansagesatz für mehrere Preset-Stimmen
(Ryan, Aiden, Serena, Uncle_Fu) und zwei VoiceDesign-Beschreibungen.
→ Alle anhören, Favorit notieren.

**Variante 2: Interaktives Web-UI** (zum freien Ausprobieren)
```bash
docker compose exec qwen3-tts \
  qwen-tts-demo Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --ip 0.0.0.0 --port 8000
# Browser: http://<homelab-ip>:8000
```

Der erste Lauf lädt die Modelle (~4,5 GB je 1.7B-Modell) in `./cache`.

---

## Phase 5, Schritt 3-5: Batch-Render + Konvertierung

Die Stimme wurde gewählt: **design_female_neutral via VoiceClone** (reference_design_de.wav).

### Schritt 3: ansagen.yaml editieren
Öffne `ansagen.yaml` und ergänze deine Ansagen (Vorlage schon drin):
```yaml
ansagen:
  - id: welcome_de
    sprache: German
    text: "Hallo, ich freue mich Sie auf Oskar begrüßen zu dürfen!..."
  - id: welcome_en
    sprache: English
    text: "Hello, I'm delighted to welcome you to Oscar!..."
  # Weitere Ansagen hier hinzufügen
```

### Schritt 4: Batch-Render (voice_clone_prompt erzeugen + rendernx)
```bash
docker compose exec qwen3-tts python /work/render.py
```
- Lädt `audition/reference_design_de.wav` (die Stimmen-Referenz)
- Erzeugt `voice_clone_prompt` (gespeichert in `voice_clone_prompt.json` für Reproduzierbarkeit)
- Rendert alle Ansagen aus `ansagen.yaml` mit der geclonten Stimme
- **Output:** `./renders/*.wav` (24 kHz WAV-Master, auf dem Host)

### Schritt 5: Konvertierung zu AAC + MP3
```bash
docker compose exec qwen3-tts python /work/convert.py
```
- Liest `./renders/*.wav`
- Normalisiert Loudness (EBU R128 Standard: -23 LUFS)
- Speichert beide Formate:
  - `./final/*.m4a` (AAC, 192 kbps)
  - `./final/*.mp3` (MP3, VBR ~192 kbps)
- **Output:** `./final/` auf dem Host

Zugriff auf die finalen Dateien im Windows-Explorer:
```
\\wsl$\Debian\home\sorb\tts\work\final\
  ├── welcome_de.m4a
  ├── welcome_de.mp3
  ├── welcome_en.m4a
  ├── welcome_en.mp3
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

4. **Audition** (optional, wenn Stimme neu wählen):
   ```bash
   docker compose exec qwen3-tts python /work/audition.py
   # -> audition/*.wav anhören, Stimme wählen
   ```

5. **Render**: `docker compose exec qwen3-tts python /work/render.py`
   → `renders/*.wav`

6. **Convert**: `docker compose exec qwen3-tts python /work/convert.py`
   → `final/*.m4a` + `final/*.mp3`

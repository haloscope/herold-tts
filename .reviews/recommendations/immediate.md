# Recommendations — Sofortige Maßnahmen (Nächster Sprint)

**Zielgruppe:** Dich und Team  
**Zeitrahmen:** 1-2 Tage Entwicklung + Test  
**Priorität:** Blocking für "Production Ready"

## 1. 🔴 Security Fixes (Blockers)

### 1.1 SEC-001: Path Traversal — convert.py

**Task:** Implementiere `validate_filename_stem()` mit Regex-Check

```python
# convert.py, nach imports:
import re

def validate_filename_stem(stem: str) -> str:
    """Allow only alphanumeric, underscore, hyphen."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', stem):
        raise ValueError(f"Invalid filename stem: {stem}")
    return stem

# In batch_convert(), Zeile 106-108:
for i, wav_path in enumerate(wav_files, 1):
    try:
        stem = validate_filename_stem(wav_path.stem)
    except ValueError as e:
        print(f"  [{i}/{len(wav_files)}] SKIP {wav_path.name}: {e}")
        continue
    # ... rest unchanged
```

**Test:** 
- `validate_filename_stem("welcome_en")` → OK
- `validate_filename_stem("../../../etc/passwd")` → ValueError ✓

**Review:** Code-Review erforderlich

---

### 1.2 SEC-002: Text DoS — render.py

**Task:** Validiere Text-Länge vor TTS

```python
# render.py, nach Imports:
MAX_TEXT_LENGTH = 5000  # Realistisch für 1-2 Min Audio

def validate_text(text: str) -> str:
    """Validate text length and type."""
    if not isinstance(text, str):
        raise TypeError(f"Expected string, got {type(text)}")
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text too long ({len(text)} > {MAX_TEXT_LENGTH} chars). "
            f"Approx {len(text) / 100:.0f} seconds of audio."
        )
    return text

# In render_batch(), Zeile 130-133:
for i, ansage in enumerate(ansagen_list, 1):
    ansage_id = ansage["id"]
    
    try:
        text_de = validate_text(ansage.get("text_de") or ansage.get("text"))
        text_en = validate_text(ansage.get("text_en"))
    except (ValueError, TypeError) as e:
        print(f"  [{i}/{len(ansagen_list)}] ⚠️ {ansage_id}: SKIP - {e}")
        continue
    
    # ... rest unchanged (Zeile 143+)
```

**Test:**
- Empty text → ValueError ✓
- 6 MB text → ValueError ✓
- 500 chars → OK ✓

**Review:** Security-Review erforderlich

---

### 1.3 VAL-001: YAML Schema Validation — render.py

**Task:** Validiere `ansagen.yaml` Struktur beim Load

```python
# render.py, nach Imports:
from dataclasses import dataclass

@dataclass
class AnsageEntry:
    id: str
    text_de: str
    text_en: str
    
    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError(f"Invalid id: {self.id}")
        if not self.text_de or not isinstance(self.text_de, str):
            raise ValueError(f"Invalid text_de for id={self.id}")
        if not self.text_en or not isinstance(self.text_en, str):
            raise ValueError(f"Invalid text_en for id={self.id}")

def load_yaml(path) -> list[AnsageEntry]:
    """Load and validate ansagen.yaml."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    ansagen = data.get("ansagen", [])
    if not ansagen:
        raise ValueError("No 'ansagen' section found in YAML")
    
    validated = []
    for i, entry in enumerate(ansagen):
        try:
            validated.append(AnsageEntry(**entry))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid ansage #{i}: {e}")
    
    return validated

# render_batch() braucht keine Änderung — validated Objekte haben guaranteed .id, .text_de, .text_en
```

**Test:**
- Missing `id` → ValueError mit Index
- Empty `text_en` → ValueError
- Valid Entry → AnsageEntry OK ✓

**Review:** Data Validation Review

---

## 2. 🟡 Error Handling & Operability

### 2.1 OPS-001: Full Error Output — convert.py

**Task:** Entferne stderr Truncation

```python
# convert.py, Zeile 62-64:
except subprocess.CalledProcessError as e:
    stderr = e.stderr.decode() if e.stderr else "(no stderr)"
    print(f"    ERROR (AAC): {stderr}")  # ← Full output
    return False

# Gleiches für convert_wav_to_mp3(), Zeile 82-84
except subprocess.CalledProcessError as e:
    stderr = e.stderr.decode() if e.stderr else "(no stderr)"
    print(f"    ERROR (MP3): {stderr}")  # ← Full output
    return False
```

**Test:** ffmpeg mit fehlender Datei → Error ist aussagekräftig ✓

---

## 3. 🟠 Portability

### 3.1 CONFIG-001: Device Auto-Detection — render.py & audition.py

**Task:** DEVICE hart-coding durch Environment-Variable + Auto-Detection ersetzen

```python
# render.py, nach Imports (Zeile 19-26):
import os

def get_device():
    """Detect device: prefer TTS_DEVICE env var, fallback to CUDA or CPU."""
    if "TTS_DEVICE" in os.environ:
        return os.environ["TTS_DEVICE"]
    return "cuda:0" if torch.cuda.is_available() else "cpu"

DEVICE = get_device()
print(f"[INFO] Using device: {DEVICE}")

# Entferne alte Hard-coded Zeile: DEVICE = "cuda:0"
```

**Gleiches für audition.py**

**Test:**
- Default (keine Env-Var) → cuda:0 wenn CUDA, sonst cpu ✓
- `TTS_DEVICE=cpu` → cpu ✓
- `TTS_DEVICE=cuda:1` → cuda:1 ✓

---

## 4. 📚 Documentation Quick-Win

### 4.1 README für `work/` Verzeichnis

**Task:** Erstelle `work/README.md` mit:
- Quick Start (welches Script zuerst?)
- Anforderungen (CUDA, Python, ffmpeg)
- Environment-Variablen (TTS_DEVICE, etc.)
- Common Errors & Fixes

**Template:**
```markdown
# Herold-TTS Work Scripts

## Quick Start
1. `python audition.py` → Wähle beste Stimme
2. `python render.py` → Generiere WAV Dateien
3. `python convert.py` → Konvertiere zu AAC + MP3

## Requirements
- Python 3.9+
- torch (pinned, siehe SBOM.csv)
- ffmpeg (apt install ffmpeg)
- CUDA 12.8 (für GPU) oder CPU-only

## Environment Variables
- `TTS_DEVICE=cuda:0` (default) oder `cuda:1`, `cpu`, etc.
- `AUDIO_BITRATE=192k` (AAC Bitrate, optional)

## Troubleshooting
...
```

---

## Sprint-Planung

| Task | Owner | Priority |
|------|-------|----------|
| SEC-001 Path Traversal | [Your] | 🔴 P0 |
| SEC-002 Text DoS | [Your] | 🔴 P0 |
| VAL-001 YAML Validation | [Your] | 🔴 P0 |
| OPS-001 Error Output | [Your] | 🟡 P1 |
| CONFIG-001 Device Auto | [Your] | 🟠 P2 |
| work/README.md | [Your] | 🟠 P2 |
| Code Review + Testing | [Reviewer] | - |

---

## Definition of Done

- [ ] Alle Code-Changes haben Tests
- [ ] `pytest` läuft mit 100% Pass-Rate
- [ ] Security-Tests bestätigen: Path Traversal + Text DoS nicht möglich
- [ ] work/README.md ist aktuell und getestet
- [ ] Keine Regressions in bestehenden Workflows
- [ ] SBOM.csv aktualisiert (wenn deps geändert)

---

**Nächster Schritt:** Code-Review dieser Findings mit dir before starting implementation.

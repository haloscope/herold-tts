# Security Review — Details

## 1. 🔴 Path Traversal in convert.py

**Location:** [convert.py:106-108](../../work/convert.py#L106-L108)

```python
for i, wav_path in enumerate(wav_files, 1):
    stem = wav_path.stem  # ← NICHT VALIDIERT
    aac_path = os.path.join(final_dir, f"{stem}.m4a")  # ← Könnte außerhalb gehen
    mp3_path = os.path.join(final_dir, f"{stem}.mp3")
```

**Problem:**
- `wav_path.stem` kann beliebig lange Strings enthalten
- Ein WAV-Dateiname wie `../../../etc/passwd_en.wav` würde erzeugt, wenn jemand die `renders/` Verzeichnis manipuliert
- `os.path.join(final_dir, "../../../etc/passwd.m4a")` normalisiert zu `final/../../../etc/passwd.m4a` → schreibt außerhalb

**Impact:** Datei-Write außerhalb des vorgesehenen Verzeichnisses (low bei lokaler Nutzung, aber schlecht für Prinzipien)

**Fix:**
```python
import re
def validate_stem(stem):
    if not re.match(r'^[a-zA-Z0-9_-]+$', stem):
        raise ValueError(f"Invalid filename: {stem}")
    return stem

stem = validate_stem(wav_path.stem)
```

---

## 2. 🔴 Unvalidierte Text-Länge in render.py

**Location:** [render.py:131-133](../../work/render.py#L131-L133)

```python
text_de = ansage.get("text_de") or ansage.get("text")
text_en = ansage.get("text_en")
# → Keine Längen-Prüfung
```

**Problem:**
- Ein YAML-Eintrag mit `text_de: "..." * 100000` (Megabyte-Text) könnte erzeugt werden
- TTS-Modell könnte hängenbleiben, CUDA-Memory exhausten, oder crashen
- Fehlgeschlagenes Rendering verursacht CPU-Spin oder unerwartete Fehler

**Impact:** Denial of Service (Hang/Crash bei großen Texten)

**Fix:**
```python
MAX_TEXT_LENGTH = 5000  # Zeichen
if len(text_de) > MAX_TEXT_LENGTH:
    raise ValueError(f"text_de exceeds {MAX_TEXT_LENGTH} chars")
if len(text_en) > MAX_TEXT_LENGTH:
    raise ValueError(f"text_en exceeds {MAX_TEXT_LENGTH} chars")
```

---

## 3. 🟡 Unvollständiges Error Logging in convert.py

**Location:** [convert.py:62-64, 82-84](../../work/convert.py#L62-L84)

```python
except subprocess.CalledProcessError as e:
    print(f"    ERROR (AAC): {e.stderr.decode()[:200]}")  # ← Gekürzt!
    return False
```

**Problem:**
- ffmpeg stderr wird auf 200 Zeichen gekürzt
- Bei komplexen Fehlern (fehlende Codec, Permission-Fehler) kann kritische Info verloren gehen
- Macht Debugging schwierig

**Fix:**
```python
except subprocess.CalledProcessError as e:
    err_msg = e.stderr.decode() if e.stderr else "No stderr"
    print(f"    ERROR (AAC): {err_msg}")
    # Oder: Logging zu Datei
```

---

## 4. 🟡 Hard-coded CUDA Device

**Location:** [render.py:32](../../work/render.py#L32), [audition.py:28](../../work/audition.py#L28), [convert.py: N/A]

```python
DEVICE = "cuda:0"  # ← Immer Device 0
```

**Problem:**
- Funktioniert nur mit Single-GPU oder wenn GPU 0 frei ist
- Auf CPU-only Systemen crashed es sofort
- Keine Fallback-Logik für CUDA-Fehler

**Impact:** Script nicht portabel zu CPU-Systemen oder Multi-GPU-Setups

**Fix:**
```python
import os
def get_device():
    if torch.cuda.is_available():
        device = os.environ.get("CUDA_DEVICE", "0")
        return f"cuda:{device}"
    return "cpu"

DEVICE = get_device()
```

---

## 5. 🟡 Keine YAML-Schema-Validierung

**Location:** [render.py:205-207](../../work/render.py#L205-L207)

```python
ansagen = load_yaml(ANSAGEN_FILE)
if not ansagen:
    raise ValueError("Keine Ansagen in ansagen.yaml gefunden!")
# ← Aber: Keine Prüfung auf fehlende/ungültige Felder
```

**Problem:**
- `load_yaml()` wirft nur ValueError wenn Liste leer ist
- Ein Eintrag ohne `id` oder `text_de`/`text_en` würde erst später crashen (bei render.py Zeile 131)
- Error-Message wäre unklar

**Impact:** Schlechte UX, verwirrende Error-Messages

**Fix:**
```python
from pydantic import BaseModel, ValidationError

class AnsageEntry(BaseModel):
    id: str
    text_de: str
    text_en: str

def load_and_validate_yaml(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    ansagen = data.get("ansagen", [])
    return [AnsageEntry(**entry) for entry in ansagen]
```

---

## Zusammenfassung

- **2 kritische Issues** müssen behoben werden (Path Traversal, Text-DoS)
- **3 mittlere Issues** können bei nächster Gelegenheit behoben werden
- **Keine Hinweise auf:** SQL-Injection, XSS, RCE, Credential-Leaks, Unencrypted Secrets

**Nächste Schritte:** Siehe `../recommendations/immediate.md`

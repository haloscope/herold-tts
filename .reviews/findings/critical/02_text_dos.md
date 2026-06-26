# CRITICAL: Unvalidated Text Length DoS

**ID:** SEC-002  
**Component:** render.py  
**Lines:** 131-133, 148-152, 164-168  
**Severity:** 🔴 CRITICAL  
**Category:** Security (Denial of Service)  

## Description

TTS-Text wird ohne Längenbeschränkung akzeptiert. Extrem lange Texte können TTS-Modell hangenbleiben, CUDA-Memory exhausten oder Crash verursachen.

## Details

```python
# Line 131-133
text_de = ansage.get("text_de") or ansage.get("text")
text_en = ansage.get("text_en")
# ← Keine Längenkontrolle

# Line 148-152
en_wavs, en_sr = model.generate_voice_clone(
    text=text_en,  # ← Könnte Megabytes sein!
    language="English",
    voice_clone_prompt=voice_clone_prompt,
)
```

**Angriffsvektor:**
```yaml
# ansagen.yaml
ansagen:
  - id: bomb
    text_en: "Hello " * 1000000  # 6+ MB Text
    text_de: "Hallo " * 1000000
```

## Impact

- TTS-Modell hängt (Infinite Loop / Extremely long inference)
- CUDA Memory Exhaustion → OOM Kill
- Gesamter Batch wird unterbrochen, weitere Ansagen verarbeitet nicht
- **DoS: HOCH** — Single malformed YAML kann ganze Pipeline lahmlegen

## Recommended Fix

```python
# Konstante oben definieren
MAX_TEXT_LENGTH = 5000  # Characters, realistisch für ~1-2 Min Audio

def validate_text(text):
    """Validiert Text-Länge und Encoding."""
    if not isinstance(text, str):
        raise TypeError(f"Expected string, got {type(text)}")
    if len(text) == 0:
        raise ValueError("Text cannot be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text exceeds max length ({len(text)} > {MAX_TEXT_LENGTH})")
    return text

# In render_batch(), für jede Ansage:
for i, ansage in enumerate(ansagen_list, 1):
    ansage_id = ansage["id"]
    try:
        text_de = validate_text(ansage.get("text_de") or ansage.get("text"))
        text_en = validate_text(ansage.get("text_en"))
    except ValueError as e:
        print(f"  SKIP [{i}/{len(ansagen_list)}] {ansage_id}: {e}")
        continue
    # ... rest of processing
```

## Acceptance Criteria

- [ ] Validation Funktion `validate_text()` implementiert
- [ ] MAX_TEXT_LENGTH = 5000 gesetzt (oder nach Tests angepasst)
- [ ] Unit-Test: Leerer Text → ValueError
- [ ] Unit-Test: 6 MB Text → ValueError
- [ ] Unit-Test: 500 Zeichen → OK
- [ ] Logging zeigt validierte Texte mit Länge

## Testing

```python
# tests/test_render.py
import pytest
from render import validate_text, MAX_TEXT_LENGTH

def test_validate_text_empty():
    with pytest.raises(ValueError):
        validate_text("")

def test_validate_text_too_long():
    with pytest.raises(ValueError):
        validate_text("x" * (MAX_TEXT_LENGTH + 1))

def test_validate_text_valid():
    text = "Hello, this is a normal test."
    assert validate_text(text) == text
```

## Priority

Blocking für Produktion

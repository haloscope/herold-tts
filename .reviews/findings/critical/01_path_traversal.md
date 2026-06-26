# CRITICAL: Path Traversal in convert.py

**ID:** SEC-001  
**Component:** convert.py  
**Lines:** 106-108  
**Severity:** 🔴 CRITICAL  
**Category:** Security  

## Description

Unsanitized file stems können zu Write-Operationen außerhalb des zielverzeichnisses führen.

## Details

```python
# Line 106-108
for i, wav_path in enumerate(wav_files, 1):
    stem = wav_path.stem  # ← NICHT VALIDIERT
    aac_path = os.path.join(final_dir, f"{stem}.m4a")  # ← Path Traversal
```

Ein manipulierter Dateiname wie `../../../etc/evil_en.wav` in `renders/` würde produzieren:
- AAC: `final/../../../etc/evil.m4a` → schreibt außerhalb

## Impact

- Dateien außerhalb des Zielverzeichnisses schreiben
- Potenzial: Konfigurationsdateien überschreiben
- **Lokales Risiko: MITTEL** (benötigt Zugriff auf renders/ Verzeichnis)
- **Produktionsrisiko: HOCH** (wenn automatische Datei-Upload-Pipeline)

## Recommended Fix

```python
import re

def validate_filename_stem(stem):
    """Erlaubt nur alphanumeric, underscore, hyphen."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', stem):
        raise ValueError(f"Invalid filename stem: {stem}")
    return stem

# In batch_convert():
for i, wav_path in enumerate(wav_files, 1):
    try:
        stem = validate_filename_stem(wav_path.stem)
    except ValueError as e:
        print(f"  SKIP {wav_path}: {e}")
        continue
    
    aac_path = os.path.join(final_dir, f"{stem}.m4a")
    mp3_path = os.path.join(final_dir, f"{stem}.mp3")
    # ...
```

## Acceptance Criteria

- [ ] Validation Funktion implementiert
- [ ] Unit-Test mit `../../../etc/passwd` bestätigt Ablehnung
- [ ] Unit-Test mit gültigen Namen (id_en, welcome_de) bestätigt Akzeptanz
- [ ] No regression in convert_batch()

## Priority

Blocking für Produktion

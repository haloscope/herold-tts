# Performance Review — Zusammenfassung

**Bewertungszeitraum:** 2026-06-26  
**Module:** render.py, convert.py, audition.py  
**Fokus:** GPU/CPU-Auslastung, I/O-Effizienz, Speicher

## Executive Summary

Die Performance ist für ein TTS-Tool angemessen, aber es gibt **3 Optimierungspotenziale**:
1. Parallelisierung in convert.py (ffmpeg-Calls können parallel laufen)
2. Ineffiziente Loudness-Messung (2x ffmpeg pro Datei)
3. Modell-Management könnte granularer sein

## Findings

### 🟡 HOCH: Fehlende Parallelisierung in convert.py

**Location:** [convert.py:105-123](../../work/convert.py#L105-L123)

```python
for i, wav_path in enumerate(wav_files, 1):
    # ... 
    # AAC conversion (blocking)
    convert_wav_to_aac(...)  
    # MP3 conversion (blocking) - WARTET auf AAC!
    convert_wav_to_mp3(...)
```

**Problem:**
- Beide ffmpeg-Prozesse laufen sequenziell
- Auf N WAV-Dateien: 2N ffmpeg-Calls hintereinander
- CPU sitzt idle während GPU/ffmpeg rechnet

**Impact:**
- ~2x Durchsatzreduktion möglich
- Auf 100 WAV-Dateien: ~10 Min statt ~20 Min

**Fix:** ThreadPoolExecutor (I/O-bound) oder ProcessPoolExecutor (CPU-bound)
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = []
    for wav_path in wav_files:
        f1 = pool.submit(convert_wav_to_aac, wav_path, ...)
        f2 = pool.submit(convert_wav_to_mp3, wav_path, ...)
        futures.extend([f1, f2])
    for f in as_completed(futures):
        f.result()  # Check exceptions
```

---

### 🟡 MITTEL: Ineffiziente Loudness-Messung

**Location:** [convert.py:47-69](../../work/convert.py#L47-L69)

```python
def convert_wav_to_aac(wav_path, output_path, ...):
    loudness_filter = get_loudness_filter(...)  # Pass 1: misst
    cmd = ["ffmpeg", "-i", wav_path, "-af", loudness_filter, ...]
    
def convert_wav_to_mp3(wav_path, output_path, ...):
    loudness_filter = get_loudness_filter(...)  # Pass 2: MISST NOCHMAL!
    cmd = ["ffmpeg", "-i", wav_path, "-af", loudness_filter, ...]
```

**Problem:**
- ffmpeg `loudnorm` Filter braucht 2 Pässe: Messung + Normalisierung
- Derzeit läuft AAC + MP3 = 2x vollständige Loudness-Messung
- Besser: 1x messen, 2x mit Parametern normalisieren

**Impact:**
- ~20-30% Zeit-Einsparung möglich pro Datei

**Fix:** Loudness auslesen und cachen
```python
def get_loudness_metadata(wav_path):
    # Nur messen, kein output
    cmd = ["ffmpeg", "-i", wav_path, "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True)
    # Parse JSON output → I, TP, LRA
    return {"I": ..., "TP": ..., "LRA": ...}

# Dann beide Formate mit den gleichen Parametern normalisieren
```

---

### 🟢 LOW: Suboptimales Modell-Management in audition.py

**Location:** [audition.py:77-100, 103-122](../../work/audition.py#L77-L122)

```python
def run_custom_voice():
    model = Qwen3TTSModel.from_pretrained(...)
    # Lade Model für JEDES Processing
    
def run_voice_design():
    model = Qwen3TTSModel.from_pretrained(...)  # NOCHMAL laden!
```

**Problem:**
- Jede Funktion lädt ihr Modell neu (auch wenn gleich)
- Modelle sind mehrere GB → waste von Time+VRAM
- Könnte mit Context Manager/Singleton optimiert werden

**Impact:**
- ~3-5 Min extra pro audition.py Run (gering, da nur bei Audition)

**Fix:** Model caching oder Single-Load-Wrapper
```python
_models = {}

def get_model(name):
    if name not in _models:
        _models[name] = Qwen3TTSModel.from_pretrained(name, ...)
    return _models[name]
```

---

## Zusammenfassung

| Opportunity | Severity | Speedup | Effort |
|-------------|----------|---------|--------|
| Parallelisierung convert.py | Hoch | ~2x | Mittel |
| Loudness-Caching | Mittel | ~1.3x | Mittel |
| Model-Caching audition | Low | ~1.2x (audition only) | Low |

**Gesamtpotenzial:** ~20-30% weniger Runtime mit parallelisierter + gecachter Loudness

---

**Details:** Siehe `details.md`  
**Recommendations:** Siehe `../recommendations/future.md`

# Recommendations — Längerfristige Verbesserungen (Q3 2026+)

**Zielgruppe:** Produkt-Roadmap  
**Anmerkung:** Nur durchführen, wenn Immediate-Fixes abgeschlossen sind

---

## Phase 1: Testing & Observability

### 1.1 Unit Tests Suite

**Umfang:**
- `test_render.py` (validate_text, load_yaml, combine_en_de)
- `test_convert.py` (validate_filename_stem, loudness_filter)
- `test_audition.py` (model loading, error cases)

**Mindest-Abdeckung:**
- Happy Path für jedes Script
- Error Cases (invalid input, missing files, CUDA errors)
- Edge Cases (empty text, huge text, special chars)

**Tooling:** pytest + pytest-cov für Coverage-Reporting

```bash
# Target: 80% Coverage minimum
pytest --cov=. --cov-report=html
```

---

### 1.2 Strukturiertes Logging statt Print

**Umfang:** Ersetze alle `print()` durch `logging` Module

**Vor:**
```python
print(f"  [{i}/{len(ansagen_list)}] {ansage_id}")
print(f"      ERROR (EN): {e}")
```

**Nach:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing ansage", extra={
    "ansage_id": ansage_id,
    "index": i,
    "total": len(ansagen_list)
})
logger.error("TTS generation failed", exc_info=True, extra={
    "ansage_id": ansage_id,
    "language": "English"
})
```

**Benefits:**
- Filtrierbar nach Level (DEBUG, INFO, WARNING, ERROR)
- Timestamps + Context automatisch
- Logging zu Datei möglich (`logs/` Verzeichnis)
- Production-ready Observability


---

## Phase 2: Performance

### 2.1 Parallelisierung in convert.py

**Problem:** Sequential ffmpeg-Aufrufe (AAC dann MP3 für jede Datei)

**Solution:** ThreadPoolExecutor für parallele Konvertierung

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_convert_parallel(renders_dir, final_dir, max_workers=4):
    """Parallel batch conversion using thread pool."""
    
    wav_files = sorted(Path(renders_dir).glob("*.wav"))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for wav_path in wav_files:
            stem = validate_filename_stem(wav_path.stem)
            aac_path = os.path.join(final_dir, f"{stem}.m4a")
            mp3_path = os.path.join(final_dir, f"{stem}.mp3")
            
            # Submit both conversions (non-blocking)
            f_aac = executor.submit(convert_wav_to_aac, str(wav_path), aac_path)
            f_mp3 = executor.submit(convert_wav_to_mp3, str(wav_path), mp3_path)
            
            futures[f_aac] = ("AAC", wav_path.name)
            futures[f_mp3] = ("MP3", wav_path.name)
        
        # Wait for all to complete
        for future in as_completed(futures):
            fmt, fname = futures[future]
            try:
                future.result()
                logger.info(f"Completed {fmt} conversion", extra={"file": fname})
            except Exception as e:
                logger.error(f"Failed {fmt} conversion", exc_info=True, extra={"file": fname})
```

**Performance Gain:** ~2x faster (4 parallel workers on 8+ core CPU)

**Aufwand:** ~1 Tag (implementation + testing)

---

### 2.2 Loudness-Messung Optimierung

**Problem:** Jeder ffmpeg-Call misst Loudness separat (redundant)

**Solution:** 1x messen, Parameter cachen für beide Formate

```python
def measure_loudness(wav_path):
    """Single ffmpeg pass to measure loudness."""
    cmd = [
        "ffmpeg", "-i", wav_path,
        "-af", "loudnorm=print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse JSON from result.stderr → {"I": ..., "TP": ..., "LRA": ...}
    return parse_loudness_json(result.stderr)

# In batch_convert():
loudness_cache = {}
for wav_path in wav_files:
    if wav_path not in loudness_cache:
        loudness_cache[wav_path] = measure_loudness(wav_path)
    
    metadata = loudness_cache[wav_path]
    # Apply both AAC + MP3 mit gleichen Parametern
    convert_wav_to_aac(wav_path, aac_path, loudness_params=metadata)
    convert_wav_to_mp3(wav_path, mp3_path, loudness_params=metadata)
```

**Performance Gain:** ~20-30% per file (1 loudness-pass instead of 2)

**Aufwand:** ~1 day (ffmpeg JSON parsing + parameter binding)

---

## Phase 3: Code Refactoring

### 3.1 Shared Config Module

**Problem:** DEVICE, DTYPE, ATTN werden 3x definiert

**Solution:** Centralized config.py

```python
# config.py
import os
import torch
from dataclasses import dataclass

@dataclass
class TTSConfig:
    device: str = os.environ.get("TTS_DEVICE", "cuda:0" if torch.cuda.is_available() else "cpu")
    dtype: torch.dtype = torch.bfloat16
    attn_implementation: str = "sdpa"
    
    # Paths
    audition_dir: str = "audition"
    renders_dir: str = "renders"
    final_dir: str = "final"
    
    # Audio
    sample_rate: int = 24000
    loudness_target: str = "-23"  # LUFS
    pause_duration: float = 2.0

# Usage in render.py:
from config import TTSConfig
cfg = TTSConfig()
model = Qwen3TTSModel.from_pretrained(..., device_map=cfg.device, dtype=cfg.dtype)
```

**Benefit:** Single source of truth, easier testing


---

### 3.2 Voice Model Caching (Optional)

**Problem:** audition.py lädt Models mehrfach neu

**Solution:** Cache mit Context Manager

```python
# models.py
from contextlib import contextmanager

_model_cache = {}

@contextmanager
def get_model(model_name, device, dtype):
    """Context manager for cached model loading."""
    if model_name not in _model_cache:
        logger.info(f"Loading model: {model_name}")
        model = Qwen3TTSModel.from_pretrained(
            model_name, device_map=device, dtype=dtype, attn_implementation="sdpa"
        )
        _model_cache[model_name] = model
    
    model = _model_cache[model_name]
    try:
        yield model
    finally:
        pass  # Keep cached

# Usage:
with get_model("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", cfg.device, cfg.dtype) as model:
    wavs, sr = model.generate_voice_design(...)
```

**Benefit:** ~3-5 min faster audition.py on repeated runs

---

## Phase 4: Deployment & Hardening

### 4.1 Docker Image Hardening

**Current Status:** Container-Ziel ist gehärtet + rootless (laut CLAUDE.md)

**To Do:**
- [ ] GPU Discovery (nvidia-ctk cdi generate) → automated in Dockerfile
- [ ] Health checks (Script can render successfully?)
- [ ] Non-root user (avoid running as root)
- [ ] Multi-stage build (reduce image size)


---

### 4.2 CPU-only Image Variant

**Current Status:** Nur CUDA/GPU-Image existiert

**To Do:**
- [ ] Separate Dockerfile.cpu
- [ ] Test auf CPU-only System
- [ ] Model size validation (fit in memory?)
- [ ] Document performance trade-off


---

### 4.3 Environment-Specific Config

**Current Status:** Hard-coded Pfade und Geräte

**To Do:**
- [ ] `.env` file support (dotenv)
- [ ] Helm charts oder Compose overrides für Deployment
- [ ] Secret management (keine API-Keys in Code, aber relevant für zukünftige Cloud-Integration)


---

## Phase 5: Documentation & Guides

### 5.1 Deployment Guide

**Content:**
- System requirements (RAM, VRAM, CPU)
- GPU compatibility matrix (tested on RTX 5090, RTX 4090, etc.)
- CPU-only performance baseline
- Docker setup & troubleshooting
- Scaling to batch 1000+ ansagen

**Aufwand:** ~2-3 days (write + peer review)

---

### 5.2 API / Service Wrapper (Optional)

**Vision:** FastAPI service um render.py exposing HTTP endpoint

```python
# api.py (FastAPI)
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class RenderRequest(BaseModel):
    ansagen: List[AnsageEntry]
    output_format: str = "multiversion"  # en, de, multiversion

@app.post("/render")
async def render(req: RenderRequest):
    """Synchronous TTS rendering."""
    # Call render_batch(req.ansagen) → returns renders/
    return {"status": "ok", "files": [...]}
```

**Benefit:** Programmatic access, potential for SaaS/multi-tenant

**Aufwand:** ~3-5 days (build + test + docs)  
**Priority:** LOW (nur wenn zukünftige Anforderung)

---

## Priority Matrix

| Initiative | Impact | ROI | Quarter |
|-----------|--------|-----|---------|
| Testing Suite | High | Very High | Q3 2026 |
| Structured Logging | High | High | Q3 2026 |
| Parallelization | High | Very High | Q3 2026 |
| Loudness Caching | Medium | High | Q3 2026 |
| Config Refactoring | Medium | Medium | Q4 2026 |
| Docker Hardening | High | Medium | Q4 2026 |
| CPU-only Image | Medium | Medium | Q4 2026 |
| Deployment Guide | High | High | Q3 2026 |
| API Service | Low | Low | Backlog |

---

## Recommended Q3 2026 Roadmap

**Sprint 1 (Weeks 1-2, after Immediate Fixes):**
- ✅ Testing Suite (target 80% coverage)
- ✅ Structured Logging (replace all print)
- ✅ Parallelization convert.py

**Sprint 2 (Weeks 3-4):**
- ✅ Loudness Caching optimization
- ✅ Deployment Guide
- ✅ Docker image improvements (non-root, health checks)

**Sprint 3+ (Q4 2026):**
- ✅ Config Refactoring
- ✅ CPU-only Image variant
- ⚠️ API Service (if demand exists)

---

## Success Metrics

After Phase 1-2 completion:
- ✅ Test Coverage ≥ 80%
- ✅ Logging structured (JSON, filterable)
- ✅ Convert.py ~2x faster
- ✅ Docker image <1GB
- ✅ CPU-only fallback working
- ✅ Deployment Guide public

**Target:** Production-Ready status by End Q3 2026

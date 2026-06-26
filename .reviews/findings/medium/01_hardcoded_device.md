# MEDIUM: Hard-coded CUDA Device

**ID:** CONFIG-001  
**Component:** render.py, audition.py  
**Lines:** render.py:32, audition.py:28  
**Severity:** 🟠 MEDIUM  
**Category:** Portability / Configuration  

## Problem

```python
DEVICE = "cuda:0"  # ← Immer Device 0, keine Option für anderen
```

Script funktioniert nur mit Single-GPU oder wenn GPU 0 frei ist. Multi-GPU-Systeme und CPU-fallback nicht unterstützt.

## Impact

- Nicht portabel auf Multi-GPU-Setups
- CPU-only Systeme crashen
- Keine Fallback-Logik

## Fix

```python
import os
import torch

def get_device():
    """Auto-detect device mit Environment-Variable Override."""
    # Environment-Variable hat Priorität
    if "TTS_DEVICE" in os.environ:
        return os.environ["TTS_DEVICE"]
    
    # Fallback: CUDA wenn verfügbar, sonst CPU
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"

DEVICE = get_device()
print(f"Using device: {DEVICE}")
```

**Usage:**
```bash
# GPU 0 (default)
python render.py

# GPU 1
TTS_DEVICE=cuda:1 python render.py

# CPU-only
TTS_DEVICE=cpu python render.py
```

## Acceptance

- [ ] `get_device()` Funktion in beiden Scripts
- [ ] Environment-Variable `TTS_DEVICE` wird gelesen
- [ ] CPU-fallback funktioniert (mit `torch.cpu` auch langsamer)
- [ ] Startup-Message zeigt aktuelles Device

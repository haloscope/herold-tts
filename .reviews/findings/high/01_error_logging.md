# HIGH: Truncated Error Logging in convert.py

**ID:** OPS-001  
**Component:** convert.py  
**Lines:** 62-64, 82-84  
**Severity:** 🟡 HIGH  
**Category:** Operability / Debugging  

## Problem

ffmpeg stderr wird auf 200 Zeichen gekürzt, critical debug information geht verloren.

```python
except subprocess.CalledProcessError as e:
    print(f"    ERROR (AAC): {e.stderr.decode()[:200]}")  # ← GEKÜRZT!
```

Bei ffmpeg-Fehler (Codec nicht gefunden, Permission denied) werden wichtige Details abgeschnitten.

## Fix

```python
except subprocess.CalledProcessError as e:
    err_msg = e.stderr.decode() if e.stderr else "(no stderr)"
    print(f"    ERROR (AAC): {err_msg}")
    # Oder: Schreibe zu Logfile für Archiv
```

## Acceptance

- [ ] Stderr wird vollständig ausgegeben
- [ ] Test mit fehlender ffmpeg → Error ist aussagekräftig

# HIGH: Missing YAML Schema Validation

**ID:** VAL-001  
**Component:** render.py  
**Lines:** 51-55, 205-207  
**Severity:** 🟡 HIGH  
**Category:** Data Validation / UX  

## Problem

`load_yaml()` prüft nur ob Liste nicht-leer ist, nicht ob Schema korrekt ist.

```python
def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("ansagen", [])  # ← Keine Feld-Prüfung!

# In render_batch:
if not ansagen:  # ← Nur Check: Liste leer?
    raise ValueError("Keine Ansagen...")
```

Ein Eintrag ohne `id` oder `text_en` wird erst bei Zeile 131 crashen mit konfusem Error.

## Fix

```python
from typing import List, Dict

class AnsageEntry:
    def __init__(self, id: str, text_de: str, text_en: str):
        if not id or not isinstance(id, str):
            raise ValueError("id is required and must be string")
        if not text_de or not isinstance(text_de, str):
            raise ValueError(f"text_de is required for id={id}")
        if not text_en or not isinstance(text_en, str):
            raise ValueError(f"text_en is required for id={id}")
        self.id = id
        self.text_de = text_de
        self.text_en = text_en

def load_yaml(path) -> List[AnsageEntry]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    ansagen = data.get("ansagen", [])
    if not ansagen:
        raise ValueError("No ansagen found in YAML")
    
    validated = []
    for i, entry in enumerate(ansagen):
        try:
            validated.append(AnsageEntry(**entry))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid ansage at index {i}: {e}")
    return validated
```

## Acceptance

- [ ] Schema-Validierung implementiert
- [ ] Test: fehlende `id` → ValueError mit Index
- [ ] Test: leerer `text_en` → ValueError
- [ ] Test: gültige Einträge → akzeptiert

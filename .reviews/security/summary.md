# Security Review — Zusammenfassung

**Bewertungszeitraum:** 2026-06-26  
**Module:** render.py, convert.py, audition.py, ansagen.yaml  
**Kritikalität:** Mittel (lokal betriebenes Tool, aber verarbeitet externe Dateien)

## Executive Summary

Die Codebase ist für ein lokal betriebenes FOSS-Tool grundsätzlich sicher, aber es gibt **2 kritische Findings** bei der Dateiverarbeitung und 3 Medium/Low-Findings. Besonders zu beachten: **subprocess + Pfad-Injektion in convert.py**.

## Findings nach Kategorie

### 🔴 KRITISCH (Muss behoben werden)

1. **Path Traversal in convert.py (Zeile 106-108)**
   - `stem` wird direkt als Dateiname verwendet ohne Validierung
   - Potenzial: `../../../etc/passwd_en.m4a` → würde außerhalb `final/` schreiben
   - **Fix:** Basename-Validierung, nur alphanumeric+underscore erlauben

2. **Unvalidierte Text-Input in render.py (Zeile 131-133)**
   - `text_de` und `text_en` aus YAML ohne Längen-Check
   - Potenzial: Extremlange Texte → DoS (TTS Hangs, Memory Exhaustion)
   - **Fix:** Max-Länge-Validierung, Sanitization

### 🟡 MITTEL (Sollte behoben werden)

3. **Error-Handling in convert.py subprocess (Zeile 62-64, 82-84)**
   - stderr wird gekürzt ([:200]) — wichtige Info könnte verloren gehen
   - Besser: Full stderr oder Logging-Datei
   - **Fix:** vollständiges Logging, optional `check=False` mit eigenem Fehler-Handler

4. **Hard-coded CUDA Device in Torch-Skripten (Zeile 32, 28, 28)**
   - `DEVICE = "cuda:0"` wird hart codiert
   - Problem: Multi-GPU-Systeme, CPU-fallback nicht vorhanden
   - **Fix:** Environment-Variable oder Auto-Detection

5. **Keine Validierung der ansagen.yaml Struktur (render.py Zeile 205-207)**
   - `load_yaml()` prüft nur ob Liste existiert, nicht Schema
   - Potenzial: Fehlende Felder → Crash mit unklarem Error
   - **Fix:** JSON-Schema oder Pydantic-Validation

## Zusammenfassung der Maßnahmen

| Severity | Count | Status |
|----------|-------|--------|
| Kritisch | 2 | ⚠️ To Do |
| Mittel   | 3 | ⚠️ To Do |
| **Summe**| **5** | **In Progress** |

---

**Details:** Siehe `details.md`  
**Recommendations:** Siehe `../recommendations/immediate.md`

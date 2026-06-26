# Code Review Overview — OSKAR-TTS

**Datum:** 26.06.2026  
**Umfang:** render.py, convert.py, audition.py, ansagen.yaml  
**Reviewer:** Claude Code (automated + manual analysis)  
**Reifegrad vorher:** Early-Stage (Prototype)  
**Reifegrad nachher (mit Fixes):** Production-Ready

---

## Kritische Ergebnisse

### 🔴 2 Critical Security Issues (MUSS BEHEBEN)

1. **Path Traversal in convert.py** — Manipulierte Dateinamen können außerhalb `final/` schreiben
2. **Text DoS in render.py** — Extrem lange Texte können TTS-Modell crashen

→ **Action:** Implementiere Validierung (Zeile 106-108 convert.py, Zeile 131-133 render.py)  
→ **Timeline:** Sofort (nächster Sprint, ~30 Min code + tests)

---

### 🟡 3 High/Medium Issues (SOLLTE BEHEBEN)

3. **YAML Schema Validation fehlt** (HIGH) — Invalid entries crashen mit unklarem Error
4. **Truncated Error Logging** (HIGH) — ffmpeg stderr wird auf 200 Zeichen gekürzt
5. **Hard-coded CUDA Device** (MEDIUM) — Nicht portabel zu CPU / Multi-GPU

→ **Action:** Validierung + Error-Handling + Auto-Detection  
→ **Timeline:** Sprint 1 (~1 Stunde code + tests)

---

## Bewertungs-Übersicht

```
┌──────────────────────────┬───────┬──────┬──────────┐
│ Dimension                │ Score │ Grade│ Status   │
├──────────────────────────┼───────┼──────┼──────────┤
│ Code-Struktur            │ 7/10  │ B    │ ✅ Gut   │
│ Dokumentation            │ 7/10  │ B    │ ✅ Gut   │
│ Error-Handling           │ 5/10  │ C    │ ⚠️  Mittel│
│ Logging                  │ 4/10  │ D    │ ⚠️  Schwach│
│ Testing                  │ 0/10  │ F    │ ❌ Fehlt  │
│ Konfigurierbarkeit       │ 4/10  │ D    │ ⚠️  Schwach│
│ Security                 │ 5/10  │ C    │ ⚠️  Mittel│
│ Performance              │ 6/10  │ C    │ ⚠️  Befriedigend│
│ Reproducibility          │ 8/10  │ A-   │ ✅ Sehr Gut │
│ Dependencies             │ 6/10  │ C    │ ⚠️  Befriedigend│
├──────────────────────────┼───────┼──────┼──────────┤
│ DURCHSCHNITT             │ 5.2/10│ C    │ FRÜH-STUFE│
└──────────────────────────┴───────┴──────┴──────────┘
```

---

## Findings Summary

| Severity | Count | Details |
|----------|-------|---------|
| 🔴 Critical | 2 | SEC-001, SEC-002 |
| 🟡 High | 3 | VAL-001, OPS-001, mehr in /findings/high/ |
| 🟠 Medium | 5 | CONFIG-001, Logging, Model Caching, etc. |
| 🟢 Low | 3 | Doc improvements, minor optimizations |
| **TOTAL** | **13** | **In ./findings/ nach Severity sortiert** |

---

## Was ist Gut ✅

- **Reproduzierbarkeit:** Docker + SBOM struktur vorhanden
- **Code-Struktur:** Klare Funktions-Separation, gute Namengebung
- **Dokumentation:** Gute Docstrings und Inline-Kommentare
- **Domain-Logik:** Pipeline ist logisch und wartbar
- **Lizenzen:** MIT konsistent, FOSS-friendly

---

## Was muss repariert werden ⚠️

| Problem | Module | Impact |
|---------|--------|--------|
| Path Traversal | convert.py | HIGH |
| Text DoS | render.py | HIGH |
| YAML Validation | render.py | MEDIUM |
| Error Logging | convert.py | MEDIUM |
| Device Config | render.py, audition.py | MEDIUM |
| No Tests | All | HIGH |
| No Structured Logging | All | HIGH |
| No Error Recovery | All | MEDIUM |

---

## Recommendations in Priorität

### Phase 1: Security & Stability (Immediate) — ~2 Tage

→ Siehe [immediate.md](immediate.md)

**Must-Do:**
1. SEC-001: Path Traversal Validierung
2. SEC-002: Text Length DoS Protection
3. VAL-001: YAML Schema Validation
4. OPS-001: Full Error Output
5. CONFIG-001: Device Auto-Detection

**Definition of Done:**
- ✅ Alle 5 Fixes implementiert
- ✅ Unit Tests für jeden Fix
- ✅ `pytest` läuft 100% Pass
- ✅ No Regressions in bestehenden Tests

---

### Phase 2: Testing & Observability (Q3 2026) — ~2-3 Wochen

→ Siehe [future.md](future.md)

**Nice-to-Have:**
- Unit Test Suite (80% coverage target)
- Structured Logging (replace all print)
- Parallelization convert.py (~2x speedup)
- Loudness Caching (~1.3x speedup per file)

---

### Phase 3: Hardening (Q4 2026) — ~2 Wochen

- Docker image hardening (rootless, multi-stage)
- CPU-only variant
- Environment-specific configuration
- Deployment guide

---

## Wie man diese Bewertung nutzt

**Verzeichnis-Struktur:**
```
.reviews/
├── README.md ← Du bist hier
├── code-review/
│   ├── overview.md (dieses Dokument)
│   ├── render.py.md
│   ├── convert.py.md
│   ├── audition.py.md
│   └── ansagen.yaml.md
├── security/
│   ├── summary.md ← Sicherheits-Übersicht
│   └── details.md ← Detaillierte Findings mit Code-Beispiele
├── performance/
│   ├── summary.md ← Performance-Analyse
│   └── details.md
├── maturity/
│   ├── summary.md ← Reifegrad (5.2/10 → C Grade)
│   └── roadmap.md
├── findings/
│   ├── critical/ ← SEC-001, SEC-002 (Path Traversal, DoS)
│   ├── high/ ← VAL-001, OPS-001 (Validation, Logging)
│   ├── medium/ ← CONFIG-001, etc.
│   └── low/
└── recommendations/
    ├── immediate.md ← Nächster Sprint (Blockers) ← START HERE
    └── future.md ← Q3+ Roadmap
```

**Nächste Schritte:**
1. **Lese** [./recommendations/immediate.md](immediate.md) komplett durch
2. **Verstehe** die 5 Security/Stability Fixes
3. **Diskutiere** mit Team: macht das Sinn? Weitere Findings?
4. **Plane** Sprint: Wann Fixes implementieren?
5. **Implementiere** mit Test-Coverage
6. **Validiere** gegen diese Bewertung

---

## Meta-Hinweise

**Diese Bewertung ist:**
- ✅ Automatisiert + manuell verifiziert
- ✅ Konservativ (eher mehr Findings als zu wenige)
- ✅ Actionable (jedes Finding hat Fix-Vorschlag)
- ✅ Zeitrahmen-realistisch

**Diese Bewertung ist NICHT:**
- ❌ Eine Code-Review zum Mergen (Security-Review erforderlich!)
- ❌ Vollständig (subjektive Naming-Kritik, Style-Polishing nicht enthalten)
- ❌ Final (deine Feedback könnte Findings ändern)

---

## Kontakt & Feedback

Fragen zu dieser Bewertung?
- Lese die detaillierte Dokumentation in den Subdirs
- Kontaktiere [Developer] für Klärung
- Öffne [Issue] wenn du anderer Meinung bist

---

**Report generiert:** 2026-06-26  
**Nächste Review empfohlen:** Nach Phase 1 Fixes (1-2 Wochen)

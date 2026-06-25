# Software Bill of Materials (SBOM)
# OSKAR-TTS
# Projekt: Open Source Kommunikations Plattform Architektur (OSKAR)
# 
# Generated: 2026-06-26
# Format: SPDX-compatible JSON + CSV reference

---

## Übersicht

Dieses Projekt ist eine vollständige, selbst-gehostete Pipeline zur Erzeugung
von Telefon-/Voicemail-Ansagen in Deutsch und Englisch mit konsistenter Stimme.

**Kommerziell nutzbar:** Alle Dependencies unter permissiver Open-Source-Lizenz.

---

## Base Container & System-Level Dependencies

| Component | Version | License | Lizenz-Typ | Link |
|-----------|---------|---------|-----------|------|
| **Ubuntu** | 24.04 LTS (jammy) | Proprietary/Multi | OS | https://ubuntu.com/legal |
| **Python** | 3.12 | PSF (Python Software Foundation) | Permissiv | https://www.python.org/about/legal/ |
| **CUDA** | 12.8.1 | NVIDIA EULA | Proprietär (free download) | https://developer.nvidia.com/cuda-toolkit |
| **cuDNN** | (12.8 enthalten) | NVIDIA EULA | Proprietär (free download) | https://developer.nvidia.com/cudnn |

### System Packages (apt)
| Package | License |
|---------|---------|
| ffmpeg | LGPL-2.1+ (Geänderte Lizenzen möglich je nach Codecs) |
| sox | GPL-2.0 |
| curl | MIT |
| git | GPL-2.0+ |
| ca-certificates | MPL-2.0 (Mozilla) |
| gnupg | GPL-3.0+ |

---

## Python Runtime Dependencies

| Package | Version | License | SBOM-ID |
|---------|---------|---------|---------|
| **torch** (PyTorch) | 2.1.x+ | BSD-3-Clause | pytorch-torch |
| **torchaudio** | 2.1.x+ | BSD-2-Clause | pytorch-torchaudio |
| **qwen-tts** | (latest) | Apache-2.0 | alibaba-qwen-tts |
| **soundfile** | (latest) | BSD-3-Clause | soundfile |
| **pyyaml** | (latest) | MIT | pyyaml |

### Detaillierte Python-Abhängigkeiten

#### torch (PyTorch 2.1+)
- **License:** BSD-style license
- **Kommerziell nutzbar:** Ja
- **Link:** https://github.com/pytorch/pytorch
- **Abhängigkeiten:** CUDA 12.8 (proprietär, aber frei), cuDNN, zstd, brotli, snappy, …

#### torchaudio (TorchAudio)
- **License:** BSD-2-Clause License (as of September 2021)
- **Kommerziell nutzbar:** Ja
- **Link:** https://github.com/pytorch/audio
- **Abhängigkeiten:** torch, libsndfile, sox libraries, …

#### qwen-tts
- **License:** Apache-2.0
- **Kommerziell nutzbar:** Ja
- **Link:** https://github.com/QwenLM/Qwen3-TTS
- **Note:** Das Modell Qwen/Qwen3-TTS-1.7B-* ist ebenfalls Apache-2.0

#### soundfile
- **License:** BSD-3-Clause
- **Kommerziell nutzbar:** Ja
- **Link:** https://github.com/bastibe/SoundFile
- **Abhängigkeiten:** libsndfile (LGPL)

#### pyyaml
- **License:** MIT
- **Kommerziell nutzbar:** Ja
- **Link:** https://github.com/yaml/pyyaml
- **Note:** Optionale C-Extension mit MIT License

---

## Qwen3-TTS Modelle

| Modell | License | Kommerziell | Größe | Quelle |
|--------|---------|------------|-------|--------|
| Qwen3-TTS-12Hz-1.7B-CustomVoice | Apache-2.0 | Ja | ~3.8 GB | HuggingFace |
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | Apache-2.0 | Ja | ~3.8 GB | HuggingFace |
| Qwen3-TTS-12Hz-1.7B-Base | Apache-2.0 | Ja | ~3.8 GB | HuggingFace |

Alle Qwen3-Modelle sind unter **Apache-2.0** lizenziert und kommerziell nutzbar.

---

## Projekt-Spezifische Dateien

| Datei | License | Author | Notizen |
|-------|---------|--------|---------|
| audition.py | MIT | Thore (Dataport) | Phase 5.1-2: Stimmen-Audition |
| render.py | MIT | Thore (Dataport) | Phase 5.3-4: Batch-Render |
| convert.py | MIT | Thore (Dataport) | Phase 5.5: ffmpeg Konvertierung |
| Dockerfile | MIT | Thore (Dataport) | Container-Definition |
| docker-compose.yml | MIT | Thore (Dataport) | Orchestrierung |
| ansagen.yaml | Frei definierbar | User | Ansagen-Liste (Daten) |

---

## Lizenz-Zusammenfassung & Compliance

### Permissive Lizenzen (Open Source, kommerziell nutzbar)
- **Apache-2.0:** qwen-tts, qwen3 Modelle, Projekt-Skripte
- **BSD-3-Clause:** PyTorch, soundfile
- **BSD-2-Clause:** torchaudio
- **MIT:** pyyaml
- **GPL-2.0/3.0:** ffmpeg, sox, git, gnupg
  - **ACHTUNG:** GPL ist copyleft; wenn du diese Binäre re-distribuierst, musst du Quellcode anbieten.
  - **In der Praxis:** Container-Images sind OK; Binäre selbst nicht-redistributiert.
- **Proprietär (frei zur Nutzung):** NVIDIA CUDA, cuDNN

### Kommerzielle Nutzbarkeit
✅ **Ja** — alle Komponenten sind für kommerzielle Nutzung freigegeben.
- Keine Gebühren oder Lizenzkosten
- Keine Attributionspflicht (außer optional bei Apache-2.0)
- Keine Copyleft-Anforderungen für Container/Endprodukt

### Besonderheiten
1. **GPL-Komponenten (ffmpeg, sox):** 
   - Zulässig, da sie als externe Tools/Utilities genutzt werden
   - Nicht statisch in deine Binäre gelinkt
   - Falls repackaged: Quellcode-Pflicht

2. **NVIDIA CUDA/cuDNN:**
   - Frei nutzbar, aber proprietär
   - Keine Quellcodes verfügbar
   - Nur als Binary-Download

3. **Modelle (Qwen3):**
   - Apache-2.0 = Frei für kommerzielle Nutzung
   - Attribution optional

---

## Vollständige Abhängigkeits-Chain (JSON-Format)

```json
{
  "sbom_version": "1.0",
  "project": {
    "name": "OSKAR-TTS",
    "version": "1.0.0",
    "date": "2026-06-26",
    "license": "MIT",
    "commercial_use": true
  },
  "components": [
    {
      "name": "torch",
      "version": "2.1+",
      "license": "BSD-3-Clause",
      "spdx_id": "BSD-3-Clause",
      "purl": "pkg:pypi/torch",
      "scope": "runtime",
      "commercial_use": true,
      "attribution_required": false
    },
    {
      "name": "torchaudio",
      "version": "2.1+",
      "license": "BSD-2-Clause",
      "spdx_id": "BSD-2-Clause",
      "purl": "pkg:pypi/torchaudio",
      "scope": "runtime",
      "commercial_use": true,
      "attribution_required": false
    },
    {
      "name": "qwen-tts",
      "version": "latest",
      "license": "Apache-2.0",
      "spdx_id": "Apache-2.0",
      "purl": "pkg:pypi/qwen-tts",
      "scope": "runtime",
      "commercial_use": true,
      "attribution_required": false
    },
    {
      "name": "soundfile",
      "version": "latest",
      "license": "BSD-3-Clause",
      "spdx_id": "BSD-3-Clause",
      "purl": "pkg:pypi/soundfile",
      "scope": "runtime",
      "commercial_use": true,
      "attribution_required": false
    },
    {
      "name": "pyyaml",
      "version": "latest",
      "license": "MIT",
      "spdx_id": "MIT",
      "purl": "pkg:pypi/pyyaml",
      "scope": "runtime",
      "commercial_use": true,
      "attribution_required": false
    },
    {
      "name": "ffmpeg",
      "version": "latest",
      "license": "LGPL-2.1-or-later",
      "spdx_id": "LGPL-2.1-or-later",
      "scope": "build/runtime",
      "commercial_use": true,
      "attribution_required": false,
      "note": "External tool, nicht statisch gelinkt"
    },
    {
      "name": "sox",
      "version": "latest",
      "license": "GPL-2.0-or-later",
      "spdx_id": "GPL-2.0-or-later",
      "scope": "runtime",
      "commercial_use": true,
      "attribution_required": false,
      "note": "Optional backend (torchaudio); externe Utility"
    },
    {
      "name": "Qwen3-TTS-1.7B Models",
      "version": "2026-01",
      "license": "Apache-2.0",
      "spdx_id": "Apache-2.0",
      "scope": "runtime-models",
      "commercial_use": true,
      "attribution_required": false,
      "source": "HuggingFace Model Hub"
    },
    {
      "name": "Ubuntu 24.04 LTS",
      "license": "Multi (Canonical proprietary + GPL + others)",
      "scope": "base-container",
      "commercial_use": true
    },
    {
      "name": "NVIDIA CUDA",
      "version": "12.8.1",
      "license": "NVIDIA EULA (Proprietary, free download)",
      "scope": "runtime-system",
      "commercial_use": true,
      "attribution_required": false,
      "note": "Frei nutzbar, aber proprietär"
    }
  ],
  "risk_assessment": {
    "copyleft_components": ["ffmpeg (LGPL)", "sox (GPL)"],
    "proprietary_components": ["NVIDIA CUDA", "NVIDIA cuDNN"],
    "commercial_use_allowed": true,
    "redistribution_notes": "Container-Images sind OK; Repackaging von GPL-Tools erfordert Quellcode-Offenlegung"
  }
}
```

---

## Für dein Git / Lizenz-Compliance

**Empfehlung:**
1. Füge `LICENSE` (Apache-2.0) in dein Repo ein
2. Kopiere dieses SBOM als `SBOM.md` oder `SBOM.json`
3. Erwähne in der `README.md`:
   ```markdown
   ## Lizenzen
   
   Alle Komponenten unter permissiven Open-Source-Lizenzen (Apache-2.0, BSD, MIT, GPL).
   Siehe [SBOM.md](SBOM.md) für Details.
   
   **Kommerziell nutzbar:** Ja. Keine Lizenzgebühren, keine Copyleft-Anforderungen.
   ```

---

## Lizenz dieser SBOM
Diese SBOM-Dokumentation und das gesamte Projekt unterliegen der MIT-Lizenz.

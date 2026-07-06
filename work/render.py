#!/usr/bin/env python3
"""
render.py - Batch-Rendering mit geclonter Stimme.

Pipeline:
1. Lade reference_design_de.wav (die Stimmen-Referenz)
2. Erzeuge voice_clone_prompt (und speichere ihn für Reproduzierbarkeit)
3. Lese ansagen.yaml (id, sprache, text)
4. Rendere jede Ansage mit der geclonten Stimme:
   - Englisch allein
   - Deutsch allein
   - Kombiniert: EN + 2s Pause + DE (kein extra Rendering)
   -> renders/*.wav (24 kHz, 3 Versionen pro Ansage)

Output: ./renders/<id>_en.wav, <id>_de.wav, <id>_multiversion.wav
Nächster Schritt: convert.py (WAV -> AAC + MP3)
"""

import os
import json
import yaml
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
from dataclasses import dataclass
from qwen_tts import Qwen3TTSModel

# --- Konfiguration -----------------------------------------------------------

ATTN = "sdpa"
DTYPE = torch.bfloat16

def get_device():
    """Auto-detect device: prefer TTS_DEVICE env var, fallback to CUDA or CPU."""
    if "TTS_DEVICE" in os.environ:
        return os.environ["TTS_DEVICE"]
    return "cuda:0" if torch.cuda.is_available() else "cpu"

DEVICE = get_device()

# Pfade
AUDITION_DIR = "audition"
RENDERS_DIR = "renders"
ANSAGEN_FILE = "ansagen.yaml"
CLONE_PROMPT_FILE = "voice_clone_prompt.json"

# Referenz-Datei
REF_AUDIO_FILE = os.path.join(AUDITION_DIR, "reference_design_de.wav")
REF_TEXT_DE = ("Hallo, ich freue mich Sie auf Oskar begrüßen zu dürfen! "
               "Hierbei handelt es sich um die Open Source Kommunikations Plattform Schleswig-Holsteins")

# Multiversion-Parameter
PAUSE_DURATION_SECONDS = 2.0  # Stille zwischen EN und DE
MAX_TEXT_LENGTH = 5000  # Max characters per text (security: DoS protection)

# --- Datenklassen & Validierung -----------------------------------------------

@dataclass
class AnsageEntry:
    id: str
    text_de: str
    text_en: str

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError(f"Invalid id: {self.id}")
        try:
            self.text_de = validate_text(self.text_de)
            self.text_en = validate_text(self.text_en)
        except ValueError as e:
            raise ValueError(f"Validation failed for id={self.id}: {e}")


def validate_text(text: str) -> str:
    """Validate text length and type (DoS protection)."""
    if not isinstance(text, str):
        raise TypeError(f"Expected string, got {type(text)}")
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text too long ({len(text)} > {MAX_TEXT_LENGTH} chars). "
            f"Approx {len(text) / 100:.0f} seconds of audio."
        )
    return text

# --- Funktionen ---------------------------------------------------------------


def load_yaml(path):
    """Load and validate ansagen.yaml schema."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    ansagen = data.get("ansagen", [])
    if not ansagen:
        raise ValueError("No 'ansagen' section found in YAML")

    validated = []
    for i, entry in enumerate(ansagen):
        try:
            validated.append(AnsageEntry(**entry))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid ansage #{i}: {e}")

    return validated


def save_clone_prompt(prompt_obj, path):
    """Speichere voice_clone_prompt als JSON (Metadaten)."""
    metadata = {
        "source": REF_AUDIO_FILE,
        "ref_text": REF_TEXT_DE,
        "created_at": str(Path.cwd()),
        "note": "Der eigentliche prompt_obj muss in-memory im Modell gehalten werden; "
                "diese JSON ist nur Metadaten.",
    }
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Metadaten des Clone-Prompts gespeichert: {path}")


def create_silence(duration_seconds, sample_rate=24000):
    """Erzeuge ein Stille-Array (zeros) mit gegebener Dauer."""
    num_samples = int(duration_seconds * sample_rate)
    return np.zeros(num_samples, dtype=np.float32)


def combine_en_de(en_wav, de_wav, sr, pause_duration=2.0):
    """
    Kombiniere EN-Audio + Pause + DE-Audio zu einer Multiversion.
    
    Args:
        en_wav: Englisches Audio-Array
        de_wav: Deutsches Audio-Array
        sr: Sample-Rate (sollte gleich sein)
        pause_duration: Dauer der Stille in Sekunden
    
    Returns:
        Kombiniertes Audio-Array
    """
    silence = create_silence(pause_duration, sr)
    combined = np.concatenate([en_wav, silence, de_wav])
    return combined


def render_batch(ansagen_list):
    """
    Batch-Render aller Ansagen mit der geclonten Stimme.
    Erzeugt für jede Ansage: EN, DE, und Multiversion (EN+Pause+DE).
    """
    print(f"\n[Render] Batch-Rendering aus ansagen.yaml ({len(ansagen_list)} Ansagen)")
    print(f"         -> 3 Versionen pro Ansage: _en, _de, _multiversion")

    # Modell laden
    print("  Lade Qwen3-TTS-12Hz-1.7B-Base (VoiceClone)...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    # Lade Referenz-Audio
    print(f"  Lade Stimmen-Referenz: {REF_AUDIO_FILE}")
    if not os.path.exists(REF_AUDIO_FILE):
        raise FileNotFoundError(f"{REF_AUDIO_FILE} nicht gefunden! "
                                f"Führe erst audition.py aus.")
    ref_wav, ref_sr = sf.read(REF_AUDIO_FILE)
    print(f"    -> {ref_sr} Hz, {len(ref_wav) / ref_sr:.1f}s")

    # Erzeuge voice_clone_prompt
    print(f"  Erzeuge voice_clone_prompt aus Referenz...")
    voice_clone_prompt = model.create_voice_clone_prompt(
        ref_audio=(ref_wav, ref_sr),
        ref_text=REF_TEXT_DE,
    )
    save_clone_prompt(voice_clone_prompt, CLONE_PROMPT_FILE)

    # Rendere alle Ansagen
    os.makedirs(RENDERS_DIR, exist_ok=True)
    
    for i, ansage in enumerate(ansagen_list, 1):
        ansage_id = ansage.id
        text_de = ansage.text_de
        text_en = ansage.text_en

        print(f"  [{i}/{len(ansagen_list)}] {ansage_id}")

        # Schritt 1: Rendere Englisch
        print(f"      Rendering EN...")
        try:
            en_wavs, en_sr = model.generate_voice_clone(
                text=text_en,
                language="English",
                voice_clone_prompt=voice_clone_prompt,
            )
            en_wav = en_wavs[0]
            en_output = os.path.join(RENDERS_DIR, f"{ansage_id}_en.wav")
            sf.write(en_output, en_wav, en_sr)
            print(f"      -> {en_output}")
        except Exception as e:
            print(f"      ERROR (EN): {e}")
            continue

        # Schritt 2: Rendere Deutsch
        print(f"      Rendering DE...")
        try:
            de_wavs, de_sr = model.generate_voice_clone(
                text=text_de,
                language="German",
                voice_clone_prompt=voice_clone_prompt,
            )
            de_wav = de_wavs[0]
            de_output = os.path.join(RENDERS_DIR, f"{ansage_id}_de.wav")
            sf.write(de_output, de_wav, de_sr)
            print(f"      -> {de_output}")
        except Exception as e:
            print(f"      ERROR (DE): {e}")
            continue

        # Schritt 3: Kombiniere EN + Pause + DE (KEIN extra Rendering!)
        print(f"      Kombiniere EN + 2s Pause + DE...")
        try:
            # Stelle sicher, dass beide die gleiche Sample-Rate haben
            if en_sr != de_sr:
                print(f"      ⚠️ Sample-Rate-Mismatch: EN={en_sr}, DE={de_sr}")
                sr = en_sr  # Nutze EN als Basis
            else:
                sr = en_sr

            combined_wav = combine_en_de(en_wav, de_wav, sr, PAUSE_DURATION_SECONDS)
            multiversion_output = os.path.join(RENDERS_DIR, f"{ansage_id}_multiversion.wav")
            sf.write(multiversion_output, combined_wav, sr)
            print(f"      -> {multiversion_output}")
        except Exception as e:
            print(f"      ERROR (Multiversion): {e}")
            continue

    del model
    torch.cuda.empty_cache()
    print(f"\nFertig! Alle Ansagen in ./renders/ (3 Versionen pro Ansage)")


if __name__ == "__main__":
    # Lade ansagen.yaml
    if not os.path.exists(ANSAGEN_FILE):
        raise FileNotFoundError(f"{ANSAGEN_FILE} nicht gefunden!")

    ansagen = load_yaml(ANSAGEN_FILE)
    if not ansagen:
        raise ValueError("Keine Ansagen in ansagen.yaml gefunden!")

    print(f"CUDA: {torch.cuda.is_available()} | "
          f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    render_batch(ansagen)

    print("\n" + "=" * 70)
    print("Nächster Schritt: python convert.py")
    print("  -> Konvertiert ./renders/*.wav zu AAC + MP3 mit Loudness-Normalisierung")
    print("=" * 70)
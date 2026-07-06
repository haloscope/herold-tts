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
from .logger import setup_logger
from .config import config

logger = setup_logger(__name__)

# --- Konfiguration -----------------------------------------------------------

ATTN = config.attn_implementation
DTYPE = config.dtype
DEVICE = config.device

# Pfade
AUDITION_DIR = config.audition_dir
RENDERS_DIR = config.renders_dir
ANSAGEN_FILE = config.ansagen_file
CLONE_PROMPT_FILE = config.clone_prompt_file

# Referenz-Datei
REF_AUDIO_FILE = config.ref_audio_file
REF_TEXT_DE = config.ref_text_de

# Multiversion-Parameter
PAUSE_DURATION_SECONDS = config.pause_duration
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
    logger.info(f"Clone-Prompt metadata saved: {path}")


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
    logger.info(f"Batch rendering {len(ansagen_list)} announcements → 3 versions per item: _en, _de, _multiversion")

    # Model loading
    logger.info("Loading Qwen3-TTS-12Hz-1.7B-Base (VoiceClone)...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    # Lade Referenz-Audio
    logger.info(f"Loading voice reference: {REF_AUDIO_FILE}")
    if not os.path.exists(REF_AUDIO_FILE):
        raise FileNotFoundError(f"{REF_AUDIO_FILE} nicht gefunden! "
                                f"Führe erst audition.py aus.")
    ref_wav, ref_sr = sf.read(REF_AUDIO_FILE)
    logger.info(f"Reference audio: {ref_sr} Hz, {len(ref_wav) / ref_sr:.1f}s")

    logger.info("Creating voice_clone_prompt from reference...")
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

        logger.info(f"[{i}/{len(ansagen_list)}] Processing: {ansage_id}")

        logger.debug(f"Rendering English for {ansage_id}...")
        try:
            en_wavs, en_sr = model.generate_voice_clone(
                text=text_en,
                language="English",
                voice_clone_prompt=voice_clone_prompt,
            )
            en_wav = en_wavs[0]
            en_output = os.path.join(RENDERS_DIR, f"{ansage_id}_en.wav")
            sf.write(en_output, en_wav, en_sr)
            logger.info(f"✓ EN saved: {en_output}")
        except Exception as e:
            logger.error(f"EN rendering failed: {e}", exc_info=True)
            continue

        logger.debug(f"Rendering German for {ansage_id}...")
        try:
            de_wavs, de_sr = model.generate_voice_clone(
                text=text_de,
                language="German",
                voice_clone_prompt=voice_clone_prompt,
            )
            de_wav = de_wavs[0]
            de_output = os.path.join(RENDERS_DIR, f"{ansage_id}_de.wav")
            sf.write(de_output, de_wav, de_sr)
            logger.info(f"✓ DE saved: {de_output}")
        except Exception as e:
            logger.error(f"DE rendering failed: {e}", exc_info=True)
            continue

        logger.debug("Combining EN + 2s pause + DE...")
        try:
            # Stelle sicher, dass beide die gleiche Sample-Rate haben
            if en_sr != de_sr:
                logger.warning(f"Sample-Rate mismatch: EN={en_sr}, DE={de_sr}. Using EN as base.")
                sr = en_sr
            else:
                sr = en_sr

            combined_wav = combine_en_de(en_wav, de_wav, sr, PAUSE_DURATION_SECONDS)
            multiversion_output = os.path.join(RENDERS_DIR, f"{ansage_id}_multiversion.wav")
            sf.write(multiversion_output, combined_wav, sr)
            logger.info(f"✓ Multiversion saved: {multiversion_output}")
        except Exception as e:
            logger.error(f"Multiversion creation failed: {e}", exc_info=True)
            continue

    del model
    torch.cuda.empty_cache()
    logger.info(f"✓ Batch rendering complete. All files in ./renders/ (3 versions per announcement)")


if __name__ == "__main__":
    # Lade ansagen.yaml
    if not os.path.exists(ANSAGEN_FILE):
        raise FileNotFoundError(f"{ANSAGEN_FILE} nicht gefunden!")

    ansagen = load_yaml(ANSAGEN_FILE)
    if not ansagen:
        raise ValueError("Keine Ansagen in ansagen.yaml gefunden!")

    cuda_info = "CUDA available" if torch.cuda.is_available() else "CPU mode"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    logger.info(f"Device: {device_name} ({cuda_info})")

    render_batch(ansagen)

    logger.info("Next step: python convert.py → converts ./renders/*.wav to AAC + MP3 with loudness normalization")
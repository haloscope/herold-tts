#!/usr/bin/env python3
"""
render.py - Batch rendering with a cloned voice.

Pipeline:
1. Load reference_design_de.wav (the voice reference)
2. Create voice_clone_prompt and record reproducibility metadata
3. Read ansagen.yaml (ID, language-specific text)
4. Render each announcement with the cloned voice:
   - English only
   - German only
   - Combined: EN + 2-second pause + DE (no third synthesis)
   -> renders/*.wav (24 kHz, three variants per announcement)

Output: ./renders/<id>_en.wav, <id>_de.wav, <id>_multiversion.wav
Next step: convert.py (WAV -> AAC + MP3)
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

# --- Configuration -----------------------------------------------------------

ATTN = config.attn_implementation
DTYPE = config.dtype
DEVICE = config.device

# Paths
AUDITION_DIR = config.audition_dir
RENDERS_DIR = config.renders_dir
ANSAGEN_FILE = config.ansagen_file
CLONE_PROMPT_FILE = config.clone_prompt_file

# Reference audio file
REF_AUDIO_FILE = config.ref_audio_file
REF_TEXT_DE = config.ref_text_de

# Combined-version parameters
PAUSE_DURATION_SECONDS = config.pause_duration
MAX_TEXT_LENGTH = 5000  # Max characters per text (security: DoS protection)

# --- Data classes and validation -----------------------------------------------

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

# --- Functions ---------------------------------------------------------------


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
    """Save metadata about the in-memory voice-clone prompt as JSON."""
    metadata = {
        "source": REF_AUDIO_FILE,
        "ref_text": REF_TEXT_DE,
        "created_at": str(Path.cwd()),
        "note": "The prompt_obj itself must remain in the model in memory; "
                "this JSON file contains metadata only.",
    }
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Clone-Prompt metadata saved: {path}")


def create_silence(duration_seconds, sample_rate=24000):
    """Create a zero-valued silence array for the specified duration."""
    num_samples = int(duration_seconds * sample_rate)
    return np.zeros(num_samples, dtype=np.float32)


def combine_en_de(en_wav, de_wav, sr, pause_duration=2.0):
    """
    Combine English audio, a pause, and German audio into a bilingual version.

    Args:
        en_wav: English audio array
        de_wav: German audio array
        sr: Sample rate (must match for both inputs)
        pause_duration: Duration of silence in seconds

    Returns:
        Combined audio array
    """
    silence = create_silence(pause_duration, sr)
    combined = np.concatenate([en_wav, silence, de_wav])
    return combined


def render_batch(ansagen_list):
    """
    Batch-render all announcements using the cloned voice.
    Each announcement produces EN, DE, and combined EN+pause+DE audio.
    """
    logger.info(f"Batch rendering {len(ansagen_list)} announcements → 3 versions per item: _en, _de, _multiversion")

    # Model loading
    logger.info("Loading Qwen3-TTS-12Hz-1.7B-Base (VoiceClone)...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    # Load reference audio
    logger.info(f"Loading voice reference: {REF_AUDIO_FILE}")
    if not os.path.exists(REF_AUDIO_FILE):
        raise FileNotFoundError(f"{REF_AUDIO_FILE} not found! "
                                f"Run audition.py first.")
    ref_wav, ref_sr = sf.read(REF_AUDIO_FILE)
    logger.info(f"Reference audio: {ref_sr} Hz, {len(ref_wav) / ref_sr:.1f}s")

    logger.info("Creating voice_clone_prompt from reference...")
    voice_clone_prompt = model.create_voice_clone_prompt(
        ref_audio=(ref_wav, ref_sr),
        ref_text=REF_TEXT_DE,
    )
    save_clone_prompt(voice_clone_prompt, CLONE_PROMPT_FILE)

    # Render all announcements
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
            # Ensure both clips use the same sample rate
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
    # Load ansagen.yaml
    if not os.path.exists(ANSAGEN_FILE):
        raise FileNotFoundError(f"{ANSAGEN_FILE} not found!")

    ansagen = load_yaml(ANSAGEN_FILE)
    if not ansagen:
        raise ValueError("No announcements found in ansagen.yaml!")

    cuda_info = "CUDA available" if torch.cuda.is_available() else "CPU mode"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    logger.info(f"Device: {device_name} ({cuda_info})")

    render_batch(ansagen)

    logger.info("Next step: python convert.py → converts ./renders/*.wav to AAC + MP3 with loudness normalization")
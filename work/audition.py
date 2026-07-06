#!/usr/bin/env python3
"""
audition.py

Erzeugt Kandidaten-Samples für Voicemail-Ansagen mit TRENNSCHÄRFEREN PROMPTS.

CustomVoice-Presets hatten unterschiedliche Emphase und Intonation.
Lösung:
  - Explizite, detaillierte Instruktionen für "neutral, steady, no variation"
  - Nur die besten Kandidaten testen (nicht alle 9)
  - VoiceDesign mit acoustic properties statt Persona
  - design_then_clone Workflow für maximale Stabilität

Ausgabe: ./audition/*.wav  (24 kHz WAV)
Danach: anhoeren, Favorit wählen & Favorit in der render.py als REF_AUDIO_FILE setzen.
"""

import os
import torch
import soundfile as sf
from contextlib import contextmanager
from qwen_tts import Qwen3TTSModel
from logger import setup_logger
from config import config

logger = setup_logger(__name__)

# --- Konfiguration -----------------------------------------------------------

OUT_DIR = config.audition_dir
ATTN = config.attn_implementation
DTYPE = config.dtype
DEVICE = config.device

# Model cache
_model_cache = {}


@contextmanager
def get_model(model_name: str):
    """Context manager for cached model loading (avoid reloading)."""
    if model_name not in _model_cache:
        logger.info(f"Loading model: {model_name}")
        model = Qwen3TTSModel.from_pretrained(
            model_name, device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN
        )
        _model_cache[model_name] = model
        logger.info(f"Model cached: {model_name}")
    else:
        logger.debug(f"Using cached model: {model_name}")

    model = _model_cache[model_name]
    try:
        yield model
    finally:
        pass  # Keep cached for next use

# Testsatz für Voicemail
TEXT_DE = ("Hallo, ich freue mich Sie auf Oskar begrüßen zu dürfen! "
           "Hierbei handelt es sich um die Open Source Kommunikations Plattform Schleswig-Holsteins")
TEXT_EN = ("Hello, I'm delighted to welcome you to Oscar!"
           "This is the Open Source Communication Platform of Schleswig-Holstein.")

# A) CustomVoice-Kandidaten mit spezifischen Instruktionen.
#    Schlüssel: neutral, steady, konsistent über DE+EN.
#    Dict statt List -> Pro Speaker explizite Instruktion.
CUSTOM_SPEAKERS = {
    # Weibliche Stimmen (die stabilen)
    "vivian": "Calm, professional, controlled, neutral affect, "
              "consistent volume, clear articulation, steady pacing",
    "sohee": "Neutral, professional, measured tone, steady delivery, "
             "clear enunciation, no emphasis variations, consistent pace",
}

# B) VoiceDesign mit acoustic properties (nicht Persona).
#    Explizit auf Voicemail-Anforderung ausgerichtet.
VOICE_DESIGNS = {
    "design_female_neutral": (
        "Mature female voice, lower-to-mid register, neutral professional tone, "
        "measured pace, steady delivery, clear articulation, no dynamic variation, "
        "authoritative announcer style, consistent volume throughout"
    ),
    "design_male_neutral": (
        "Male voice, deeper register, neutral professional tone, measured pace, "
        "steady and calm, clear enunciation, consistent volume, "
        "authoritative announcer style, no emotional inflection, "
        "predictable phrasing"
    ),
}

# Optional: Design-then-Clone Workflow für maximale Stabilität
#           Erzeugt einmal eine Referenz mit VoiceDesign, klont dann davon.
#           (Aktiviert mit USE_DESIGN_THEN_CLONE = True)
USE_DESIGN_THEN_CLONE =  True

# --- Funktionen ---------------------------------------------------------------


def save(wav, sr, name):
    path = os.path.join(OUT_DIR, f"{name}.wav")
    sf.write(path, wav, sr)
    logger.info(f"Saved: {path}")


def run_custom_voice():
    """CustomVoice: fertige Presets mit expliziten Instruktionen."""
    logger.info("[A] CustomVoice (preset speakers with instructions)")

    with get_model("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice") as model:
        logger.info(f"Available speakers: {model.get_supported_speakers()}")
        logger.info(f"Available languages: {model.get_supported_languages()}")

        for spk, instruct in CUSTOM_SPEAKERS.items():
            logger.info(f"Speaker: {spk} — {instruct[:60]}...")
            wavs, sr = model.generate_custom_voice(
                text=[TEXT_DE, TEXT_EN],
                language=["German", "English"],
                speaker=[spk, spk],
                instruct=[instruct, instruct],
            )
            save(wavs[0], sr, f"custom_{spk}_de")
            save(wavs[1], sr, f"custom_{spk}_en")

    torch.cuda.empty_cache()


def run_voice_design():
    """VoiceDesign: Stimmen per acoustic-Beschreibung."""
    logger.info("[B] VoiceDesign (design voices by description)")

    with get_model("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign") as model:
        for name, instruct in VOICE_DESIGNS.items():
            logger.info(f"Design: {name} — {instruct[:60]}...")
            wavs, sr = model.generate_voice_design(
                text=[TEXT_DE, TEXT_EN],
                language=["German", "English"],
                instruct=[instruct, instruct],
            )
            save(wavs[0], sr, f"{name}_de")
            save(wavs[1], sr, f"{name}_en")

    torch.cuda.empty_cache()


def run_design_references():
    """Generate reference recordings for all VoiceDesign designs (basis for cloning)."""
    logger.info("[C] VoiceDesign References (all designs in DE + EN)")

    with get_model("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign") as model:
        for design_name, instruct in VOICE_DESIGNS.items():
            logger.debug(f"Design: {design_name}")
            wavs, sr = model.generate_voice_design(
                text=[TEXT_DE, TEXT_EN],
                language=["German", "English"],
                instruct=[instruct, instruct],
            )
            save(wavs[0], sr, f"ref_{design_name}_de")
            save(wavs[1], sr, f"ref_{design_name}_en")

    torch.cuda.empty_cache()


def run_design_then_clone():
    """Optional: Design-then-Clone Workflow (create reference → clone from it)."""
    if not USE_DESIGN_THEN_CLONE:
        return

    logger.info("[D] Design-then-Clone (optional, for maximum stability)")

    # Step 1: Create reference with VoiceDesign
    ref_instruct = VOICE_DESIGNS["design_female_neutral"]
    ref_text = TEXT_DE

    with get_model("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign") as design_model:
        logger.info("Creating reference clip with VoiceDesign...")
        ref_wavs, sr = design_model.generate_voice_design(
            text=ref_text,
            language="German",
            instruct=ref_instruct,
        )
        ref_wav = ref_wavs[0]
        save(ref_wav, sr, "reference_design_de")

    torch.cuda.empty_cache()

    # Step 2: Clone from reference
    with get_model("Qwen/Qwen3-TTS-12Hz-1.7B-Base") as clone_model:
        voice_clone_prompt = clone_model.create_voice_clone_prompt(
            ref_audio=(ref_wav, sr),
            ref_text=ref_text,
        )

        logger.info("Cloning reference voice...")
        for lang_code, text, name_suffix in [
            ("German", TEXT_DE, "dtc_de"),
            ("English", TEXT_EN, "dtc_en"),
        ]:
            wavs, sr = clone_model.generate_voice_clone(
                text=text,
                language=lang_code,
                voice_clone_prompt=voice_clone_prompt,
            )
            save(wavs[0], sr, f"design_then_clone_{name_suffix}")

    torch.cuda.empty_cache()


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    cuda_device = (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "CPU"
    )
    logger.info(f"Device: {cuda_device}")

    run_custom_voice()
    run_voice_design()
    run_design_references()
    run_design_then_clone()

    logger.info("✓ Audition complete. All samples in ./audition/")
    logger.info("Review candidates:")
    logger.info("  A) CustomVoice (custom_*.wav) — consistency check DE=EN")
    logger.info("  B) VoiceDesign (design_*_*.wav) — naturalness check")
    logger.info("  C) VoiceDesign References (ref_*.wav) — basis for cloning")
    
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
from qwen_tts import Qwen3TTSModel
from logger import setup_logger

logger = setup_logger(__name__)

# --- Konfiguration -----------------------------------------------------------

OUT_DIR = "audition"
ATTN = "sdpa"
DTYPE = torch.bfloat16

def get_device():
    """Auto-detect device: prefer TTS_DEVICE env var, fallback to CUDA or CPU."""
    if "TTS_DEVICE" in os.environ:
        return os.environ["TTS_DEVICE"]
    return "cuda:0" if torch.cuda.is_available() else "cpu"

DEVICE = get_device()

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
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    logger.info(f"Available speakers: {model.get_supported_speakers()}")
    logger.info(f"Available languages: {model.get_supported_languages()}")

    for spk, instruct in CUSTOM_SPEAKERS.items():
        logger.info(f"Speaker: {spk} — {instruct[:60]}...")
        wavs, sr = model.generate_custom_voice(
            text=[TEXT_DE, TEXT_EN],
            language=["German", "English"],
            speaker=[spk, spk],
            instruct=[instruct, instruct],  # GLEICH für DE+EN
        )
        save(wavs[0], sr, f"custom_{spk}_de")
        save(wavs[1], sr, f"custom_{spk}_en")

    del model
    torch.cuda.empty_cache()


def run_voice_design():
    """VoiceDesign: Stimmen per acoustic-Beschreibung."""
    logger.info("[B] VoiceDesign (design voices by description)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    for name, instruct in VOICE_DESIGNS.items():
        logger.info(f"Design: {name} — {instruct[:60]}...")
        wavs, sr = model.generate_voice_design(
            text=[TEXT_DE, TEXT_EN],
            language=["German", "English"],
            instruct=[instruct, instruct],  # GLEICH für DE+EN
        )
        save(wavs[0], sr, f"{name}_de")
        save(wavs[1], sr, f"{name}_en")

    del model
    torch.cuda.empty_cache()


def run_design_references():
    """
    Generiere Referenzaufnahmen für alle VoiceDesign-Beschreibungen
    in beiden Sprachen (DE + EN). Diese sind die Basis für das Design-then-Clone
    Workflow und interessant zum Anhören.
    """
    logger.info("[C] VoiceDesign References (all designs in DE + EN)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    for design_name, instruct in VOICE_DESIGNS.items():
        logger.debug(f"Design: {design_name}")
        wavs, sr = model.generate_voice_design(
            text=[TEXT_DE, TEXT_EN],
            language=["German", "English"],
            instruct=[instruct, instruct],
        )
        save(wavs[0], sr, f"ref_{design_name}_de")
        save(wavs[1], sr, f"ref_{design_name}_en")

    del model
    torch.cuda.empty_cache()


def run_design_then_clone():
    """
    Optional: Design-then-Clone Workflow.
    1. Erzeugt Referenzclip mit VoiceDesign
    2. Klont davon ab für stabiler konsistente Ergebnisse
    (Benötigt VoiceClone-Base-Modell; nur wenn USE_DESIGN_THEN_CLONE=True)
    """
    if not USE_DESIGN_THEN_CLONE:
        return

    logger.info("[D] Design-then-Clone (optional, for maximum stability)")
    # Schritt 1: VoiceDesign erzeugt Referenz
    design_model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    ref_instruct = VOICE_DESIGNS["design_female_neutral"]
    ref_text = TEXT_DE  # Referenz auf Deutsch

    logger.info("Creating reference clip with VoiceDesign...")
    ref_wavs, sr = design_model.generate_voice_design(
        text=ref_text,
        language="German",
        instruct=ref_instruct,
    )
    ref_wav = ref_wavs[0]
    save(ref_wav, sr, "reference_design_de")
    del design_model
    torch.cuda.empty_cache()

    # Schritt 2: Clone-Modell verwendet die Referenz
    clone_model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    voice_clone_prompt = clone_model.create_voice_clone_prompt(
        ref_audio=(ref_wav, sr),
        ref_text=ref_text,
    )

    # Aus der Referenz klonen (auf DE+EN)
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

    del clone_model
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
    
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
Danach: anhören, beurteilen, einer Stimme final wählen.
"""

import os
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

# --- Konfiguration -----------------------------------------------------------

OUT_DIR = "audition"
ATTN = "sdpa"
DTYPE = torch.bfloat16
DEVICE = "cuda:0"

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
    print(f"  -> {path}")


def run_custom_voice():
    """CustomVoice: fertige Presets mit expliziten Instruktionen."""
    print("\n[A] CustomVoice (fertige Presets mit Instruktionen)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    print("  verfügbare Speaker:", model.get_supported_speakers())
    print("  verfügbare Sprachen:", model.get_supported_languages())

    for spk, instruct in CUSTOM_SPEAKERS.items():
        print(f"  Speaker: {spk}")
        print(f"    Instruct: {instruct[:60]}...")
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
    print("\n[B] VoiceDesign (Stimmen per Beschreibung)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    for name, instruct in VOICE_DESIGNS.items():
        print(f"  Design: {name}")
        print(f"    Prompt: {instruct[:60]}...")
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
    print("\n[C] VoiceDesign-Referenzen (alle Designs in DE + EN)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    for design_name, instruct in VOICE_DESIGNS.items():
        print(f"  Design: {design_name}")
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

    print("\n[C] Design-then-Clone (optional, für maximale Stabilität)")
    # Schritt 1: VoiceDesign erzeugt Referenz
    design_model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    ref_instruct = VOICE_DESIGNS["design_female_neutral"]
    ref_text = TEXT_DE  # Referenz auf Deutsch

    print(f"  Erzeuge Referenzclip mit VoiceDesign...")
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
    print(f"  Klone davon ab...")
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
    print(f"CUDA: {torch.cuda.is_available()} | Device: {cuda_device}")

    run_custom_voice()
    run_voice_design()
    run_design_references()  # Referenzen für alle Designs in DE+EN
    run_design_then_clone()

    print("\n" + "=" * 70)
    print("Fertig. Alle Samples in ./audition/")
    print("Zu prüfen:")
    print("  A) CustomVoice (custom_*.wav):")
    print("     - Welche ist am konsistentesten (DE=EN Emphasis)?")
    print("  B) VoiceDesign (design_*_*.wav):")
    print("     - Welche klingt am natürlichsten?")
    print("  C) VoiceDesign-Referenzen (ref_*.wav) - NEUE Dateien:")
    print("     - design_female_neutral in DE + EN")
    print("     - design_male_neutral in DE + EN")
    print("     (Basis für Design-then-Clone Cloning)")
    print("=" * 70)

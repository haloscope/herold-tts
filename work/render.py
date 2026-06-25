#!/usr/bin/env python3
"""
render.py

Pipeline:
1. Lade reference_design_de.wav (die Stimmen-Referenz)
2. Erzeuge voice_clone_prompt (und speichere ihn für Reproduzierbarkeit)
3. Lese ansagen.yaml (id, sprache, text)
4. Rendere jede Ansage mit der geclonten Stimme -> renders/*.wav (24 kHz)

Ausgabe: ./renders/<id>.wav
Nächster Schritt: convert.py (WAV -> AAC + MP3)
"""

import os
import json
import yaml
import torch
import soundfile as sf
from pathlib import Path
from qwen_tts import Qwen3TTSModel

# --- Konfiguration -----------------------------------------------------------

ATTN = "sdpa"
DTYPE = torch.bfloat16
DEVICE = "cuda:0"

# Pfade
AUDITION_DIR = "audition"
RENDERS_DIR = "renders"
ANSAGEN_FILE = "ansagen.yaml"
CLONE_PROMPT_FILE = "voice_clone_prompt.json"  # Speichert den Prompt (für Reproduzierbarkeit)

# Referenz-Datei (muss in audition/ liegen)
REF_AUDIO_FILE = os.path.join(AUDITION_DIR, "reference_design_de.wav")
REF_TEXT_DE = ("Hallo, ich freue mich Sie auf Oskar begrüßen zu dürfen! "
               "Hierbei handelt es sich um die Open Source Kommunikations Plattform Schleswig-Holsteins")

# --- Funktionen ---------------------------------------------------------------


def load_yaml(path):
    """Lese ansagen.yaml."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("ansagen", [])


def save_clone_prompt(prompt_obj, path):
    """Speichere voice_clone_prompt als JSON (für Reproduzierbarkeit + Debugging)."""
    # Serialisierung ist schwierig (prompt_obj ist ein Qwen3-Datentyp),
    # aber wir speichern zumindest Metadaten + eine Referenz.
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


def render_batch(ansagen_list):
    """
    Batch-Render aller Ansagen mit der geclonten Stimme.
    """
    print(f"\n[Render] Batch-Rendering aus ansagen.yaml ({len(ansagen_list)} Ansagen)")

    # Modell laden (VoiceClone-Base)
    print("  Lade Qwen3-TTS-12Hz-1.7B-Base (VoiceClone)...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )

    # Schritt 1: Lade Referenz-Audio
    print(f"  Lade Stimmen-Referenz: {REF_AUDIO_FILE}")
    if not os.path.exists(REF_AUDIO_FILE):
        raise FileNotFoundError(f"{REF_AUDIO_FILE} nicht gefunden! "
                                f"Führe erst audition.py aus.")
    ref_wav, ref_sr = sf.read(REF_AUDIO_FILE)
    print(f"    -> {ref_sr} Hz, {len(ref_wav) / ref_sr:.1f}s")

    # Schritt 2: Erzeuge voice_clone_prompt
    print(f"  Erzeuge voice_clone_prompt aus Referenz...")
    voice_clone_prompt = model.create_voice_clone_prompt(
        ref_audio=(ref_wav, ref_sr),
        ref_text=REF_TEXT_DE,
    )
    # Speichere Metadaten (für Audit/Reproduzierbarkeit)
    save_clone_prompt(voice_clone_prompt, CLONE_PROMPT_FILE)

    # Schritt 3: Rendere alle Ansagen
    os.makedirs(RENDERS_DIR, exist_ok=True)
    
    for i, ansage in enumerate(ansagen_list, 1):
        ansage_id = ansage["id"]
        lang = ansage["sprache"]
        text = ansage["text"]
        
        print(f"  [{i}/{len(ansagen_list)}] {ansage_id} ({lang})")
        print(f"      Text: {text[:60]}...")
        
        # Qwen3 erkennt Sprache; "German" / "English" sind die Codes
        lang_code = "German" if lang.lower() in ["de", "german", "deutsch"] else "English"
        
        try:
            wavs, sr = model.generate_voice_clone(
                text=text,
                language=lang_code,
                voice_clone_prompt=voice_clone_prompt,
            )
            
            # Speichere als 24 kHz WAV
            output_path = os.path.join(RENDERS_DIR, f"{ansage_id}.wav")
            sf.write(output_path, wavs[0], sr)
            print(f"      -> {output_path}")
        except Exception as e:
            print(f"      ERROR: {e}")
            continue

    del model
    torch.cuda.empty_cache()
    print(f"\nFertig! {len(ansagen_list)} Ansagen in ./renders/")


if __name__ == "__main__":
    # Lade ansagen.yaml
    if not os.path.exists(ANSAGEN_FILE):
        raise FileNotFoundError(f"{ANSAGEN_FILE} nicht gefunden! "
                                f"Erstelle die Datei mit den Ansagen.")

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

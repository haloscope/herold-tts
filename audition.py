#!/usr/bin/env python3
"""
audition.py - Stimmen-Auditierung.

Erzeugt fuer jede Kandidatenstimme denselben deutschen UND englischen
Ansage-Testsatz, damit du mit echten Ohren entscheidest, welche Stimme
fuer die Voicemail/Ansagen passt - bevor wir die finalen Ansagen rendern.

Deckt beide Wege ab:
  A) CustomVoice  -> 9 fertige Presets (kein Sample noetig).
                     KEINE davon ist deutscher Native; Englisch-Presets
                     (Ryan/Aiden) sind erfahrungsgemaess der beste Kompromiss
                     fuer DE+EN aus einer Stimme.
  B) VoiceDesign  -> Stimme per Textbeschreibung, kann deutschen Native-Klang
                     erzeugen, ebenfalls ohne Aufnahme.

Ausgabe: ./audition/*.wav  (24 kHz WAV)
Danach: anhoeren, Favorit wählen & Favorit in der render.py als REF_AUDIO_FILE setzen. -> wir locken die
Stimme fest und rendern die echten Ansagen (Schritt 3-5).
"""

import os
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

# --- Konfiguration -----------------------------------------------------------

OUT_DIR = "audition"
# "sdpa" laeuft ohne Zusatz-Build. Nach `pip install flash-attn` kannst du
# hier auf "flash_attention_2" wechseln (spart VRAM, auf der 5090 nicht noetig).
ATTN = "sdpa"
DTYPE = torch.bfloat16
DEVICE = "cuda:0"

# Neutraler Ansage-Testsatz - bewusst typischer Voicemail-Inhalt.
TEXT_DE = ("Willkommen. Sie haben unsere Mailbox erreicht. "
           "Bitte hinterlassen Sie nach dem Signalton eine Nachricht.")
TEXT_EN = ("Welcome. You have reached our voicemail. "
           "Please leave a message after the tone.")

# A) Welche CustomVoice-Presets antesten (aus den 9 verfuegbaren).
#    Englisch-Presets zuerst, weil sie DE+EN am ausgewogensten klingen.
CUSTOM_SPEAKERS = ["Sohee", "Serena", "Vivian"]

# B) VoiceDesign-Beschreibungen (frei editierbar - das ist der kreative Hebel).
VOICE_DESIGNS = {
    "design_de_frau": "Ruhige, professionelle deutsche Sprecherin mittleren "
                      "Alters, klare Artikulation, neutrales Hochdeutsch, "
                      "sachlicher und freundlicher Ansagen-Tonfall.",
    "design_de_mann": "Seriöser deutscher Sprecher, mittlere bis tiefe "
                      "Stimmlage, ruhig und vertrauenswürdig, neutraler "
                      "Hochdeutsch-Akzent, klarer Ansagen-Tonfall.",
}

# -----------------------------------------------------------------------------


def save(wav, sr, name):
    path = os.path.join(OUT_DIR, f"{name}.wav")
    sf.write(path, wav, sr)
    print(f"  -> {path}")


def run_custom_voice():
    print("\n[A] CustomVoice (fertige Presets)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    # Ground Truth ausgeben - was kann das Modell wirklich?
    print("  unterstuetzte Speaker:", model.get_supported_speakers())
    print("  unterstuetzte Sprachen:", model.get_supported_languages())

    for spk in CUSTOM_SPEAKERS:
        print(f"  Speaker: {spk}")
        wavs, sr = model.generate_custom_voice(
            text=[TEXT_DE, TEXT_EN],
            language=["German", "English"],
            speaker=[spk, spk],
            instruct=["", ""],   # leer = natuerlicher Klang; spaeter z.B. "Calm, professional."
        )
        save(wavs[0], sr, f"custom_{spk}_de")
        save(wavs[1], sr, f"custom_{spk}_en")

    del model
    torch.cuda.empty_cache()


def run_voice_design():
    print("\n[B] VoiceDesign (Stimme per Beschreibung)")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map=DEVICE, dtype=DTYPE, attn_implementation=ATTN,
    )
    for name, instruct in VOICE_DESIGNS.items():
        print(f"  Design: {name}")
        wavs, sr = model.generate_voice_design(
            text=[TEXT_DE, TEXT_EN],
            language=["German", "English"],
            instruct=[instruct, instruct],
        )
        save(wavs[0], sr, f"{name}_de")
        save(wavs[1], sr, f"{name}_en")

    del model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"CUDA: {torch.cuda.is_available()} | "
          f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    run_custom_voice()
    run_voice_design()
    print("\nFertig. Alle Samples liegen in ./audition/ - anhoeren und Favorit waehlen.")

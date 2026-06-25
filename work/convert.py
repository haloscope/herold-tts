#!/usr/bin/env python3
"""
convert.py - Batch-Konvertierung zu AAC + MP3.

Pipeline:
1. Lese ./renders/*.wav (24 kHz, von render.py)
2. Normalisiere Loudness (EBU R128 -23 LUFS, typisch für Broadcast)
3. Speichere beide Formate:
   - ./final/*.m4a (AAC, ~192 kbps)
   - ./final/*.mp3 (MP3, ~192 kbps VBR)

Ausgabe: ./final/<id>.m4a und ./final/<id>.mp3
"""

import os
import subprocess
from pathlib import Path

# --- Konfiguration -----------------------------------------------------------

RENDERS_DIR = "renders"
FINAL_DIR = "final"

# ffmpeg-Parameter
# AAC: libfdk_aac (höhere Qualität) oder aac (default)
# MP3: libmp3lame -q:a 2 (VBR ~192 kbps, transparent)
AAC_CODEC = "aac"  # oder "libfdk_aac" falls vorhanden
AAC_BITRATE = "192k"
MP3_VBR = "2"  # 0=best, 9=worst; 2 ≈ 190 kbps VBR, transparent

# EBU R128: Standard für Broadcast/Voicemail
LOUDNESS_TARGET = "-23"  # LUFS (Loudness Units relative to Full Scale)

# --- Funktionen ---------------------------------------------------------------


def get_loudness_filter(target_lufs="-23"):
    """
    ffmpeg loudnorm Filter: misst Loudness, normalisiert auf target.
    Zwei Pässe: Pass 1 misst, Pass 2 normalisiert.
    """
    return (
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
    )


def convert_wav_to_aac(wav_path, output_path, loudness_target="-23"):
    """WAV -> AAC mit Loudness-Normalisierung."""
    loudness_filter = get_loudness_filter(loudness_target)
    cmd = [
        "ffmpeg",
        "-i", wav_path,
        "-af", loudness_filter,
        "-c:a", AAC_CODEC,
        "-b:a", AAC_BITRATE,
        "-y",  # overwrite
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ERROR (AAC): {e.stderr.decode()[:200]}")
        return False


def convert_wav_to_mp3(wav_path, output_path, loudness_target="-23"):
    """WAV -> MP3 mit Loudness-Normalisierung."""
    loudness_filter = get_loudness_filter(loudness_target)
    cmd = [
        "ffmpeg",
        "-i", wav_path,
        "-af", loudness_filter,
        "-c:a", "libmp3lame",
        "-q:a", MP3_VBR,
        "-y",  # overwrite
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ERROR (MP3): {e.stderr.decode()[:200]}")
        return False


def batch_convert(renders_dir, final_dir):
    """
    Batch-Konvertierung: alle *.wav aus renders_dir -> final_dir (m4a + mp3).
    """
    print(f"\n[Convert] Batch-Konvertierung {renders_dir}/ -> {final_dir}/")

    if not os.path.isdir(renders_dir):
        raise FileNotFoundError(f"{renders_dir}/ nicht gefunden! "
                                f"Führe erst render.py aus.")

    os.makedirs(final_dir, exist_ok=True)

    wav_files = sorted(Path(renders_dir).glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"Keine *.wav in {renders_dir}/ gefunden!")

    print(f"  Gefunden: {len(wav_files)} WAV-Dateien")

    for i, wav_path in enumerate(wav_files, 1):
        stem = wav_path.stem  # Dateiname ohne .wav
        aac_path = os.path.join(final_dir, f"{stem}.m4a")
        mp3_path = os.path.join(final_dir, f"{stem}.mp3")

        print(f"  [{i}/{len(wav_files)}] {stem}")

        # AAC
        if convert_wav_to_aac(str(wav_path), aac_path):
            print(f"      -> {aac_path}")
        else:
            print(f"      -> FAILED: {aac_path}")

        # MP3
        if convert_wav_to_mp3(str(wav_path), mp3_path):
            print(f"      -> {mp3_path}")
        else:
            print(f"      -> FAILED: {mp3_path}")

    print(f"\nFertig! Alle Dateien in ./{final_dir}/")


if __name__ == "__main__":
    print("ffmpeg-Konvertierung: WAV -> AAC + MP3 mit Loudness-Normalisierung\n")
    
    # Check ffmpeg verfügbar
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg nicht gefunden! Installiere mit: apt-get install ffmpeg")

    batch_convert(RENDERS_DIR, FINAL_DIR)

    print("\n" + "=" * 70)
    print("Fertig!")
    print(f"AAC-Dateien (.m4a):  ./{FINAL_DIR}/*.m4a")
    print(f"MP3-Dateien (.mp3):  ./{FINAL_DIR}/*.mp3")
    print("=" * 70)

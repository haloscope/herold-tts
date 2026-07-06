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
import re
import subprocess
from pathlib import Path
from logger import setup_logger

logger = setup_logger(__name__)

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


def validate_filename_stem(stem: str) -> str:
    """Allow only alphanumeric, underscore, hyphen (Path Traversal protection)."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', stem):
        raise ValueError(f"Invalid filename stem: {stem}")
    return stem


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
        stderr = e.stderr.decode() if e.stderr else "(no stderr)"
        print(f"    ERROR (AAC): {stderr}")
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
        stderr = e.stderr.decode() if e.stderr else "(no stderr)"
        print(f"    ERROR (MP3): {stderr}")
        return False


def batch_convert(renders_dir, final_dir):
    """
    Batch-Konvertierung: alle *.wav aus renders_dir -> final_dir (m4a + mp3).
    """
    logger.info(f"Batch conversion: {renders_dir}/ → {final_dir}/")

    if not os.path.isdir(renders_dir):
        raise FileNotFoundError(f"{renders_dir}/ nicht gefunden! "
                                f"Führe erst render.py aus.")

    os.makedirs(final_dir, exist_ok=True)

    wav_files = sorted(Path(renders_dir).glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"Keine *.wav in {renders_dir}/ gefunden!")

    logger.info(f"Found {len(wav_files)} WAV files")

    for i, wav_path in enumerate(wav_files, 1):
        try:
            stem = validate_filename_stem(wav_path.stem)
        except ValueError as e:
            logger.warning(f"[{i}/{len(wav_files)}] Skipping {wav_path.name}: {e}")
            continue

        aac_path = os.path.join(final_dir, f"{stem}.m4a")
        mp3_path = os.path.join(final_dir, f"{stem}.mp3")

        logger.info(f"[{i}/{len(wav_files)}] Converting: {stem}")

        if convert_wav_to_aac(str(wav_path), aac_path):
            logger.info(f"✓ AAC: {aac_path}")
        else:
            logger.error(f"✗ AAC conversion failed: {aac_path}")

        if convert_wav_to_mp3(str(wav_path), mp3_path):
            logger.info(f"✓ MP3: {mp3_path}")
        else:
            logger.error(f"✗ MP3 conversion failed: {mp3_path}")

    logger.info(f"✓ Conversion complete. All files in ./{final_dir}/")


if __name__ == "__main__":
    logger.info("WAV → AAC + MP3 conversion with loudness normalization")

    # Check ffmpeg available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except FileNotFoundError:
        logger.critical("ffmpeg not found! Install with: apt-get install ffmpeg")
        raise RuntimeError("ffmpeg not found")

    batch_convert(RENDERS_DIR, FINAL_DIR)

    logger.info(f"Output files: ./{FINAL_DIR}/*.m4a (AAC) and ./{FINAL_DIR}/*.mp3 (MP3)")

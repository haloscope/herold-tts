#!/usr/bin/env python3
"""
convert.py - Batch conversion to AAC and MP3.

Pipeline:
1. Read ./renders/*.wav (24 kHz, from render.py)
2. Normalize loudness (EBU R128, -23 LUFS, typical for broadcast)
3. Save both output formats:
   - ./final/*.m4a (AAC, ~192 kbps)
   - ./final/*.mp3 (MP3, ~192 kbps VBR)

Output: ./final/<id>.m4a and ./final/<id>.mp3
"""

import os
import re
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .logger import setup_logger
from .config import config

logger = setup_logger(__name__)

# --- Configuration -----------------------------------------------------------

RENDERS_DIR = config.renders_dir
FINAL_DIR = config.final_dir

# ffmpeg parameters
AAC_CODEC = config.aac_codec
AAC_BITRATE = config.aac_bitrate
MP3_VBR = config.mp3_vbr

# EBU R128 loudness target
LOUDNESS_TARGET = config.loudness_target

# --- Funktionen ---------------------------------------------------------------


def validate_filename_stem(stem: str) -> str:
    """Allow only alphanumeric, underscore, hyphen (Path Traversal protection)."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', stem):
        raise ValueError(f"Invalid filename stem: {stem}")
    return stem


def get_loudness_filter(target_lufs="-23"):
    """ffmpeg loudnorm filter: normalize to target loudness (EBU R128)."""
    return f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"


def convert_wav_to_aac(wav_path, output_path, loudness_target="-23"):
    """Convert WAV to AAC with loudness normalization."""
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
    """Convert WAV to MP3 with loudness normalization."""
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


def batch_convert(renders_dir, final_dir, max_workers=4):
    """
    Parallel batch conversion: all *.wav → m4a + mp3 (ThreadPoolExecutor).
    """
    logger.info(f"Batch conversion: {renders_dir}/ → {final_dir}/ (max_workers={max_workers})")

    if not os.path.isdir(renders_dir):
        raise FileNotFoundError(f"{renders_dir}/ not found! Run render.py first.")

    os.makedirs(final_dir, exist_ok=True)

    wav_files = sorted(Path(renders_dir).glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"No *.wav files in {renders_dir}/")

    logger.info(f"Found {len(wav_files)} WAV files")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        total_tasks = 0

        # Submit all conversion tasks (AAC + MP3 per file)
        for i, wav_path in enumerate(wav_files, 1):
            try:
                stem = validate_filename_stem(wav_path.stem)
            except ValueError as e:
                logger.warning(f"[{i}/{len(wav_files)}] Skipping {wav_path.name}: {e}")
                continue

            aac_path = os.path.join(final_dir, f"{stem}.m4a")
            mp3_path = os.path.join(final_dir, f"{stem}.mp3")

            logger.info(f"[{i}/{len(wav_files)}] Submitted: {stem}")

            # Submit both conversions (non-blocking)
            f_aac = executor.submit(convert_wav_to_aac, str(wav_path), aac_path)
            f_mp3 = executor.submit(convert_wav_to_mp3, str(wav_path), mp3_path)

            futures[f_aac] = ("AAC", stem, aac_path)
            futures[f_mp3] = ("MP3", stem, mp3_path)
            total_tasks += 2

        # Wait for all tasks to complete
        completed = 0
        for future in as_completed(futures):
            fmt, stem, path = futures[future]
            completed += 1
            try:
                result = future.result()
                if result:
                    logger.info(f"✓ [{completed}/{total_tasks}] {fmt}: {stem}")
                else:
                    logger.error(f"✗ [{completed}/{total_tasks}] {fmt} failed: {stem}")
            except Exception as e:
                logger.error(f"✗ [{completed}/{total_tasks}] {fmt} error: {e}", exc_info=True)

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

"""Centralized configuration for Herold-TTS scripts."""

import os
import torch
from pathlib import Path
from dataclasses import dataclass

# Project root (parent of herold/ package)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def get_device():
    """Auto-detect device: prefer TTS_DEVICE env var, fallback to CUDA or CPU."""
    if "TTS_DEVICE" in os.environ:
        return os.environ["TTS_DEVICE"]
    return "cuda:0" if torch.cuda.is_available() else "cpu"


@dataclass
class TTSConfig:
    """TTS Configuration (centralized)."""

    # Device & Model
    device: str = get_device()
    dtype: torch.dtype = torch.bfloat16
    attn_implementation: str = "sdpa"

    # Directories (resolved to PROJECT_ROOT)
    audition_dir: str = None
    renders_dir: str = None
    final_dir: str = None

    # Audio
    sample_rate: int = 24000
    loudness_target: str = "-23"  # LUFS
    pause_duration: float = 2.0  # seconds between EN and DE

    # Conversion
    aac_codec: str = "aac"
    aac_bitrate: str = "192k"
    mp3_vbr: str = "2"  # 0=best, 9=worst; 2 ≈ 190 kbps VBR

    # Files (resolved to PROJECT_ROOT)
    ansagen_file: str = None
    clone_prompt_file: str = "voice_clone_prompt.json"
    ref_audio_file: str = None  # Will be set to os.path.join(audition_dir, "reference_design_de.wav")

    # Reference voice text
    ref_text_de: str = (
        "Hallo, ich freue mich Sie auf Oskar begrüßen zu dürfen! "
        "Hierbei handelt es sich um die Open Source Kommunikations Plattform Schleswig-Holsteins"
    )

    def __post_init__(self):
        if self.audition_dir is None:
            self.audition_dir = str(PROJECT_ROOT / "data" / "audition")
        if self.renders_dir is None:
            self.renders_dir = str(PROJECT_ROOT / "data" / "renders")
        if self.final_dir is None:
            self.final_dir = str(PROJECT_ROOT / "data" / "final")
        if self.ansagen_file is None:
            self.ansagen_file = str(PROJECT_ROOT / "resources" / "ansagen.yaml")
        if self.ref_audio_file is None:
            self.ref_audio_file = os.path.join(self.audition_dir, "reference_design_de.wav")


# Global config instance
config = TTSConfig()

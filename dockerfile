# Qwen3-TTS für Blackwell (sm_120)
# WICHTIG: CUDA 12.8 ist Pflicht. Ältere Images (12.1 / 12.4) laufen auf Blackwell
# Karten NICHT ("no kernel image available for execution on the device").
# runtime (NICHT devel): wir kompilieren nichts, PyTorch cu128 bringt CUDA+cuDNN
# selbst mit. devel würde nur fette statische Libs mitschleppen (~3x Größe).
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3-pip \
        ffmpeg sox git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Isoliertes venv, hält das System-Python sauber
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# PyTorch + torchaudio mit CUDA 12.8 (Blackwell-fähig) ZUERST und als PAAR
# installieren. Wichtig: torchaudio MUSS mit, sonst zieht der spätere
# qwen-tts-Install eine CUDA-13-torchaudio nach -> Mismatch
# (libcudart.so.13 fehlt, torchaudio crasht beim Laden).
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu128

# Qwen3-TTS Laufzeit + WAV-IO + YAML-Support
RUN pip install --no-cache-dir qwen-tts soundfile pyyaml

# HuggingFace-Cache auf gemountetes Volume -> Modelle nur einmal herunterladen
ENV HF_HOME=/cache/hf

WORKDIR /work
CMD ["bash"]

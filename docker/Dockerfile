# OSKAR-TTS: GPU-optimized Docker image (CUDA 12.8, PyTorch)
# Multi-stage build for minimal final image size
# Non-root user for security hardening

# ============================================================================
# Stage 1: Builder (large, contains compile toolchain)
# ============================================================================
FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04 AS builder

LABEL maintainer="OSKAR-TTS Project"
LABEL description="OSKAR-TTS: Open Source Text-to-Speech with voice cloning"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    build-essential \
    git \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip, setuptools, wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# qwen-tts installed separately with --no-deps: its own dependency resolution
# pulls an incompatible torchaudio, breaking the cu128 torch/torchaudio pair above.
# Its remaining dependencies (everything except torchaudio) are installed explicitly.
RUN pip install --no-cache-dir --no-deps qwen-tts && \
    pip install --no-cache-dir \
        "transformers==4.57.3" \
        "accelerate==1.12.0" \
        gradio \
        librosa \
        onnxruntime \
        einops \
        sox

# ============================================================================
# Stage 2: Runtime (minimal, only runtime deps)
# ============================================================================
FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04

LABEL maintainer="OSKAR-TTS Project"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r oskar && useradd -r -g oskar oskar

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY herold/ /app/herold/
COPY resources/ /app/resources/
COPY requirements.txt /app/

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    CUDA_DEVICE_ORDER=PCI_BUS_ID \
    NVIDIA_VISIBLE_DEVICES=all \
    NUMBA_CACHE_DIR=/tmp/numba_cache \
    HF_HOME=/app/.cache/huggingface

# Health check: light HTTP probe against the API. Importing herold.render here
# (pre-v0.4.1) loaded the full torch/qwen-tts stack on every probe — CPU-intensive
# and >10s on slower hosts, flagging healthy containers unhealthy. start-period
# covers the API's slow first import.
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status', timeout=5)" || exit 1

# Change ownership to non-root user
RUN chown -R oskar:oskar /app

# Switch to non-root user
USER oskar

# Default command: bash (can be overridden)
CMD ["/bin/bash"]

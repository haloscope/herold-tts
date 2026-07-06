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
    NVIDIA_VISIBLE_DEVICES=all

# Health check: verify package is importable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "from herold.render import render_batch; print('OK')" || exit 1

# Change ownership to non-root user
RUN chown -R oskar:oskar /app

# Switch to non-root user
USER oskar

# Default command: bash (can be overridden)
CMD ["/bin/bash"]

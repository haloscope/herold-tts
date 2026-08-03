# Herold-TTS Deployment Guide

Production-ready deployment of Herold-TTS with Docker, GPU/CPU support, and REST API.

## Quick Start

### Docker (GPU)

```bash
# Build image
docker build -t herold-tts:latest .

# Run with GPU
docker run --gpus all -it \
  -v $(pwd)/audition:/app/audition \
  -v $(pwd)/renders:/app/renders \
  -v $(pwd)/final:/app/final \
  herold-tts:latest

# Or use docker-compose
docker-compose up herold-tts-gpu
```

### Docker (CPU-only)

```bash
docker build -f Dockerfile.cpu -t herold-tts:cpu .
docker run -it \
  -e TTS_DEVICE=cpu \
  -v $(pwd)/audition:/app/audition \
  -v $(pwd)/renders:/app/renders \
  -v $(pwd)/final:/app/final \
  herold-tts:cpu
```

### Volume Permissions (required before first run)

The container runs as a non-root user (`oskar` in the GPU image, `herold` in the CPU image,
both uid `999`). Docker auto-creates missing bind-mount source directories on the **host** as
`root:root`, which the non-root container user cannot write to — `audition.py`/`render.py`/
`convert.py` will fail with a generic `LibsndfileError: ... System error.` when saving WAV files.

Before the first run, make sure the host-side data directories are owned by uid `999`:

```bash
mkdir -p data/audition data/renders data/final
chown -R 999:999 data/
```

If you don't have host `chown` permissions, fix it from inside a running container instead
(container root has host-root file permissions on the bind mount as long as no user-namespace
remapping is configured):

```bash
docker compose exec --user root herold-tts-gpu chown -R oskar:oskar /app/data
```

---

## REST API

Start the API server:

```bash
cd work
python api.py
# or: uvicorn api:app --host 0.0.0.0 --port 8000
```

### Endpoints

#### Health Check
```bash
curl http://localhost:8000/api/status
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-07-06T12:34:56.789012",
  "device": "cuda:0",
  "service": "Herold-TTS API",
  "version": "0.2.0"
}
```

#### Render Announcements (Async)
```bash
curl -X POST http://localhost:8000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "ansagen": [
      {
        "id": "welcome",
        "text_de": "Willkommen!",
        "text_en": "Welcome!"
      }
    ]
  }'
```

Response (202 Accepted):
```json
{
  "status": "accepted",
  "message": "Rendering started",
  "count": 1,
  "output_dir": "renders"
}
```

#### Convert WAV to AAC/MP3 (Async)
```bash
curl -X POST http://localhost:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{"filter_pattern": "*.wav"}'
```

### Interactive Docs

Open http://localhost:8000/docs for Swagger UI (try endpoints in browser).

---

## System Requirements

### GPU (NVIDIA)
- **GPU**: RTX 4090, RTX 5090, A100, or similar (compute capability >= 8.0)
- **CUDA**: 12.8 (included in container)
- **VRAM**: 12+ GB (9 GB for model + buffers)
- **Container Toolkit**: Required for Docker GPU support

```bash
# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.8.1-runtime-ubuntu24.04 nvidia-smi
```

### CPU-only
- **RAM**: 32+ GB recommended (model + batch buffers)
- **CPU**: 8+ cores
- **Expected**: ~10-15x slower than GPU

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_DEVICE` | `cuda:0` if CUDA available, else `cpu` | Device (`cuda:0`, `cpu`, etc.) |
| `PYTHONUNBUFFERED` | `1` | Unbuffered logging |
| `CUDA_DEVICE_ORDER` | `PCI_BUS_ID` | GPU device ordering |

```bash
# Override device at runtime
docker run -e TTS_DEVICE=cuda:1 herold-tts:latest
docker run -e TTS_DEVICE=cpu herold-tts:cpu
```

---

## Performance Baseline

**Superseded** — the numbers previously here (RTX 5090, "~18 sec" audition, "~90 sec per
announcement pair") were estimates, not measurements, and didn't hold up against an actual
end-to-end run (measured GPU throughput was faster: ~9-11 sec per synthesis, not ~90 sec).

See **[docs/HARDWARE.md](HARDWARE.md)** for measured hardware requirements, disk space, tokens/sec,
and render time expectations on both GPU and CPU, including the exact commands to reproduce the
measurements yourself.

---

## Troubleshooting

### NVIDIA Container Toolkit Missing
```
docker: Error response from daemon: could not select device driver "" with capabilities [[gpu]]
```

**Fix**:
```bash
# Install NVIDIA Container Toolkit (Ubuntu)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### CUDA Out of Memory
- Reduce batch size (edit `config.py`)
- Use CPU-only variant
- Increase VRAM or use smaller model

### ffmpeg Not Found
```
RuntimeError: ffmpeg not found! Install with: apt-get install ffmpeg
```

**Fix**: Already included in Docker image. If running locally, install ffmpeg.

---

## Production Checklist

- [ ] Test on target hardware (GPU model, VRAM)
- [ ] Verify health endpoint (`/api/status`)
- [ ] Render test announcement, validate output
- [ ] Convert test WAV, check loudness (-23 LUFS)
- [ ] Set resource limits (`docker-compose` resource section)
- [ ] Configure logging aggregation (ELK, CloudWatch, etc.)
- [ ] Set up monitoring (health checks, GPU metrics)
- [ ] Document `ansagen.yaml` structure for users
- [ ] Backup `audition/`, `renders/`, `final/` volumes

---

## Scaling & Optimization

### Multi-GPU
```bash
docker run --gpus all \  # all GPUs
  -e TTS_DEVICE=cuda:0 \
  herold-tts:latest
```

Or use load balancer (nginx, Traefik) in front of multiple API instances.

### Caching
- Models are cached in-memory per process
- Run single API instance per container for best caching
- Multi-instance setup: each gets own model cache

### Volume Mounts
- `audition/` — read-only reference voices
- `renders/` — read-write WAV outputs
- `final/` — read-write final AAC/MP3

Consider S3 or network storage for production.

---

## Next Steps

1. **Test locally** with Docker
2. **Deploy API** on production server
3. **Monitor** GPU/CPU metrics
4. **Scale** with load balancer if needed
5. **Integrate** with existing systems via REST API

See API docs at `/docs` (Swagger UI) when service is running.


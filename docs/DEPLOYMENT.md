# Herold-TTS Deployment Guide

Production-ready deployment of Herold-TTS with Docker, GPU/CPU support, and REST API.

## Quick Start

### Docker (GPU)

```bash
docker compose build
docker compose up -d
# API + demo web frontend on http://localhost:8000/
```

Manual build without compose:

```bash
docker build -f docker/Dockerfile -t herold-tts:latest .
docker run --gpus all -p 8000:8000 \
  -v $(pwd)/data/audition:/app/data/audition \
  -v $(pwd)/data/renders:/app/data/renders \
  -v $(pwd)/data/final:/app/data/final \
  -v $(pwd)/data/hf-cache:/app/.cache/huggingface \
  herold-tts:latest python -m herold.api
```

### Docker (CPU-only)

The CPU variant is wired up as a Compose profile (not started by default). On a CPU-only host, **name the CPU service explicitly**; otherwise Compose also starts the default GPU service:

```bash
docker compose --profile cpu build herold-tts-cpu
docker compose --profile cpu up -d herold-tts-cpu
# API + demo web frontend on http://localhost:8001/
```

Manual build without compose: as above, but with `-f docker/Dockerfile.cpu`,
image tag `herold-tts:cpu`, `-e TTS_DEVICE=cpu` and without `--gpus`.

### Volume Permissions (required before first run)

The container runs as a non-root user (`oskar` in the GPU image, `herold` in the CPU image,
both uid `999`). Docker auto-creates missing bind-mount source directories on the **host** as
`root:root`, which the non-root container user cannot write to — `audition.py`/`render.py`/
`convert.py` will fail with a generic `LibsndfileError: ... System error.` when saving WAV files.

Before the first run, make sure the host-side data directories are owned by uid `999`:

```bash
mkdir -p data/audition data/renders data/final data/hf-cache
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

Start the API server (inside the container this is the default `command`):

```bash
python -m herold.api
# or: uvicorn herold.api:app --host 0.0.0.0 --port 8000
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
  "timestamp": "2026-08-03T12:34:56.789012",
  "device": "cuda:0",
  "service": "Herold-TTS API",
  "version": "0.4.0"
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
  "job_id": "3f2a9c1d40be",
  "count": 1,
  "output_dir": "/app/data/renders"
}
```

#### Poll Job Status
```bash
curl http://localhost:8000/api/jobs/3f2a9c1d40be
```

Response (`status` is one of `queued | running | done | failed`):
```json
{
  "job_id": "3f2a9c1d40be",
  "kind": "render",
  "status": "done",
  "created_at": "2026-08-03T12:35:01.123456",
  "items": ["welcome"],
  "error": null
}
```

The registry is in-memory: job state is lost on restart and not shared between
instances (see `docs/adr/0002`).

#### Convert WAV to AAC/MP3 (Async)
```bash
curl -X POST http://localhost:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{"filter_pattern": "*.wav"}'
```

Also returns a `job_id` (poll as above).

#### List & Download Result Files
```bash
curl http://localhost:8000/api/files
curl -O http://localhost:8000/api/files/renders/welcome_en.wav
curl -O http://localhost:8000/api/files/final/welcome_en.mp3
```

`renders/` serves `.wav`, `final/` serves `.m4a`/`.mp3`; filenames are validated
against path traversal.

### Demo Web Frontend

`http://localhost:8000/` (redirects to `/demo/`) serves a self-contained example
web page that exercises exactly this API: render form → job polling → audio
players → convert → downloads. Intended as an integration blueprint.

### Interactive Docs

Open http://localhost:8000/docs for Swagger UI (try endpoints in browser).

---

## CI/CD (GitLab)

Since v0.4.2 the images are built by the project's own GitLab runners (see
`.gitlab-ci.yml` and `docs/adr/0003`): every push runs pytest; pushes to `main`
additionally build both images and push them to the project's Container Registry as
`<registry>/…/herold-tts/gpu:<version|latest>` and `…/cpu:<version|latest>`. The registry
keeps only the current and previous version per image (`latest` always remains).

Target machines should pull instead of building. Note the `docker tag` step:
`docker-compose.yml` references the local image names `herold-tts:latest` /
`herold-tts:cpu`, so the pulled registry images must be tagged accordingly —
otherwise `docker compose up` triggers a local build despite the pull:

```bash
docker login registry.git.lab    # once; PAT with read_registry as password
docker pull registry.git.lab/dataport/herold-tts/gpu:latest
docker tag  registry.git.lab/dataport/herold-tts/gpu:latest herold-tts:latest
# CPU variant (compose profile "cpu", port 8001):
docker pull registry.git.lab/dataport/herold-tts/cpu:latest
docker tag  registry.git.lab/dataport/herold-tts/cpu:latest herold-tts:cpu
```

One-time setup: enable the Container Registry in the project and create the CI/CD
variable `REGISTRY_CLEANUP_TOKEN` (project access token, Maintainer role, scope `api`,
masked). Local builds (sections above) remain the documented fallback.

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

### `[Errno 5] Input/output error` when loading the Qwen3-TTS model

OS-level I/O error during model download/load (render job fails, traceback in
`docker logs herold-tts-gpu`). The line *above* the errno tells you which case:
`download`/`hf_hub`/`xet` → error while downloading; `safetensors`/`mmap` →
error while reading already-cached files. Check in this order:

1. **Disk full (most common):** `df -h ~` and `docker system df`. Old images +
   new image + 3.8 GB model add up fast. Clean up: `docker rmi herold-tts:cpu`
   (unused on the GPU box), `docker image prune` (dangling images after retag).
2. **Corrupted/partial model download in the cache:** stale half-downloaded
   files in `data/hf-cache/` cause I/O errors on reuse. Fix (costs one
   re-download of ~3.8 GB):
   ```bash
   docker compose down && sudo rm -rf data/hf-cache/* && docker compose up -d
   ```
3. **Actual disk/filesystem fault:** `sudo dmesg --ctime | tail -25` — NVMe or
   EXT4 errors there mean a hardware problem; stop writing and investigate the
   disk before continuing.

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


# Hardware Requirements & Performance

Measured numbers from an actual end-to-end run of the pipeline (audition → render → convert),
not vendor estimates. Test rig used for all measurements below:

- **GPU host:** NVIDIA GeForce RTX 5090 (32 GB VRAM), CUDA 12.8, torch 2.12.1+cu130
- **CPU host:** Intel Core Ultra 9 285K (24 threads), 32 GB RAM
- Model: `Qwen/Qwen3-TTS-12Hz-1.7B-*` (Base/CustomVoice/VoiceDesign), `dtype=bfloat16` (fixed in
  `herold/config.py`, same on GPU and CPU)

Your numbers will vary with GPU/CPU model, text length, and language — treat the tables below as
calibration points, not guarantees.

---

## Disk Space

| Item | Size | Notes |
|---|---|---|
| `herold-tts:latest` (GPU image) | 15.3 GB total / 5.4 GB content | multi-stage build, CUDA 12.8 base |
| `herold-tts:cpu` (CPU image) | 9.8 GB total / 3.3 GB content | `ubuntu:24.04` base, no CUDA |
| Each `Qwen3-TTS-12Hz-1.7B-*` model | ~3.8 GB | per SBOM.md; downloaded from HuggingFace on first use |
| Full `audition.py` run (3 models: CustomVoice, VoiceDesign, Base) | ~11 GB | HF cache under `HF_HOME=/app/.cache/huggingface` |
| Production `render.py` (Base model only) | ~3.8 GB | if you skip `audition.py`'s other candidates |
| WAV output (24 kHz, 16-bit, mono) | ~46.9 KB per second of audio | `sample_rate × 2 bytes` exactly |
| AAC output (`.m4a`, 192 kbps) | ~24 KB per second of audio | measured: 8.64 s → 212 KB |
| MP3 output (VBR ~192 kbps) | ~11 KB per second of audio | measured: 8.64 s → 94 KB |

**Important:** the HuggingFace cache (`HF_HOME=/app/.cache/huggingface`) is **not** a mounted
volume in `docker-compose.yml` — it lives inside the container's writable layer. Every
`docker compose build` + container recreate throws it away, forcing a full re-download (~3.8–11 GB)
on the next `audition`/`render` run. If you rebuild often, add a volume mount for it, e.g.:

```yaml
volumes:
  - ./data/hf-cache:/app/.cache/huggingface
```

---

## GPU Requirements

- **VRAM observed:** 8.2 GB (CustomVoice inference) to 13 GB (VoiceDesign phase) for a single
  loaded 1.7B model — README's "12+ GB recommended" is a reasonable floor; more headroom needed
  if you keep multiple model variants loaded simultaneously (as `audition.py` does)
- **Compute:** any CUDA 12.8-capable GPU (compute capability ≥ 8.0, per `docs/DEPLOYMENT.md`)

## CPU Requirements

- **RAM:** not measured for peak usage in this session; the host had 32 GB total and did not swap.
  Treat 32 GB as the practical floor for a 1.7B model at bf16 plus OS/Docker overhead.
- **Threads:** `docker/Dockerfile.cpu` sets `OMP_NUM_THREADS=4` / `MKL_NUM_THREADS=4` (fixed in
  v0.3.3 — previously set the non-functional `TORCH_NUM_THREADS`, which PyTorch never reads, so
  earlier CPU runs silently used **all** host cores instead of the intended 4)

---

## Render Performance

### What "tokens" means here

`Qwen3-TTS-12Hz` generates acoustic tokens at a fixed rate of **12 tokens per second of output
audio** (the "12Hz" in the model name). Token count is therefore derived directly from output
audio duration: `tokens = audio_seconds × 12`. This is a better cross-run comparison metric than
input character count, since generation cost scales with audio output, not input text.

### GPU — RTX 5090 (measured, `render.py` batch of 3 announcements)

| Item | Input chars | Output audio | Acoustic tokens | Wall time | Tokens/sec |
|---|---|---|---|---|---|
| `unavailable_en` | 99 | 6.80 s | 82 | 7.49 s | 10.9 |
| `welcome_de` | 144 | 10.00 s | 120 | 11.77 s | 10.2 |
| `unavailable_de` | 153 | 10.64 s | 128 | 13.55 s | 9.4 |
| `voicemail_de` | 153 | 10.40 s | 125 | 13.37 s | 9.3 |
| `voicemail_en` | 129 | 8.48 s | 102 | 11.69 s | 8.7 |

**Average: ~9.7 tokens/sec, i.e. real-time factor ≈ 0.8×** (generating 10 s of audio takes ~11–14 s
wall time on this GPU). One-time overhead per `render.py` invocation (model load from cache +
reference load + voice-clone-prompt creation): ~10–15 s, paid once per process, not per item.

**Extrapolation** (3-announcement batch = 9 files done in ~68 s wall time end-to-end on this rig):

| Announcements | Est. wall time (GPU, warm cache) |
|---|---|
| 1 | ~25–35 s |
| 3 (current `ansagen.yaml`) | ~1–1.5 min |
| 10 | ~4–5 min |

This is **much faster** than the older estimate in `docs/DEPLOYMENT.md` ("10 announcements:
~15 min", "~90 sec per announcement pair") — that figure predates this measurement and should be
treated as superseded for RTX 5090-class hardware.

### CPU — Intel Ultra 9 285K (measured, single announcement via `/api/render`)

| Item | Input chars | Output audio | Acoustic tokens | Wall time | Tokens/sec |
|---|---|---|---|---|---|
| `cputest_unavailable_de` | 153 | 9.84 s | 118 | 41.2 s | 2.9 |

**Caveat:** this measurement was taken **before** the v0.3.3 thread-limit fix — PyTorch was
using all 24 host cores (`TORCH_NUM_THREADS` was silently ignored), not the intended 4. It
represents a best-case, not the throughput you'll get from the now-fixed `OMP_NUM_THREADS=4`
image. Full pipeline for this one item (model load + reference + EN + DE + combine) took
**~2 min 39 s wall clock** total — again, on unrestricted 24 cores.

**Not yet re-measured:** CPU performance after the `OMP_NUM_THREADS=4`/`MKL_NUM_THREADS=4` fix.
Expect it to be slower than the numbers above, plausibly in the direction of the vendor estimate
in `docs/DEPLOYMENT.md` ("~10–15× slower than GPU") for a 4-thread-limited run, but this has not
been benchmarked — re-run the CPU smoke test and update this section if you need a reliable number.

---

## Reproducing These Measurements

```bash
docker compose up -d herold-tts-gpu
docker compose exec herold-tts-gpu python -m herold.audition   # one-time, produces reference_design_de.wav
docker compose exec herold-tts-gpu python -m herold.render     # renders resources/ansagen.yaml
stat --format='%n %y' data/renders/*.wav                        # precise per-file timestamps
```

WAV duration from any file without extra tooling (header is fixed PCM, 24 kHz/16-bit/mono):

```bash
od -An -tu4 -j40 -N4 data/renders/welcome_en.wav   # data chunk size in bytes
# duration_seconds = data_chunk_bytes / 48000
```

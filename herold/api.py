#!/usr/bin/env python3
"""
Herold-TTS FastAPI Service

REST API for batch TTS rendering:
- POST /api/render — render announcements (WAV), returns job_id
- POST /api/convert — convert WAV to AAC/MP3, returns job_id
- GET /api/jobs/{job_id} — poll job status
- GET /api/files — list rendered/converted audio files
- GET /api/files/{dirname}/{filename} — download a single audio file
- GET /api/status — check service health
- /demo — example web frontend built on this API
"""

import threading
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime
from . import __version__
from .logger import setup_logger
from .config import config
from .render import render_batch, load_yaml, AnsageEntry
from .convert import batch_convert, validate_filename_stem

logger = setup_logger(__name__)

app = FastAPI(
    title="Herold-TTS API",
    description="Text-to-Speech with voice cloning",
    version=__version__,
)

# ============================================================================
# Job registry (in-memory, single instance — see docs/adr/0002)
# ============================================================================

jobs = {}
_jobs_lock = threading.Lock()


def _create_job(kind, items):
    """Register a new job and return its id."""
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "items": items,
            "error": None,
        }
    return job_id


def _set_job(job_id, **fields):
    with _jobs_lock:
        jobs[job_id].update(fields)


def _run_job(job_id, func, *args):
    """Background wrapper: track status and capture failures."""
    _set_job(job_id, status="running")
    try:
        func(*args)
        _set_job(job_id, status="done")
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        _set_job(job_id, status="failed", error=str(e))


# ============================================================================
# File access (download endpoints for renders/final)
# ============================================================================

# dirname → (base dir from config, allowed extensions, media types)
FILE_DIRS = {
    "renders": (lambda: config.renders_dir, {".wav"}),
    "final": (lambda: config.final_dir, {".m4a", ".mp3"}),
}

MEDIA_TYPES = {".wav": "audio/wav", ".m4a": "audio/mp4", ".mp3": "audio/mpeg"}

# ============================================================================
# Models
# ============================================================================

class AnsageRequest(BaseModel):
    id: str = Field(..., description="Unique announcement ID")
    text_de: str = Field(..., description="German text")
    text_en: str = Field(..., description="English text")


class RenderRequest(BaseModel):
    ansagen: List[AnsageRequest] = Field(..., description="List of announcements to render")


class ConvertRequest(BaseModel):
    filter_pattern: str = Field("*.wav", description="WAV file pattern to convert")


class StatusResponse(BaseModel):
    status: str
    timestamp: str
    device: str
    service: str = "Herold-TTS API"
    version: str = __version__


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the example web frontend."""
    return RedirectResponse(url="/demo/")


@app.get("/api/status", response_model=StatusResponse)
async def status():
    """Health check endpoint."""
    return StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        device=config.device,
    )


@app.post("/api/render")
async def render(request: RenderRequest, background_tasks: BackgroundTasks):
    """
    Render announcements (WAV format).

    Returns a job_id (async, renders in background — poll /api/jobs/{job_id}).
    """
    logger.info(f"Render request: {len(request.ansagen)} announcements")

    try:
        # Validate announcements
        ansagen_list = [
            AnsageEntry(
                id=a.id,
                text_de=a.text_de,
                text_en=a.text_en,
            )
            for a in request.ansagen
        ]

        # Run rendering in background, tracked as a job
        job_id = _create_job("render", [a.id for a in ansagen_list])
        background_tasks.add_task(_run_job, job_id, render_batch, ansagen_list)

        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Rendering started",
                "job_id": job_id,
                "count": len(ansagen_list),
                "output_dir": config.renders_dir,
            },
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Render error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/convert")
async def convert(request: ConvertRequest, background_tasks: BackgroundTasks):
    """
    Convert WAV files to AAC + MP3 (parallel).

    Returns a job_id (async, converts in background — poll /api/jobs/{job_id}).
    """
    logger.info(f"Convert request: pattern={request.filter_pattern}")

    try:
        # Run conversion in background, tracked as a job
        job_id = _create_job("convert", [])
        background_tasks.add_task(
            _run_job, job_id, batch_convert, config.renders_dir, config.final_dir
        )

        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Conversion started",
                "job_id": job_id,
                "renders_dir": config.renders_dir,
                "output_dir": config.final_dir,
            },
        )

    except Exception as e:
        logger.error(f"Convert error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    """Status of a render/convert job (queued | running | done | failed)."""
    with _jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    return job


@app.get("/api/files")
async def list_files():
    """List rendered WAVs (renders/) and converted AAC/MP3 files (final/)."""
    files = []
    for dirname, (get_dir, exts) in FILE_DIRS.items():
        base = Path(get_dir())
        if not base.is_dir():
            continue
        for f in sorted(base.iterdir()):
            if f.is_file() and f.suffix in exts:
                st = f.stat()
                files.append({
                    "dir": dirname,
                    "name": f.name,
                    "size": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                    "url": f"/api/files/{dirname}/{f.name}",
                })
    return {"files": files}


@app.get("/api/files/{dirname}/{filename}")
async def get_file(dirname: str, filename: str):
    """Download a single audio file from renders/ or final/."""
    if dirname not in FILE_DIRS:
        raise HTTPException(status_code=404, detail=f"Unknown directory: {dirname}")

    get_dir, exts = FILE_DIRS[dirname]
    suffix = Path(filename).suffix
    if suffix not in exts:
        raise HTTPException(status_code=404, detail=f"Unsupported file type: {suffix}")

    try:
        validate_filename_stem(Path(filename).stem)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = Path(get_dir()) / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    return FileResponse(file_path, media_type=MEDIA_TYPES[suffix], filename=filename)


@app.get("/api/docs", include_in_schema=False)
async def docs_redirect():
    """Redirect to interactive API documentation."""
    return {
        "message": "Use /docs for interactive Swagger UI",
        "docs_url": "/docs",
    }


# ============================================================================
# Example web frontend (static, uses only the public API endpoints)
# ============================================================================

app.mount("/demo", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="demo")


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info(f"Herold-TTS API starting on device: {config.device}")
    Path(config.renders_dir).mkdir(parents=True, exist_ok=True)
    Path(config.final_dir).mkdir(parents=True, exist_ok=True)


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Herold-TTS API shutting down")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Herold-TTS API server...")
    uvicorn.run(
        "herold.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )

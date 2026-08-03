#!/usr/bin/env python3
"""
Herold-TTS FastAPI Service

REST API for batch TTS rendering:
- POST /api/render — render announcements (WAV)
- POST /api/convert — convert WAV to AAC/MP3
- GET /api/status — check service health
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import os
from datetime import datetime
from . import __version__
from .logger import setup_logger
from .config import config
from .render import render_batch, load_yaml, AnsageEntry
from .convert import batch_convert

logger = setup_logger(__name__)

app = FastAPI(
    title="Herold-TTS API",
    description="Text-to-Speech with voice cloning",
    version=__version__,
)

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
    """Redirect to interactive API documentation."""
    return RedirectResponse(url="/docs")


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
    
    Returns job info (async, renders in background).
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

        # Run rendering in background
        background_tasks.add_task(
            render_batch,
            ansagen_list,
        )

        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Rendering started",
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
    
    Returns job info (async, converts in background).
    """
    logger.info(f"Convert request: pattern={request.filter_pattern}")

    try:
        # Run conversion in background
        background_tasks.add_task(
            batch_convert,
            config.renders_dir,
            config.final_dir,
        )

        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Conversion started",
                "renders_dir": config.renders_dir,
                "output_dir": config.final_dir,
            },
        )

    except Exception as e:
        logger.error(f"Convert error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/docs", include_in_schema=False)
async def docs_redirect():
    """Redirect to interactive API documentation."""
    return {
        "message": "Use /docs for interactive Swagger UI",
        "docs_url": "/docs",
    }


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

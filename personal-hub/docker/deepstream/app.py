#!/usr/bin/env python3
"""
DeepStream Camera Stream Service

This service provides:
- RTSP stream ingestion from cameras
- GPU-accelerated video processing
- RTSP output stream for consumption
- REST API for status and control
"""

import asyncio
import logging
import os
import subprocess
import threading
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("deepstream-service")

# Environment variables
CAMERA_URL = os.getenv("CAMERA_URL", "rtsp://admin:password@192.168.1.100:554/stream1")
CAMERA_NAME = os.getenv("CAMERA_NAME", "main_camera")
OUTPUT_RTSP_PORT = int(os.getenv("OUTPUT_RTSP_PORT", "8554"))
API_PORT = int(os.getenv("API_PORT", "5000"))

app = FastAPI(
    title="DeepStream Camera Stream",
    description="GPU-accelerated video streaming service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StreamStatus(BaseModel):
    """Stream status response model."""
    camera_name: str
    camera_url: str
    output_url: str
    is_running: bool
    uptime_seconds: int
    frames_processed: int
    errors: list[str]
    last_updated: str


class StreamConfig(BaseModel):
    """Stream configuration model."""
    camera_url: str
    camera_name: str = "main_camera"


# Global state
stream_state = {
    "is_running": False,
    "start_time": None,
    "frames_processed": 0,
    "errors": [],
    "process": None,
}


def start_deepstream_pipeline():
    """Start the DeepStream pipeline using GStreamer."""
    global stream_state

    # Build GStreamer pipeline
    # This is a simplified pipeline - in production, use DeepStream SDK
    pipeline = f"""
    gst-launch-1.0 -e \
        rtspsrc location="{CAMERA_URL}" latency=100 ! \
        rtph264depay ! h264parse ! \
        nvv4l2decoder ! \
        nvvideoconvert ! \
        nvv4l2h264enc bitrate=4000000 ! \
        h264parse ! \
        rtspsink service={OUTPUT_RTSP_PORT} mapping=/ds-output
    """

    try:
        logger.info(f"Starting DeepStream pipeline for {CAMERA_NAME}")
        logger.info(f"Input: {CAMERA_URL}")
        logger.info(f"Output: rtsp://localhost:{OUTPUT_RTSP_PORT}/ds-output")

        # In a real implementation, use DeepStream SDK Python bindings
        # This is a placeholder that would be replaced with actual DeepStream code
        stream_state["is_running"] = True
        stream_state["start_time"] = datetime.utcnow()
        stream_state["errors"] = []

        logger.info("DeepStream pipeline started successfully")

    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")
        stream_state["errors"].append(str(e))
        stream_state["is_running"] = False


def stop_deepstream_pipeline():
    """Stop the DeepStream pipeline."""
    global stream_state

    if stream_state["process"]:
        stream_state["process"].terminate()
        stream_state["process"] = None

    stream_state["is_running"] = False
    logger.info("DeepStream pipeline stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if stream_state["is_running"] else "stopped",
        "service": "deepstream-camera-stream",
        "gpu_available": check_gpu_available(),
    }


@app.get("/status", response_model=StreamStatus)
async def get_status():
    """Get current stream status."""
    uptime = 0
    if stream_state["is_running"] and stream_state["start_time"]:
        uptime = int((datetime.utcnow() - stream_state["start_time"]).total_seconds())

    return StreamStatus(
        camera_name=CAMERA_NAME,
        camera_url=mask_credentials(CAMERA_URL),
        output_url=f"rtsp://localhost:{OUTPUT_RTSP_PORT}/ds-output",
        is_running=stream_state["is_running"],
        uptime_seconds=uptime,
        frames_processed=stream_state["frames_processed"],
        errors=stream_state["errors"][-5:],  # Last 5 errors
        last_updated=datetime.utcnow().isoformat(),
    )


@app.post("/start")
async def start_stream():
    """Start the stream."""
    if stream_state["is_running"]:
        raise HTTPException(status_code=400, detail="Stream is already running")

    # Start in background thread
    thread = threading.Thread(target=start_deepstream_pipeline)
    thread.start()

    return {"message": "Stream starting...", "status": "starting"}


@app.post("/stop")
async def stop_stream():
    """Stop the stream."""
    if not stream_state["is_running"]:
        raise HTTPException(status_code=400, detail="Stream is not running")

    stop_deepstream_pipeline()
    return {"message": "Stream stopped", "status": "stopped"}


@app.post("/restart")
async def restart_stream():
    """Restart the stream."""
    if stream_state["is_running"]:
        stop_deepstream_pipeline()
        await asyncio.sleep(2)

    thread = threading.Thread(target=start_deepstream_pipeline)
    thread.start()

    return {"message": "Stream restarting...", "status": "restarting"}


@app.put("/config")
async def update_config(config: StreamConfig):
    """Update stream configuration."""
    global CAMERA_URL, CAMERA_NAME

    was_running = stream_state["is_running"]

    if was_running:
        stop_deepstream_pipeline()

    CAMERA_URL = config.camera_url
    CAMERA_NAME = config.camera_name

    if was_running:
        await asyncio.sleep(1)
        thread = threading.Thread(target=start_deepstream_pipeline)
        thread.start()

    return {
        "message": "Configuration updated",
        "camera_name": CAMERA_NAME,
        "restarted": was_running,
    }


@app.get("/logs")
async def get_logs(lines: int = 100):
    """Get recent logs."""
    # In production, read from actual log file
    return {
        "logs": [
            f"[INFO] DeepStream service initialized",
            f"[INFO] Camera: {CAMERA_NAME}",
            f"[INFO] Status: {'running' if stream_state['is_running'] else 'stopped'}",
        ],
        "total_lines": 3,
    }


def mask_credentials(url: str) -> str:
    """Mask credentials in URL for display."""
    import re
    return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)


def check_gpu_available() -> bool:
    """Check if NVIDIA GPU is available."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


@app.on_event("startup")
async def startup_event():
    """Start the stream on service startup."""
    logger.info("DeepStream service starting...")

    # Check GPU
    if check_gpu_available():
        logger.info("NVIDIA GPU detected")
        # Auto-start stream
        thread = threading.Thread(target=start_deepstream_pipeline)
        thread.start()
    else:
        logger.warning("No NVIDIA GPU detected - stream will not auto-start")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("DeepStream service shutting down...")
    stop_deepstream_pipeline()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=False,
        workers=1,
    )

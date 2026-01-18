#!/usr/bin/env python3
"""
Person Detection Service

This service provides:
- Person detection using YOLO models
- Image upload detection
- Stream snapshot detection
- GPU acceleration when available
"""

import base64
import io
import logging
import os
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel
from ultralytics import YOLO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("person-detection")

# Environment variables
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("DETECTION_CONFIDENCE", "0.5"))
IOU_THRESHOLD = float(os.getenv("DETECTION_IOU_THRESHOLD", "0.45"))
USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"
MODEL_DIR = os.getenv("MODEL_DIR", "/app/models")

app = FastAPI(
    title="Person Detection API",
    description="AI-powered person detection using YOLO",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global model instance
model: Optional[YOLO] = None
device: str = "cpu"
model_info = {
    "name": YOLO_MODEL,
    "loaded": False,
    "load_time": None,
    "device": "cpu",
}


class Detection(BaseModel):
    """Single detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]
    center: list[float]  # [cx, cy]


class DetectionResult(BaseModel):
    """Detection response model."""
    success: bool
    detections: list[Detection]
    total_persons: int
    inference_time_ms: float
    image_size: list[int]  # [width, height]
    model: str
    device: str


class DetectionRequest(BaseModel):
    """Detection request with base64 image."""
    image: str  # Base64 encoded image
    confidence: float = CONFIDENCE_THRESHOLD
    iou: float = IOU_THRESHOLD
    return_image: bool = False


def load_model():
    """Load YOLO model."""
    global model, device, model_info

    logger.info(f"Loading model: {YOLO_MODEL}")

    # Determine device
    if USE_GPU and torch.cuda.is_available():
        device = "cuda"
        logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        logger.info("Using CPU for inference")

    # Load model
    model_path = os.path.join(MODEL_DIR, YOLO_MODEL)
    if not os.path.exists(model_path):
        # Download model if not exists
        logger.info(f"Model not found at {model_path}, downloading...")
        model_path = YOLO_MODEL

    start_time = time.time()
    model = YOLO(model_path)
    model.to(device)
    load_time = time.time() - start_time

    model_info = {
        "name": YOLO_MODEL,
        "loaded": True,
        "load_time": load_time,
        "device": device,
    }

    logger.info(f"Model loaded in {load_time:.2f}s on {device}")


def decode_image(image_data: str) -> np.ndarray:
    """Decode base64 image to numpy array."""
    # Remove data URL prefix if present
    if "base64," in image_data:
        image_data = image_data.split("base64,")[1]

    image_bytes = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB if necessary
    if image.mode != "RGB":
        image = image.convert("RGB")

    return np.array(image)


def encode_image(image: np.ndarray) -> str:
    """Encode numpy array to base64 string."""
    image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    buffer = io.BytesIO()
    image_pil.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode()


def draw_detections(image: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """Draw bounding boxes on image."""
    image = image.copy()

    for det in detections:
        x1, y1, x2, y2 = [int(c) for c in det.bbox]

        # Draw box
        color = (0, 255, 0)  # Green
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        # Draw label
        label = f"{det.class_name}: {det.confidence:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(
            image,
            (x1, y1 - label_size[1] - 10),
            (x1 + label_size[0], y1),
            color,
            -1,
        )
        cv2.putText(
            image,
            label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
        )

    return image


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if model_info["loaded"] else "loading",
        "service": "person-detection",
        "model": model_info["name"],
        "device": model_info["device"],
        "gpu_available": torch.cuda.is_available(),
    }


@app.get("/info")
async def get_info():
    """Get model and service information."""
    gpu_info = None
    if torch.cuda.is_available():
        gpu_info = {
            "name": torch.cuda.get_device_name(0),
            "memory_total": torch.cuda.get_device_properties(0).total_memory,
            "memory_allocated": torch.cuda.memory_allocated(0),
        }

    return {
        "model": model_info,
        "gpu": gpu_info,
        "config": {
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "iou_threshold": IOU_THRESHOLD,
            "use_gpu": USE_GPU,
        },
    }


@app.post("/detect", response_model=DetectionResult)
async def detect_image(request: DetectionRequest):
    """Detect persons in a base64 encoded image."""
    if not model_info["loaded"]:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Decode image
        image = decode_image(request.image)
        height, width = image.shape[:2]

        # Run inference
        start_time = time.time()
        results = model.predict(
            image,
            conf=request.confidence,
            iou=request.iou,
            classes=[0],  # 0 = person in COCO
            verbose=False,
        )
        inference_time = (time.time() - start_time) * 1000

        # Process results
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls_id = int(box.cls[0].item())

                detections.append(Detection(
                    class_id=cls_id,
                    class_name="person",
                    confidence=round(conf, 3),
                    bbox=[round(c, 1) for c in [x1, y1, x2, y2]],
                    center=[round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                ))

        return DetectionResult(
            success=True,
            detections=detections,
            total_persons=len(detections),
            inference_time_ms=round(inference_time, 2),
            image_size=[width, height],
            model=model_info["name"],
            device=model_info["device"],
        )

    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect/upload")
async def detect_upload(
    file: UploadFile = File(...),
    confidence: float = CONFIDENCE_THRESHOLD,
    iou: float = IOU_THRESHOLD,
    return_image: bool = False,
):
    """Detect persons in an uploaded image file."""
    if not model_info["loaded"]:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read image
        contents = await file.read()
        image = np.array(Image.open(io.BytesIO(contents)).convert("RGB"))
        height, width = image.shape[:2]

        # Run inference
        start_time = time.time()
        results = model.predict(
            image,
            conf=confidence,
            iou=iou,
            classes=[0],
            verbose=False,
        )
        inference_time = (time.time() - start_time) * 1000

        # Process results
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                cls_id = int(box.cls[0].item())

                detections.append(Detection(
                    class_id=cls_id,
                    class_name="person",
                    confidence=round(conf, 3),
                    bbox=[round(c, 1) for c in [x1, y1, x2, y2]],
                    center=[round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                ))

        response = {
            "success": True,
            "detections": [d.model_dump() for d in detections],
            "total_persons": len(detections),
            "inference_time_ms": round(inference_time, 2),
            "image_size": [width, height],
            "model": model_info["name"],
            "device": model_info["device"],
        }

        # Optionally return image with bboxes
        if return_image:
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            annotated = draw_detections(image_bgr, detections)
            response["annotated_image"] = encode_image(annotated)

        return response

    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect/url")
async def detect_url(
    url: str,
    confidence: float = CONFIDENCE_THRESHOLD,
    iou: float = IOU_THRESHOLD,
):
    """Detect persons in an image from URL."""
    if not model_info["loaded"]:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()

        image = np.array(Image.open(io.BytesIO(response.content)).convert("RGB"))
        height, width = image.shape[:2]

        # Run inference
        start_time = time.time()
        results = model.predict(
            image,
            conf=confidence,
            iou=iou,
            classes=[0],
            verbose=False,
        )
        inference_time = (time.time() - start_time) * 1000

        # Process results
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()

                detections.append(Detection(
                    class_id=0,
                    class_name="person",
                    confidence=round(conf, 3),
                    bbox=[round(c, 1) for c in [x1, y1, x2, y2]],
                    center=[round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                ))

        return {
            "success": True,
            "detections": [d.model_dump() for d in detections],
            "total_persons": len(detections),
            "inference_time_ms": round(inference_time, 2),
            "image_size": [width, height],
            "source_url": url,
            "model": model_info["name"],
            "device": model_info["device"],
        }

    except Exception as e:
        logger.error(f"Detection from URL failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    logger.info("Person Detection service starting...")
    load_model()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=int(os.getenv("WORKERS", "1")),
    )

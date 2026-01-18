# =============================================================================
# DeepStream Camera Stream Service
# =============================================================================
# Requires NVIDIA GPU and nvidia-container-toolkit
# Base image: NVIDIA DeepStream SDK

FROM nvcr.io/nvidia/deepstream:6.4-gc-triton-devel AS builder

WORKDIR /app

# Install additional dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn \
    pyyaml \
    httpx

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

EXPOSE 8554 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["python3", "/app/app.py"]

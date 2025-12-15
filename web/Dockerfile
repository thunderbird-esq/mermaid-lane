# Dockerfile for Mermaid Lane - Fly.io Deployment
# Named after Philo Farnsworth's W3XPF at 127 E. Mermaid Lane, Philadelphia

FROM python:3.12-slim

# Install ffmpeg for transcoding and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/app ./app

# Copy frontend static files
COPY frontend ./frontend

# Copy M3U stream files for additional streams
# These are from iptv-org/iptv repository (not in API)
COPY iptv_streams ./iptv_streams

# Create data directory (but use volume in production)
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

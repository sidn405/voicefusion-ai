# ---- Python FastAPI backend for LawBot 360 with Replicate ----
# Super simple - no torch, no scipy, no numpy issues!
FROM python:3.11.9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on

WORKDIR /app

# Install system dependencies for pyttsx3 and espeak
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create audio directory
RUN mkdir -p /tmp/audio

# Default port Railway exposes
ENV PORT=8080
EXPOSE 8080

# Start FastAPI
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
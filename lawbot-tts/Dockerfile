# ---- TTS Service for LawBot ----
# Matches your working ai-meeting-notes Dockerfile structure
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on

WORKDIR /app

# Install audio/ML system dependencies for TTS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tzdata \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy TTS server code
COPY . .

# Port for TTS service
ENV PORT=5000
EXPOSE 5000

# Start TTS server with gunicorn (matches your ai-meeting-notes pattern)
CMD ["sh","-c","gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 tts_server:app"]
# ---- Python FastAPI backend for LawBot 360 with Replicate ----
# Super simple - no torch, no scipy, no numpy issues!
FROM python:3.11.9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# Install minimal system dependencies (no audio processing libraries needed!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies (super fast - no torch!)
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Default port Railway exposes
ENV PORT=8080
EXPOSE 8080

# Start FastAPI
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
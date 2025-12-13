# ---- Python Flask backend for LawBot 360 Voice Sales Agent ----
# With voice cloning - fixed scipy/numpy versions
FROM python:3.11.9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tzdata \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# CRITICAL FIX: Install compatible numpy/scipy versions FIRST
# This prevents the ufunc error
RUN pip install numpy==1.24.3 scipy==1.10.1

# Install PyTorch CPU versions from specific index
RUN pip install torch==2.5.1 torchaudio==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu

# Remove conflicting lines from requirements to avoid reinstalling
RUN sed -i '/^torch==/d; /^torchaudio==/d; /^torchvision==/d; /^numpy==/d; /^scipy==/d' requirements.txt

# Install remaining dependencies
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Default port Railway exposes
ENV PORT=8080
EXPOSE 8080

# Start Flask app with voice cloning enabled
CMD ["python", "twilio_phone_integration.py"]
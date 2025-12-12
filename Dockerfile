# ---- Python FastAPI backend only ----
FROM python:3.11.9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on

WORKDIR /app

# system deps (sqlite, tz, etc. if you need them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tzdata \
 && rm -rf /var/lib/apt/lists/*

# install deps first (better caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy app code
COPY app ./app

# default port Railway exposes
ENV PORT=8080
EXPOSE 8080

# start FastAPI
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

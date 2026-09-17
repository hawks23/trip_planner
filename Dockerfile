FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

# Copy only runtime files. Credentials are supplied when the container starts.
COPY app.py backend.py ./
COPY tools/ ./tools/
COPY templates/ ./templates/
COPY static/ ./static/

USER app
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '10000') + '/api/health', timeout=4)"

# Expand Render's PORT and forward shutdown signals directly to Uvicorn.
CMD ["sh", "-c", "exec python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]

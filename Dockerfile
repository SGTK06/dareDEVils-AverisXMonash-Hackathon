# syntax=docker/dockerfile:1.7

FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies first for Docker layer caching.
COPY server/requirements.txt ./requirements.txt

RUN pip install \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# Hugging Face models must already exist in /app/models.
ENV HF_HUB_OFFLINE=1

# ------------------------------------------------------------
# Application code
# ------------------------------------------------------------
COPY server/scoring.py ./scoring.py
COPY server/app.py ./app.py
COPY server/score_cli.py ./score_cli.py
COPY server/persistence.py ./persistence.py
COPY server/comparison_service.py ./comparison_service.py
COPY server/comparison ./comparison
COPY server/classification ./classification

# ------------------------------------------------------------
# ML models
# ------------------------------------------------------------
COPY models ./models

# ------------------------------------------------------------
# Public challenge data
#
# This is copied into the image because Render does not use
# the bind mounts from docker-compose.yml.
#
# IMPORTANT:
# ground_truth.json is NOT copied here.
# ------------------------------------------------------------
COPY data_v2 ./data_v2

# Tell the application where the public data lives.
ENV DATA_DIR=/app/data_v2

# Ground truth should remain private.
# If you configure a Render secret/file for it, point
# GROUND_TRUTH at that location.
ENV GROUND_TRUTH=/secrets/ground_truth.json

# ------------------------------------------------------------
# Server
# ------------------------------------------------------------
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      libasound2t64 \
      libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.12.0" \
    && pip install latentscore==0.1.8

COPY render.py /app/render.py
WORKDIR /work

ENTRYPOINT ["python", "/app/render.py"]

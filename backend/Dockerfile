FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

RUN groupadd -r fastapi && useradd -r -g fastapi -s /sbin/nologin fastapi
COPY --chown=fastapi:fastapi ./app /app/app

USER fastapi

EXPOSE 8000

CMD ["uvicorn", "app.server:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--proxy-headers", \
    "--forwarded-allow-ips", "*"]
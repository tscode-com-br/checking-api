FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY assets ./assets
COPY sistema ./sistema

FROM base AS app-runtime

EXPOSE 8000

CMD ["python", "-m", "sistema.app.http_runtime"]

FROM base AS forms-worker-runtime

RUN playwright install --with-deps --only-shell chromium \
	&& rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

CMD ["python", "-m", "sistema.app.forms_worker_main"]

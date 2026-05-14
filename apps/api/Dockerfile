# Reference container for the FastAPI service. Build from repo root:
#   docker build -f apps/api/Dockerfile .
# Run with DATABASE_URL, API_SECRET_KEY, S3_*, etc. (see .env.example). Not continuously verified in cloud environments.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
  && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

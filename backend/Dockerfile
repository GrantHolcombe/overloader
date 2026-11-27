# syntax=docker/dockerfile:1
#
# The Overloader API as one image that runs the same everywhere: on a laptop, in CI, and on
# AWS Lambda (through the Lambda Web Adapter, which turns Lambda events into plain HTTP
# requests to uvicorn). Off Lambda the adapter does nothing, so the image also runs unchanged on
# Fargate or Fly.io.
#
#   docker build -t overloader-api backend
#   docker run -p 8080:8080 -e DATABASE_URL=... -e JWT_SECRET=... overloader-api
#
# Built for ARM64 (Graviton) in CI. The same image runs the database migrations and the
# catalog sync during a deploy:
#   docker run ... overloader-api alembic upgrade head
#   docker run ... overloader-api python -m app.catalog --apply

ARG PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.14-slim

# --- build: install the dependencies into a virtualenv -------------------------------------
FROM ${PYTHON_IMAGE} AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml ./
# Only the runtime dependencies from pyproject.toml (not the dev tools, and not the app itself:
# the source is copied as plain files below so app/, migrations/ and catalog/ sit side by side).
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
 && python -m venv /venv \
 && /venv/bin/pip install -r requirements.txt \
 && /venv/bin/pip freeze > /venv/installed.txt

# --- runtime --------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE}

# Lambda Web Adapter, pinned. Lambda runs anything in /opt/extensions as an extension.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter

COPY --from=build /venv /venv
WORKDIR /srv
COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY catalog ./catalog

RUN useradd --system --uid 10001 --no-create-home overloader
USER overloader

# ENV=production: the app refuses to start without a real JWT_SECRET (see app/main.py) and
# never prints sign-in codes. Local runs can pass -e ENV=dev.
ENV PATH=/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENV=production \
    PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/api/health \
    AWS_LWA_READINESS_CHECK_HEALTHY_STATUS=200-299

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')"

# --proxy-headers: behind Lambda/Cloudflare the TCP peer is the adapter, so the client address
# comes from the forwarding headers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]

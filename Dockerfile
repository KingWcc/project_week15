#
# Homework 2: container image for the OpenAI Agents SDK implementation.
# Secrets are deliberately NOT baked into the image. Supply OPENAI_API_KEY at
# runtime with --env-file, docker compose, or your orchestrator's secret store.
#
# 不使用 # syntax=docker/dockerfile:1：ACR 构建环境访问 Docker Hub 会超时。
# 基础镜像默认走国内镜像源，可用 --build-arg BASE_IMAGE=... 覆盖。

ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${BASE_IMAGE} AS runtime

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install dependencies in a separate layer so source edits do not reinstall them.
COPY requirements-openai-agents.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url "${PIP_INDEX_URL}" \
        -r requirements-openai-agents.txt

COPY common ./common
COPY openai_agents_app ./openai_agents_app
COPY frontend ./frontend

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "openai_agents_app.server:app", "--host", "0.0.0.0", "--port", "8000"]

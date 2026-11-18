#!/usr/bin/env bash
# 在服务器上部署 week15 情感支持镜像。
# 用法：
#   export IMAGE=registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:latest
#   ./deploy.sh
# 可选环境变量：APP_PORT（默认 8000）、CONTAINER_NAME（默认 week15-sentiment-agent）

set -euo pipefail
cd "$(dirname "$0")"

IMAGE="${IMAGE:-}"
APP_PORT="${APP_PORT:-8000}"
CONTAINER_NAME="${CONTAINER_NAME:-week15-sentiment-agent}"

if [[ -z "$IMAGE" ]]; then
  echo "错误：请先设置 IMAGE，例如：" >&2
  echo "  export IMAGE=registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:latest" >&2
  exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "错误：服务器上没有 docker" >&2; exit 1; }
[[ -f .env ]] || { echo "错误：缺少 .env，请先上传并 chmod 600 .env" >&2; exit 1; }

perm="$(stat -c '%a' .env 2>/dev/null || stat -f '%Lp' .env 2>/dev/null || echo '?')"
if [[ "$perm" != "600" ]]; then
  echo "警告：.env 权限是 $perm，正在改为 600"
  chmod 600 .env
fi

echo "==> 拉取镜像 $IMAGE"
docker pull "$IMAGE"

echo "==> 替换旧容器（如有）"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "==> 启动容器，端口 $APP_PORT"
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "${APP_PORT}:8000" \
  --env-file .env \
  "$IMAGE" >/dev/null

echo "==> 等待健康检查"
for i in $(seq 1 30); do
  status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER_NAME" 2>/dev/null || echo missing)"
  echo "  ${i}/30: $status"
  case "$status" in
    healthy) break ;;
    unhealthy) echo "错误：容器健康检查失败，查看日志：docker logs $CONTAINER_NAME" >&2; exit 1 ;;
  esac
  sleep 2
done

echo "==> 本地健康检查"
curl -fsS "http://127.0.0.1:${APP_PORT}/api/health" && echo

echo "==> 部署完成"
docker ps --filter "name=$CONTAINER_NAME"

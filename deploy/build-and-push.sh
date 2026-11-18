#!/usr/bin/env bash
# 在装有 Docker 的机器上构建镜像并推送到阿里云 ACR。
# 用法：
#   ./deploy/build-and-push.sh            # 默认 tag 1.0
#   TAG=1.0.1 ./deploy/build-and-push.sh
# ECS 同地域可用 VPC 地址加速：
#   REGISTRY=crpi-svlhwbrf12hgphb3-vpc.cn-hangzhou.personal.cr.aliyuncs.com ./deploy/build-and-push.sh

set -euo pipefail
cd "$(dirname "$0")/.."   # 切到项目根目录（Dockerfile 所在位置）

REGISTRY="${REGISTRY:-crpi-svlhwbrf12hgphb3.cn-hangzhou.personal.cr.aliyuncs.com}"
NAMESPACE="${NAMESPACE:-project_week15}"
REPO="${REPO:-project_week15}"
TAG="${TAG:-1.0}"
ACR_USERNAME="${ACR_USERNAME:-aliyun1023347068}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"

IMAGE="$REGISTRY/$NAMESPACE/$REPO:$TAG"

command -v docker >/dev/null 2>&1 || {
  echo "错误：当前机器没有 docker，无法构建镜像。" >&2
  exit 1
}
[[ -f Dockerfile ]] || { echo "错误：当前目录没有 Dockerfile" >&2; exit 1; }

echo "==> 登录 $REGISTRY（按提示输入 ACR 访问凭证密码）"
docker login --username="$ACR_USERNAME" "$REGISTRY"

echo "==> 构建 $IMAGE"
docker build --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" -t "$IMAGE" .

echo "==> 推送 $IMAGE"
docker push "$IMAGE"

echo "==> 完成：$IMAGE"
echo "在服务器上拉取运行："
echo "  docker pull $IMAGE"
echo "  docker run -d --name week15-sentiment-agent --restart unless-stopped -p 8000:8000 --env-file .env $IMAGE"

# 服务器部署说明

目标：把 ACR 里的 `week15-sentiment-agent` 镜像跑在服务器上，`.env` 只放在服务器本地，不进 Git、不进镜像。

> 下面的 `<user>`、`<server>`、`<端口>`、`<命名空间>` 都要替换成实际值。

## 0. 前提

- 服务器已安装 Docker（`docker --version` 能输出版本）。
- ACR 里已经构建好镜像，例如：
  `registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:latest`

## 1. 从 Windows 上传文件

在本地 PowerShell 里，先进入项目目录：

```powershell
cd "C:\ai培训班\正式课程\第15周：Reasoning、Sanbox和ClaudeCode Codex应用\week15_homework"
```

创建远程目录并上传部署包和 `.env`（`scp` 的端口参数是大写 `-P`）：

```powershell
ssh -p <端口> <user>@<server> "mkdir -p /opt/week15"
scp -P <端口> -r deploy <user>@<server>:/opt/week15/
scp -P <端口> .env <user>@<server>:/opt/week15/deploy/.env
ssh -p <端口> <user>@<server> "chmod 600 /opt/week15/deploy/.env"
```

如果服务器用密钥登录，加上 `-i C:\path\to\key.pem`。密码登录时命令会提示输入密码，密码不要发到对话里。

## 2. 在服务器上部署

```bash
ssh -p <端口> <user>@<server>
cd /opt/week15/deploy

export IMAGE=registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:latest
chmod +x deploy.sh
./deploy.sh
```

如果镜像仓库是私有的，先登录：

```bash
docker login --username=<阿里云账号> registry.cn-hangzhou.aliyuncs.com
```

也可以改用 Compose：

```bash
export IMAGE=registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:latest
docker compose up -d
docker compose logs -f
```

## 3. 验证

```bash
curl http://127.0.0.1:8000/api/health
docker ps --filter name=week15-sentiment-agent
docker logs --tail 50 week15-sentiment-agent
```

浏览器访问 `http://<服务器公网IP>:8000/`；云服务器安全组/防火墙需要放行 8000 端口。

## 4. 更新与回滚

```bash
# 更新到新镜像
export IMAGE=registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:1.0
./deploy.sh

# 回退到上一个 tag
export IMAGE=registry.cn-hangzhou.aliyuncs.com/<命名空间>/week15-sentiment-agent:0.9
./deploy.sh
```

## 5. 没有 ACR 镜像时

在服务器上直接构建（把代码目录传上去）：

```bash
docker build -t week15-sentiment-agent:1.0 .
docker run -d --name week15-sentiment-agent --restart unless-stopped \
  -p 8000:8000 --env-file .env week15-sentiment-agent:1.0
```

## 6. 安全注意事项

- `.env` 只放服务器本地，权限 `600`；不要提交到 Codeup/GitHub，也不要打进镜像。
- 本次作业的 DeepSeek Key 曾出现在对话中，建议在 DeepSeek 控制台重置一次后再用于服务器。
- 生产环境建议在前面加 Nginx/Caddy 做 TLS 和限流，不要把 8000 端口直接暴露到公网太久。

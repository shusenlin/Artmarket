# ArtMarket WSL + ngrok 公网访问

这个方案适合本机测试公网访问：Gunicorn 在 WSL 内运行 Flask，ngrok 把本地端口转成公网 HTTPS 地址。

## 需要安装

Python 依赖已在 `requirements.txt` 中包含 `gunicorn`。在你的 conda 环境里执行：

```bash
conda activate artmarket
cd /home/forest/Projects/ArtMarket
pip install -r requirements.txt
```

ngrok 需要单独安装。官方 Debian Linux 安装命令：

```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list \
  && sudo apt update \
  && sudo apt install ngrok
```

登录 https://dashboard.ngrok.com/get-started/your-authtoken 获取 token，然后执行：

```bash
ngrok config add-authtoken 你的_NGROK_AUTHTOKEN
```

## 启动网站

打开第一个 WSL 终端：

```bash
conda activate artmarket
cd /home/forest/Projects/ArtMarket
bash scripts/run_gunicorn.sh
```

打开第二个 WSL 终端：

```bash
conda activate artmarket
cd /home/forest/Projects/ArtMarket
bash scripts/start_ngrok.sh
```

ngrok 会显示一个 `https://...ngrok-free.app` 地址。把这个地址发给别人即可访问。

## 可选配置

修改监听端口：

```bash
ARTMARKET_BIND=127.0.0.1:8000 bash scripts/run_gunicorn.sh
ARTMARKET_PORT=8000 bash scripts/start_ngrok.sh
```

修改 Gunicorn worker 数：

```bash
ARTMARKET_WORKERS=3 bash scripts/run_gunicorn.sh
```

## 注意

- 电脑关机、WSL 停止、Gunicorn 停止或 ngrok 停止后，公网地址都会无法访问。
- 免费 ngrok 地址通常会变化；固定域名一般需要 ngrok 账号配置保留域名或付费能力。
- 当前数据库和上传文件都在本机，正式对外长期使用前应备份 `instance/artmarket.db` 和 `static/uploads/`。

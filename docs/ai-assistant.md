# 艺术品鉴赏智能体配置

## 依赖

已在 `requirements.txt` 中加入：

```txt
openai>=1.0
```

安装：

```bash
conda activate artmarket
cd /home/forest/Projects/ArtMarket
pip install -r requirements.txt
```

## 环境变量

火山方舟 API Key：

```bash
export ARK_API_KEY="你的_API_KEY"
```

如果用 `.env` 文件，也可以在项目根目录创建 `/home/forest/Projects/ArtMarket/.env`：

```bash
ARK_API_KEY=你的_API_KEY
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=doubao-seed-2-0-pro-260215
```

注意：如果你是在某个终端里 `export ARK_API_KEY=...`，必须在同一个终端里启动 `python app.py` 或 Gunicorn；已经启动的 Flask 进程不会自动获得后来 export 的环境变量。

可选配置：

```bash
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export ARK_MODEL="doubao-seed-2-0-pro-260215"
```

## 启动

```bash
conda activate artmarket
cd /home/forest/Projects/ArtMarket
python app.py
```

或使用 Gunicorn：

```bash
bash scripts/run_gunicorn.sh
```

## 功能说明

页面右下角会显示 `AI` 悬浮按钮。点击后打开右侧侧边栏。

支持：

- 拖拽 1-5 张图片
- 粘贴图片
- 输入补充信息
- 调用 `/api/assistant/appraise`
- 返回固定格式中文鉴赏意见

后端执行三阶段调用：

1. 客观视觉观察
2. 风格与类别候选判断
3. 固定格式鉴赏文本生成

图片不会保存到数据库，只在请求内转为 data URL 发送给模型。

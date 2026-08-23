# 每日外刊英语学习 + 知识拓展

每天自动抓取权威外刊 RSS → OpenAI 生成中英双语摘要 → 从双知识库随机抽取 3 条知识 →
AI 生成「今日词汇」板块 → 渲染 HTML 并部署到 GitHub Pages。

## 目录结构

```
├── main.py                  # 每日主流程
├── api_server.py            # 知识库 HTTP API 服务（可选）
├── config.yaml              # 所有配置（RSS 源、数量、模型等）
├── requirements.txt
├── src/
│   ├── knowledge_base.py    # 知识库 API 层（Python 调用入口）
│   ├── kb_updater.py        # 知识库一：每周抓取外刊刷新
│   ├── rss_fetcher.py       # 每日新闻 RSS 抓取
│   ├── ai_client.py         # OpenAI 摘要 / 词汇生成
│   └── html_generator.py    # Jinja2 渲染
├── templates/page.html      # 页面模板
├── data/
│   ├── kb_news.json         # 知识库一（自动生成，勿手改）
│   └── books/*.md           # 知识库二：读书笔记（手动维护）
├── output/                  # 生成的页面（index.html + archive/）
└── .github/workflows/       # 每日生成 + 每周刷新知识库
```

## 双知识库设计

| 知识库 | 内容 | 维护方式 |
|---|---|---|
| **news**（`data/kb_news.json`） | 最新新闻资讯、科学报刊摘要 | GitHub Actions 每周一自动抓取 BBC/Guardian/ScienceDaily/Nature/SciAm 并 AI 摘要入库，滚动保留 200 条 |
| **books**（`data/books/*.md`） | 书本内容 / 读书笔记 | 手动维护：每本书的笔记存为一个 `.md` 文件，支持 YAML front matter（title / book / tags） |

## 知识库调用 API

### Python 方式

```python
from src.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
kb.stats()                          # 存量统计
kb.get_random(3)                    # 随机 3 条（两库混合）
kb.get_random(3, source="books")    # 只从书本库抽
kb.get_daily(3)                     # 每日 3 条：以日期为 seed，同一天结果固定
kb.save_news_entries(entries)       # 写入新闻库（自动去重 + 滚动淘汰）
```

### HTTP 方式

```bash
uvicorn api_server:app --port 8000
```

| 接口 | 说明 |
|---|---|
| `GET /api/knowledge/stats` | 知识库存量 |
| `GET /api/knowledge/items?source=news&limit=20` | 列出条目 |
| `GET /api/knowledge/random?n=3&source=books` | 随机抽取 |
| `GET /api/knowledge/daily?n=3&date=2026-08-23` | 每日固定抽取 |
| `POST /api/knowledge/refresh?use_ai=false` | 手动刷新新闻知识库 |

## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 OPENAI_API_KEY
set -a; source .env; set +a   # Windows PowerShell: $env:OPENAI_API_KEY="sk-..."

python -m src.kb_updater        # 首次先建新闻知识库
python main.py                  # 生成今日页面到 output/index.html
python main.py --no-ai          # 测试模式：不调 OpenAI
```

## 在 Kindle 上阅读（局域网模式，国内网络直连，推荐）

每次生成会同时产出两个版本：

- `output/index.html` —— 电脑/手机版（排版美观）
- `output/kindle.html` —— Kindle 电纸书专用极简版：纯黑白、无 JS、120% 大字体、
  单栏结构，兼容 Kindle 内置的"体验版网页浏览器"

在电脑上启动局域网服务：

```bash
python serve.py          # 默认 8000 端口
```

启动后会打印地址，例如：

```
电脑版    http://192.168.1.5:8000/
Kindle版  http://192.168.1.5:8000/kindle.html
```

在 Kindle 上打开「体验版网页浏览器」，输入上面的 Kindle 版地址即可阅读；
页面顶部有近 7 天的归档链接，可以翻历史。要求：电脑和 Kindle 连同一个 Wi-Fi，
首次运行 Windows 防火墙弹窗选"允许"。搭配 Windows 任务计划程序定时运行
`main.py`，即可每天早上自动生成新页面。

## 部署到 GitHub Pages（备选，国内访问可能不稳定）

1. 把本目录推送到一个 GitHub 仓库；
2. 仓库 **Settings → Secrets → Actions** 添加 `OPENAI_API_KEY`（如用代理再加 `OPENAI_BASE_URL`）；
3. **Settings → Pages → Source** 选择 **GitHub Actions**；
4. 之后每天 06:47（北京时间）自动生成并发布页面，每周一 06:17 自动刷新新闻知识库；也可在 Actions 页手动触发。

## 配置说明（config.yaml）

- `news_feeds` / `kb_feeds`：随意增删 RSS 源；
- `pipeline.kb_items_per_day`：每日知识条数（默认 3）；
- `pipeline.vocab_count`：今日词汇数量（默认 3）；
- `pipeline.kb_max_entries`：新闻知识库容量（默认 200，滚动淘汰）；
- `openai.model`：默认 `gpt-4o-mini`，可换任意兼容模型。

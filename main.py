"""每日主流程：抓新闻 -> AI 摘要 -> 抽 3 条知识 -> 生成今日词汇 -> 渲染 HTML。

用法：
    python main.py              # 完整流程（需要 OPENAI_API_KEY）
    python main.py --no-ai      # 干跑：不调 OpenAI，用原文代替摘要（用于测试）
    python main.py --date 2026-08-23
"""

from __future__ import annotations

import argparse
import shutil
from datetime import date, datetime
from pathlib import Path

import yaml

from src.ai_client import AIClient
from src.html_generator import render_page
from src.knowledge_base import KnowledgeBase
from src.rss_fetcher import fetch_daily_news


def run(target_date: str | None = None, use_ai: bool = True) -> Path:
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    pipe, paths = cfg["pipeline"], cfg["paths"]
    day = target_date or date.today().isoformat()

    ai = AIClient(cfg["openai"]) if use_ai else None

    # 1. 抓取每日新闻 + AI 摘要
    print(f"[main] 抓取新闻 RSS ...")
    news = fetch_daily_news(cfg["news_feeds"], pipe["news_items_per_feed"],
                            pipe["news_max_total"], pipe["request_timeout"])
    print(f"[main] 抓到 {len(news)} 条新闻")
    if ai:
        for n in news:
            n["summary"] = ai.summarize_news(n["title"], n["content"])

    # 2. 从双知识库随机抽 3 条（同一天结果稳定）
    kb = KnowledgeBase("config.yaml")
    kb_items = kb.get_daily(n=pipe["kb_items_per_day"], date_str=day)
    print(f"[main] 抽取知识 {len(kb_items)} 条（知识库存量 {kb.stats()}）")

    # 3. AI 生成今日词汇
    vocab = ai.generate_vocab(kb_items, pipe["vocab_count"]) if ai and kb_items else []
    print(f"[main] 生成词汇 {len(vocab)} 个")

    # 4. 渲染 HTML：PC 版 index.html + Kindle 极简版 kindle.html + 双版本归档
    out_dir = Path(paths["output_dir"])
    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    context = {
        "date": day,
        "news": news,
        "kb_items": kb_items,
        "vocab": vocab,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    index = render_page(paths["template_file"], str(out_dir / "index.html"), **context)
    shutil.copy(index, archive_dir / f"{day}.html")

    # Kindle 版：附加近 7 天归档链接，方便电纸书上翻历史
    archive_links = sorted(p.stem for p in archive_dir.glob("kindle-*.html"))[-6:]
    archive_links.append(day)
    kindle = render_page("templates/kindle.html", str(out_dir / "kindle.html"),
                         archive_links=archive_links, **context)
    shutil.copy(kindle, archive_dir / f"kindle-{day}.html")
    print(f"[main] 页面已生成: {index} / {kindle}")
    return index


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="指定日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--no-ai", action="store_true", help="不调用 OpenAI（测试用）")
    args = ap.parse_args()
    run(args.date, use_ai=not args.no_ai)

"""知识库一（新闻/科学报刊）每周刷新：抓取权威外刊 RSS -> AI 摘要 -> 入库。

用法：
    python -m src.kb_updater            # 全量刷新
    python -m src.kb_updater --no-ai    # 不调用 OpenAI，直接用 RSS 摘要入库
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from .knowledge_base import KnowledgeBase, make_id


def _clean_html(raw: str, limit: int = 1200) -> str:
    text = BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)
    return text[:limit]


def fetch_feed_entries(feeds: list[dict], per_feed: int, timeout: int) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (daily-english-kb bot)"}
    entries = []
    for feed in feeds:
        try:
            resp = requests.get(feed["url"], headers=headers, timeout=timeout)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            for e in parsed.entries[:per_feed]:
                entries.append({
                    "id": make_id(e.get("link", e.get("title", ""))),
                    "source": "news",
                    "title": e.get("title", "").strip(),
                    "content": _clean_html(e.get("summary") or e.get("description", "")),
                    "source_name": feed["name"],
                    "url": e.get("link", ""),
                    "published": e.get("published", e.get("updated", "")),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "tags": [],
                })
        except Exception as exc:  # 单个源失败不阻塞整体
            print(f"[kb_updater] 抓取失败 {feed['name']}: {exc}")
    return entries


def refresh(use_ai: bool = True, config_path: str = "config.yaml") -> int:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    pipe = cfg["pipeline"]

    entries = fetch_feed_entries(cfg["kb_feeds"], per_feed=15,
                                 timeout=pipe["request_timeout"])
    print(f"[kb_updater] 抓到 {len(entries)} 条原始条目")

    if use_ai and entries:
        from .ai_client import AIClient
        ai = AIClient(cfg["openai"])
        for e in entries:
            summary = ai.summarize_knowledge(e["title"], e["content"])
            if summary:
                e["content"] = summary

    kb = KnowledgeBase(config_path)
    n = kb.save_news_entries(entries, max_entries=pipe["kb_max_entries"])
    print(f"[kb_updater] 入库完成，新增/更新 {n} 条，当前总量 {kb.stats()}")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ai", action="store_true", help="跳过 OpenAI 摘要")
    args = ap.parse_args()
    refresh(use_ai=not args.no_ai)

"""每日新闻 RSS 抓取。"""

from __future__ import annotations

import feedparser
import requests
from bs4 import BeautifulSoup


def _clean(raw: str, limit: int = 2500) -> str:
    return BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)[:limit]


def fetch_daily_news(feeds: list[dict], per_feed: int, max_total: int,
                     timeout: int = 20) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (daily-english bot)"}
    items = []
    for feed in feeds:
        try:
            resp = requests.get(feed["url"], headers=headers, timeout=timeout)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            for e in parsed.entries[:per_feed]:
                items.append({
                    "title": e.get("title", "").strip(),
                    "content": _clean(e.get("summary") or e.get("description", "")),
                    "url": e.get("link", ""),
                    "published": e.get("published", e.get("updated", "")),
                    "source_name": feed["name"],
                    "category": feed.get("category", "综合"),
                })
        except Exception as exc:
            print(f"[rss] 抓取失败 {feed['name']}: {exc}")
    return items[:max_total]

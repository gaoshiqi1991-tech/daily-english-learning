"""
知识库 API 层 —— 所有对知识库的访问统一走这里。

两种使用方式：
1. Python 直接调用：
       from src.knowledge_base import KnowledgeBase
       kb = KnowledgeBase()
       items = kb.get_random(3)

2. HTTP API（运行 api_server.py 后）：
       GET http://127.0.0.1:8000/api/knowledge/random?n=3&source=news

知识条目统一结构（dict）：
    {
        "id":          唯一 id（url 或文件名的哈希）,
        "source":      "news" | "books",
        "title":       标题,
        "content":     正文 / 摘要,
        "source_name": 来源报刊或书名,
        "url":         原文链接（书本条目可为空）,
        "published":   发布日期字符串（可为空）,
        "tags":        [..],
    }
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
from pathlib import Path
from typing import Optional

import yaml

_LOCK = threading.Lock()


def _load_config(config_path: str | Path = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


class KnowledgeBase:
    """双知识库：news（每周刷新的新闻/科学报刊）+ books（读书笔记 md 文件）。"""

    def __init__(self, config_path: str | Path = "config.yaml"):
        cfg = _load_config(config_path)
        paths = cfg["paths"]
        self.kb_news_file = Path(paths["kb_news_file"])
        self.kb_books_dir = Path(paths["kb_books_dir"])
        self.kb_books_dir.mkdir(parents=True, exist_ok=True)
        self.kb_news_file.parent.mkdir(parents=True, exist_ok=True)

    # ---------- 读取 ----------

    def get_all(self, source: Optional[str] = None) -> list[dict]:
        """返回知识条目；source 可为 'news'、'books' 或 None（全部）。"""
        items: list[dict] = []
        if source in (None, "news"):
            items.extend(self._load_news())
        if source in (None, "books"):
            items.extend(self._load_books())
        return items

    def get_random(self, n: int = 3, source: Optional[str] = None,
                   seed: Optional[int] = None) -> list[dict]:
        """随机抽取 n 条知识。seed 固定则结果可复现（例如按日期做每日固定抽取）。"""
        pool = self.get_all(source)
        if not pool:
            return []
        rng = random.Random(seed)
        return rng.sample(pool, min(n, len(pool)))

    def get_daily(self, n: int = 3, date_str: Optional[str] = None,
                  source: Optional[str] = None) -> list[dict]:
        """“每日 3 条”：以日期为 seed，同一天内抽取结果稳定不变。"""
        from datetime import date
        day = date_str or date.today().isoformat()
        seed = int(hashlib.sha1(day.encode()).hexdigest()[:8], 16)
        return self.get_random(n=n, source=source, seed=seed)

    def stats(self) -> dict:
        return {
            "news_count": len(self._load_news()),
            "books_count": len(self._load_books()),
        }

    # ---------- 写入（供 kb_updater 与用户手动维护使用） ----------

    def save_news_entries(self, entries: list[dict], max_entries: int = 200) -> int:
        """合并去重写入新闻知识库，超出 max_entries 时按 fetched_at 滚动淘汰最旧条目。"""
        with _LOCK:
            existing = {e["id"]: e for e in self._load_news()}
            for e in entries:
                e.setdefault("id", make_id(e.get("url") or e["title"]))
                e.setdefault("source", "news")
                e.setdefault("tags", [])
                existing[e["id"]] = e
            merged = sorted(existing.values(),
                            key=lambda e: e.get("fetched_at", ""), reverse=True)
            merged = merged[:max_entries]
            self.kb_news_file.write_text(
                json.dumps(merged, ensure_ascii=False, indent=2),
                encoding="utf-8")
            return len(entries)

    # ---------- 内部 ----------

    def _load_news(self) -> list[dict]:
        if not self.kb_news_file.exists():
            return []
        try:
            data = json.loads(self.kb_news_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _load_books(self) -> list[dict]:
        """书本知识库：data/books/ 下每个 .md 文件 = 一条读书笔记。

        支持可选的 YAML front matter：
            ---
            title: 章节名
            book: 书名
            tags: [a, b]
            ---
        """
        items = []
        for md in sorted(self.kb_books_dir.glob("*.md")):
            text = md.read_text(encoding="utf-8").strip()
            if not text:
                continue
            title, book, tags, body = md.stem, "", [], text
            if text.startswith("---"):
                end = text.find("\n---", 3)
                if end != -1:
                    meta = yaml.safe_load(text[3:end]) or {}
                    title = meta.get("title", title)
                    book = meta.get("book", "")
                    tags = meta.get("tags", []) or []
                    body = text[end + 4:].strip()
            items.append({
                "id": make_id(str(md)),
                "source": "books",
                "title": title,
                "content": body,
                "source_name": book or "读书笔记",
                "url": "",
                "published": "",
                "tags": tags,
            })
        return items

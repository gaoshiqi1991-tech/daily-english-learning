"""知识库 HTTP API 服务（可选）。

启动：
    uvicorn api_server:app --port 8000

接口：
    GET /api/knowledge/stats                      知识库存量
    GET /api/knowledge/items?source=news&limit=20 列出条目（source: news|books）
    GET /api/knowledge/random?n=3&source=books    随机 n 条
    GET /api/knowledge/daily?n=3&date=2026-08-23  每日固定抽取（同日稳定）
    POST /api/knowledge/refresh?use_ai=false      手动触发新闻知识库刷新
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query

from src.kb_updater import refresh
from src.knowledge_base import KnowledgeBase

app = FastAPI(title="Knowledge Base API", version="1.0")
kb = KnowledgeBase("config.yaml")


@app.get("/api/knowledge/stats")
def stats():
    return kb.stats()


@app.get("/api/knowledge/items")
def items(source: Optional[str] = Query(None, pattern="^(news|books)$"),
          limit: int = Query(20, ge=1, le=100)):
    data = kb.get_all(source)
    return {"total": len(data), "items": data[:limit]}


@app.get("/api/knowledge/random")
def random_items(n: int = Query(3, ge=1, le=20),
                 source: Optional[str] = Query(None, pattern="^(news|books)$")):
    return {"items": kb.get_random(n=n, source=source)}


@app.get("/api/knowledge/daily")
def daily_items(n: int = Query(3, ge=1, le=20),
                date: Optional[str] = None,
                source: Optional[str] = Query(None, pattern="^(news|books)$")):
    return {"date": date, "items": kb.get_daily(n=n, date_str=date, source=source)}


@app.post("/api/knowledge/refresh")
def refresh_kb(use_ai: bool = False):
    added = refresh(use_ai=use_ai)
    return {"added_or_updated": added, **kb.stats()}

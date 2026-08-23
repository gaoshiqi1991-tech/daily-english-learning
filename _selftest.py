"""本地验证脚本：不依赖 feedparser/OpenAI，测试知识库 API 与页面渲染。"""
import json
from src.knowledge_base import KnowledgeBase
from src.html_generator import render_page

# 1. 知识库：读取 + 每日抽取稳定性
kb = KnowledgeBase("config.yaml")
stats = kb.stats()
print("stats:", stats)
assert stats["books_count"] == 3, "books 知识库应有 3 条种子笔记"

day1 = kb.get_daily(3, date_str="2026-08-23")
day2 = kb.get_daily(3, date_str="2026-08-23")
assert [i["id"] for i in day1] == [i["id"] for i in day2], "同日抽取必须稳定"
print("daily pick:", [i["title"] for i in day1])

# 2. 新闻库写入：去重 + 滚动淘汰
kb.save_news_entries([
    {"title": "Test A", "content": "content a", "url": "http://x/a",
     "source_name": "Test", "published": "", "fetched_at": "2026-08-23T00:00:00+00:00"},
    {"title": "Test B", "content": "content b", "url": "http://x/b",
     "source_name": "Test", "published": "", "fetched_at": "2026-08-23T00:01:00+00:00"},
])
kb.save_news_entries([  # 重复 url 应去重
    {"title": "Test A v2", "content": "updated", "url": "http://x/a",
     "source_name": "Test", "published": "", "fetched_at": "2026-08-23T00:02:00+00:00"},
])
news = kb.get_all("news")
assert len(news) == 2, f"去重失败: {len(news)}"
print("news kb:", [(i["title"], i["content"]) for i in news])
import os; os.remove("data/kb_news.json")  # 清掉测试数据

# 3. 页面渲染（用假数据）
out = render_page(
    "templates/page.html", "output/index.html",
    date="2026-08-23",
    news=[{"title": "Test News", "source_name": "BBC", "published": "",
           "url": "http://x", "content": "raw content",
           "summary": {"summary_en": "English summary.",
                       "summary_cn": "中文要点。",
                       "keywords": ["test", "demo"]}}],
    kb_items=day1,
    vocab=[{"word": "resilient", "phonetic": "/rɪˈzɪliənt/", "pos": "adj.",
            "meaning_en": "able to recover quickly",
            "meaning_cn": "有韧性的",
            "example": "She is resilient.", "example_cn": "她很有韧性。"}],
    generated_at="2026-08-23 15:10",
)
html = out.read_text(encoding="utf-8")
for token in ["今日词汇", "每日知识", "resilient", "Test News", "中文要点"]:
    assert token in html, f"页面缺少: {token}"
print("render OK ->", out)
print("\nALL TESTS PASSED")

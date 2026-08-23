"""OpenAI 调用封装：新闻摘要、知识摘要、今日词汇生成。"""

from __future__ import annotations

import json
import os

from openai import OpenAI


class AIClient:
    def __init__(self, openai_cfg: dict):
        kwargs = {"api_key": os.environ["OPENAI_API_KEY"],
                  "timeout": 60, "max_retries": 2}
        base_url = openai_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = os.environ.get("OPENAI_MODEL") or openai_cfg.get("model", "gpt-4o-mini")
        self.temperature = openai_cfg.get("temperature", 0.4)
        print(f"[ai] 使用模型 {self.model}, 接口 {base_url or 'https://api.openai.com (默认)'}")

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            **kwargs,
        )
        return resp.choices[0].message.content.strip()

    def summarize_news(self, title: str, content: str) -> dict | None:
        """每日新闻摘要：英文摘要 + 中文要点。返回 dict 或 None。"""
        try:
            raw = self._chat(
                "You are an English-learning editor. Reply in JSON only.",
                f"""Summarize this news article for an English learner.
Return JSON: {{"summary_en": "2-3 sentence English summary",
              "summary_cn": "2-3 句中文要点",
              "keywords": ["3-5 个关键词"]}}

Title: {title}
Content: {content[:3000]}""",
                json_mode=True)
            return json.loads(raw)
        except Exception as exc:
            print(f"[ai] summarize_news 失败: {exc}")
            return None

    def summarize_knowledge(self, title: str, content: str) -> str | None:
        """知识库条目摘要（一段话，供学习用）。"""
        try:
            return self._chat(
                "You are an editor for an English-learning knowledge base.",
                f"""Condense the following article into a compact knowledge card
(80-120 English words): key fact + why it matters + one useful expression.
Keep it in English.

Title: {title}
Content: {content[:3000]}""")
        except Exception as exc:
            print(f"[ai] summarize_knowledge 失败: {exc}")
            return None

    def generate_vocab(self, kb_items: list[dict], count: int = 3) -> list[dict]:
        """今日词汇：从随机知识条目中提炼学习词汇。返回词汇列表。"""
        material = "\n\n".join(
            f"[{i+1}] {it['title']}\n{it['content'][:1200]}"
            for i, it in enumerate(kb_items))
        try:
            raw = self._chat(
                "You are an English vocabulary teacher. Reply in JSON only.",
                f"""Based on the knowledge items below, pick {count} English words or
phrases that are useful for an intermediate-advanced learner (prefer words
appearing in or closely related to the texts).

Return JSON: {{"vocab": [
  {{"word": "...", "phonetic": "/.../", "pos": "n./v./adj./phrase",
    "meaning_en": "short English definition",
    "meaning_cn": "中文释义",
    "example": "an example sentence, ideally adapted from the material",
    "example_cn": "例句中文翻译",
    "from_item": 1}}
]}}

Knowledge items:
{material}""",
                json_mode=True)
            data = json.loads(raw)
            return data.get("vocab", [])[:count]
        except Exception as exc:
            print(f"[ai] generate_vocab 失败: {exc}")
            return []

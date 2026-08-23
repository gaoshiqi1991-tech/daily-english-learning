"""HTML 页面生成（Jinja2 模板渲染）。"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_page(template_file: str, output_file: str, **context) -> Path:
    tpl_path = Path(template_file)
    env = Environment(
        loader=FileSystemLoader(str(tpl_path.parent)),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template(tpl_path.name).render(**context)
    out = Path(output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out

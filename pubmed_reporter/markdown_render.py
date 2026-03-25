"""将 LLM 输出的 Markdown 转为 HTML，并生成 fpdf2 可用的样式映射。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import markdown
from fpdf.fonts import FontFace, TextStyle
from fpdf.html import DEFAULT_TAG_STYLES

if TYPE_CHECKING:
    from fpdf import FPDF


# extra：围栏代码、表格、脚注等；nl2br：软换行；sane_lists：列表解析更稳健
DEFAULT_MARKDOWN_EXTENSIONS: list[str] = [
    "extra",
    "nl2br",
    "sane_lists",
]


def llm_markdown_to_html(md_text: str, *, extensions: list[str] | None = None) -> str:
    """
    将 Markdown 转为可交给 fpdf2.write_html 的 XHTML 片段（带 html/body 根）。
    """
    text = md_text.strip()
    if not text:
        return "<html><body></body></html>"

    ext = extensions if extensions is not None else DEFAULT_MARKDOWN_EXTENSIONS
    md = markdown.Markdown(extensions=ext)
    fragment = md.convert(text)
    # 若模型未写根节点，包一层便于 HTMLParser
    return f"<html><body>{fragment}</body></html>"


def build_tag_styles_for_family(font_family: str) -> dict[str, FontFace | TextStyle]:
    """
    在 fpdf2 默认 HTML 样式基础上，为各标签指定 CJK 字体族名（须已通过 add_font 注册）。
    """
    out: dict[str, FontFace | TextStyle] = {}
    for tag, style in DEFAULT_TAG_STYLES.items():
        if isinstance(style, TextStyle):
            out[tag] = style.replace(font_family=font_family)
        else:
            out[tag] = style.replace(family=font_family)
    return out


def register_ttf_family_all_styles(pdf: FPDF, family: str, font_path: str) -> None:
    """
    为同一 TTF/TTC 注册常规、粗体、斜体、粗斜体名，供 write_html 中 emphasis 使用。
    fpdf2 在渲染 <strong> 等时会查找 family+B 等字形名。
    """
    p = str(font_path)
    pdf.add_font(family, "", p)
    pdf.add_font(family, "B", p)
    pdf.add_font(family, "I", p)
    pdf.add_font(family, "BI", p)


def strip_outer_md_fence(text: str) -> str:
    """
    若模型将整个回答包在 ```markdown ... ``` 中，去掉围栏以便正确解析。
    """
    s = text.strip()
    m = re.match(r"^```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$", s, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return s

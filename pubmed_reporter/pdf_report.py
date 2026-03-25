"""使用 fpdf2 生成中文 PDF 报告（优先将 Markdown 渲染为 HTML 再写入 PDF）。"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

from pubmed_reporter.config import Settings
from pubmed_reporter.font_utils import resolve_chinese_font
from pubmed_reporter.markdown_render import (
    build_tag_styles_for_family,
    llm_markdown_to_html,
    register_ttf_family_all_styles,
    strip_outer_md_fence,
)


class ReportPDF(FPDF):
    """支持中文字体注册与简易 Markdown 回退。"""

    def __init__(self, font_path: Path | None) -> None:
        super().__init__()
        self._font_path = font_path
        self._use_unicode = False
        self._cjk_registered = False

    def setup_font(self) -> None:
        if self._font_path and self._font_path.suffix.lower() in (".ttf", ".ttc"):
            try:
                if not self._cjk_registered:
                    register_ttf_family_all_styles(self, "zh", str(self._font_path))
                    self._cjk_registered = True
                self.set_font("zh", size=11)
                self._use_unicode = True
                return
            except Exception:
                pass
        self.set_font("Helvetica", size=11)
        self._use_unicode = False

    def add_markdown_like_text(self, text: str) -> None:
        """无中文字体或 HTML 失败时的简易回退（仅处理少量标题前缀）。"""
        self.set_auto_page_break(auto=True, margin=15)
        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            for line in block.split("\n"):
                line = line.strip()
                line = re.sub(r"^\*\*(.+?)\*\*$", r"\1", line)
                if line.startswith("# "):
                    if self._use_unicode:
                        self.set_font("zh", size=16)
                    else:
                        self.set_font("Helvetica", "B", 16)
                    self.multi_cell(0, 10, self._safe(line[2:]))
                    self.ln(2)
                    self.setup_font()
                elif line.startswith("## "):
                    if self._use_unicode:
                        self.set_font("zh", size=14)
                    else:
                        self.set_font("Helvetica", "B", 14)
                    self.multi_cell(0, 9, self._safe(line[3:]))
                    self.ln(1)
                    self.setup_font()
                else:
                    if self._use_unicode:
                        self.set_font("zh", size=11)
                    else:
                        self.set_font("Helvetica", size=11)
                    self.multi_cell(0, 6, self._safe(line))
                    self.ln(1)
            self.ln(2)

    def _safe(self, s: str) -> str:
        if self._use_unicode:
            return s
        return s.encode("latin-1", errors="replace").decode("latin-1")

    def write_body_markdown_html(self, md_body: str) -> None:
        """将 Markdown 转为 HTML 后由 fpdf2 排版（需已注册 zh 全样式）。"""
        cleaned = strip_outer_md_fence(md_body)
        html = llm_markdown_to_html(cleaned)
        styles = build_tag_styles_for_family("zh")
        self.set_auto_page_break(auto=True, margin=15)
        with self.local_context():
            self.write_html(
                html,
                tag_styles=styles,
                warn_on_tags_not_matching=False,
            )


def write_report_pdf(
    settings: Settings,
    title: str,
    body: str,
    output_path: Path,
) -> Path:
    font = resolve_chinese_font(settings)
    pdf = ReportPDF(font)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    pdf.setup_font()

    if pdf._use_unicode:
        pdf.set_font("zh", size=18)
    else:
        pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, pdf._safe(title))
    pdf.ln(6)

    pdf.setup_font()
    if pdf._use_unicode:
        try:
            pdf.write_body_markdown_html(body)
        except Exception:
            pdf.setup_font()
            pdf.add_markdown_like_text(body)
    else:
        pdf.add_markdown_like_text(body)

    output_path = Path(output_path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path

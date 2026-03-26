"""将 LLM 报告正文写入 UTF-8 文本文件。"""

from __future__ import annotations

from pathlib import Path


def normalize_report_output_path(path: Path) -> Path:
    """若用户仍传入 .pdf 路径，改为同名的 .txt，避免扩展名与内容不符。"""
    p = Path(path).expanduser()
    if p.suffix.lower() == ".pdf":
        return p.with_suffix(".txt")
    return p


def write_report_txt(title: str, body: str, output_path: Path) -> Path:
    """写入带标题行的 UTF-8 文本报告。"""
    out = normalize_report_output_path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    title_line = title.strip() or "文献分析报告"
    sep = "=" * min(max(len(title_line), 8), 80)
    text = f"{title_line}\n{sep}\n\n{body.strip()}\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    return out

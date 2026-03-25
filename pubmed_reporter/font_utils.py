"""中文字体路径探测（macOS / Linux / Windows）。"""

from __future__ import annotations

from pathlib import Path

from pubmed_reporter.config import Settings


def resolve_chinese_font(settings: Settings) -> Path | None:
    if settings.chinese_font_path:
        return settings.chinese_font_path

    candidates = [
        # macOS
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        # Linux 常见
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        # Windows
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None

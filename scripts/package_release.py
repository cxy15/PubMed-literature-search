#!/usr/bin/env python3
"""生成不含密钥与虚拟环境的发布用 zip 包。"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "文献检索-分享包.zip"
ARCHIVE_TOP = "文献检索"


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if ".venv" in parts or "__pycache__" in parts:
        return True
    if ".git" in parts:
        return True
    if rel.name == ".env":
        return True
    if rel.name == ".DS_Store":
        return True
    if len(parts) >= 1 and parts[0] == "logs" and rel.suffix == ".log":
        return True
    if rel.name == OUT.name:
        return True
    return False


def main() -> None:
    paths = [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and not should_skip(p)
    ]
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            arcname = Path(ARCHIVE_TOP) / p.relative_to(ROOT)
            zf.write(p, arcname)
    print(f"已生成: {OUT} ({OUT.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()

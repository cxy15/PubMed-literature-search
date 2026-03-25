"""从 run.bat 调用：在 .env 中写入或替换一行 KEY=value（UTF-8）。"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: env_write.py KEY VALUE", file=sys.stderr)
        sys.exit(2)
    key, val = sys.argv[1], sys.argv[2]
    p = Path(".env")
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    prefix = f"{key}="
    out = [ln for ln in lines if not ln.strip().startswith(prefix)]
    out.append(f"{key}={val}")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

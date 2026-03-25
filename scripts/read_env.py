"""从 run.bat 调用：打印 .env 中某一键的值（供批处理 for /f 捕获）。"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(2)
    load_dotenv()
    v = os.getenv(sys.argv[1], "") or ""
    if sys.argv[1] == "ENTREZ_EMAIL" and (
        "your_email" in v.lower() or v.strip() == "your_email@example.com"
    ):
        v = ""
    if sys.argv[1] == "OPENAI_API_KEY" and v.strip() == "sk-...":
        v = ""
    print(v)


if __name__ == "__main__":
    main()

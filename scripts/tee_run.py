"""从 run.bat 调用：将 pubmed_reporter 子进程的 stdout/stderr 同时打印并追加到日志文件。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "用法: tee_run.py LOG_FILE [传给 python -m pubmed_reporter 的参数...]",
            file=sys.stderr,
        )
        sys.exit(2)
    log_path = Path(sys.argv[1])
    args = sys.argv[2:]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-u", "-m", "pubmed_reporter", *args]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    with open(log_path, "a", encoding="utf-8") as f:
        for line in proc.stdout:
            print(line, end="")
            f.write(line)
    raise SystemExit(proc.wait())


if __name__ == "__main__":
    main()

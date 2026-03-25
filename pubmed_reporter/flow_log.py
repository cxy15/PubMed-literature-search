"""流程追踪：统一输出到 stderr，便于终端与 run.sh 的 tee 日志同时记录。"""

from __future__ import annotations

import sys
from datetime import datetime


def flow_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def flow_info(msg: str) -> None:
    """单行或多行（含换行）流程信息。"""
    for line in msg.splitlines():
        print(f"[pubmed_reporter] [{flow_ts()}] {line}", file=sys.stderr)

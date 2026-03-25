#!/usr/bin/env python3
"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from pubmed_reporter.config import load_settings
from pubmed_reporter.flow_log import flow_info
from pubmed_reporter import modes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="基于 PubMed（NCBI E-utilities）与 OpenAI 兼容 Chat Completions 的文献检索与中文 PDF 报告。",
        epilog=(
            "环境变量：ENTREZ_EMAIL（NCBI 要求的联系邮箱）；可选 NCBI_API_KEY（eutils 的 api_key= 参数）。"
            "LLM：OPENAI_API_KEY + OPENAI_BASE_URL（一般为 …/v1）指向任意兼容服务，无需使用 ChatGPT。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("report.pdf"),
        help="输出 PDF 路径（默认 report.pdf）",
    )
    parser.add_argument(
        "-n",
        "--retmax",
        type=int,
        default=80,
        help="单次检索返回并拉取详情的最大文献条数（默认 80，可调）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_rev = sub.add_parser("review", help="综述模式：围绕检索意图检索并生成简报")
    p_rev.add_argument(
        "keyword",
        help="检索意图的自然语言描述（中/英均可），将经 LLM 转为 PubMed 检索式",
    )
    p_rev.add_argument(
        "-q",
        "--raw-query",
        dest="raw_query",
        default=None,
        metavar="QUERY",
        help="跳过 LLM 翻译，直接使用此 PubMed 检索式",
    )
    p_rev.add_argument(
        "-a",
        "--authoritative",
        action="store_true",
        help="限定为权威生物医学期刊子集（在检索式中追加期刊过滤）",
    )

    p_tr = sub.add_parser("trend", help="研究趋势：近若干年文献按时序分析热点变化")
    p_tr.add_argument(
        "keyword",
        help="检索意图的自然语言描述（中/英均可），将经 LLM 转为 PubMed 检索式",
    )
    p_tr.add_argument(
        "-q",
        "--raw-query",
        dest="raw_query",
        default=None,
        metavar="QUERY",
        help="跳过 LLM 翻译，直接使用此 PubMed 检索式",
    )
    p_tr.add_argument(
        "-y",
        "--years",
        type=int,
        default=5,
        help="回溯年数（默认 5）",
    )

    p_au = sub.add_parser("author", help="作者分析：按作者检索并归纳研究方向")
    p_au.add_argument(
        "name",
        help="作者或检索意图的自然语言描述（中/英均可），将经 LLM 转为 PubMed 检索式",
    )
    p_au.add_argument(
        "-q",
        "--raw-query",
        dest="raw_query",
        default=None,
        metavar="QUERY",
        help="跳过 LLM 翻译，直接使用此 PubMed 检索式",
    )

    args = parser.parse_args()
    settings = load_settings()

    if not settings.entrez_email:
        print("错误：请在环境变量 ENTREZ_EMAIL 中设置 NCBI 要求的联系邮箱。", file=sys.stderr)
        return 1
    if not settings.openai_api_key:
        print("错误：请在环境变量 OPENAI_API_KEY 中设置 API 密钥。", file=sys.stderr)
        return 1

    modes.warn_if_no_cjk_font(settings)

    flow_info(
        f"CLI 子命令: {args.command}  retmax={args.retmax}  输出 PDF: {args.output}"
    )

    try:
        if args.command == "review":
            path = modes.run_review(
                settings,
                args.keyword,
                query=args.raw_query,
                authoritative_journals=args.authoritative,
                retmax=args.retmax,
                output_pdf=args.output,
            )
        elif args.command == "trend":
            path = modes.run_trend(
                settings,
                args.keyword,
                raw_query=args.raw_query,
                years=args.years,
                retmax=args.retmax,
                output_pdf=args.output,
            )
        elif args.command == "author":
            path = modes.run_author(
                settings,
                args.name,
                raw_query=args.raw_query,
                retmax=args.retmax,
                output_pdf=args.output,
            )
        else:
            return 1
    except Exception as e:
        print(f"执行失败: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    print(f"已生成: {path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

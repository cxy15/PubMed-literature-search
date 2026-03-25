"""三种工作模式：综述、趋势、作者分析。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from pubmed_reporter import entrez_client
from pubmed_reporter.config import Settings
from pubmed_reporter.flow_log import flow_info
from pubmed_reporter.llm_client import chat_completion
from pubmed_reporter.prompts import (
    SYSTEM_ZH,
    build_author_user_prompt,
    build_review_user_prompt,
    build_trend_user_prompt,
)
from pubmed_reporter.pdf_report import write_report_pdf
from pubmed_reporter.query_builder import natural_language_to_pubmed_query
from pubmed_reporter.retrieval_log import save_retrieved_articles_to_logs


def _emit_final_search_term(term: str) -> None:
    """在即将请求 NCBI 前，完整展示最终检索式（与 esearch 使用的一致）。"""
    flow_info("实际用于检索的 PubMed 表达式（完整）：\n" + term.strip())


def run_review(
    settings: Settings,
    keyword: str,
    *,
    query: str | None,
    authoritative_journals: bool,
    retmax: int,
    output_pdf: Path,
) -> Path:
    if query:
        term = query.strip()
        flow_info("已使用手工检索式（--raw-query），跳过「自然语言 → PubMed 检索式」的 LLM。")
    else:
        term = natural_language_to_pubmed_query(
            settings,
            keyword,
            mode="review",
            authoritative_journals=authoritative_journals,
        )

    _emit_final_search_term(term)

    entrez_client.configure_entrez(settings.entrez_email, settings.ncbi_api_key)
    result = entrez_client.search_pubmed(term, retmax=retmax, sort="relevance")

    snap = save_retrieved_articles_to_logs(
        result,
        mode="review",
        extra_meta={"user_keyword": keyword},
    )
    flow_info(f"已保存检索文献快照（LLM 分析前）：{snap.resolve()}")

    user_prompt = build_review_user_prompt(
        keyword, term, result.total_count, result.articles
    )

    report = chat_completion(
        settings,
        SYSTEM_ZH,
        user_prompt,
        temperature=0.35,
        flow_stage="LLM：生成中文文献报告（综述）",
    )
    title = f"「文献综述简报」{keyword}"
    flow_info("开始 | 写入 PDF 文件")
    path = write_report_pdf(settings, title, report, output_pdf)
    flow_info(f"完成 | 写入 PDF 文件：{path.resolve()}")
    return path


def run_trend(
    settings: Settings,
    keyword: str,
    *,
    raw_query: str | None,
    years: int,
    retmax: int,
    output_pdf: Path,
) -> Path:
    now = datetime.now().year
    mindate = str(now - years + 1)
    maxdate = str(now)
    if raw_query:
        term = raw_query.strip()
        flow_info("已使用手工检索式（--raw-query），跳过「自然语言 → PubMed 检索式」的 LLM。")
    else:
        term = natural_language_to_pubmed_query(
            settings,
            keyword,
            mode="trend",
            years=years,
        )

    _emit_final_search_term(term)

    entrez_client.configure_entrez(settings.entrez_email, settings.ncbi_api_key)
    result = entrez_client.search_pubmed(
        term,
        retmax=retmax,
        sort="pub_date",
        mindate=mindate,
        maxdate=maxdate,
    )

    snap = save_retrieved_articles_to_logs(
        result,
        mode="trend",
        extra_meta={
            "user_keyword": keyword,
            "years": str(years),
            "pdat_range": f"{mindate}–{maxdate}",
        },
    )
    flow_info(f"已保存检索文献快照（LLM 分析前）：{snap.resolve()}")

    user_prompt = build_trend_user_prompt(
        keyword,
        years,
        mindate,
        maxdate,
        term,
        result.total_count,
        result.articles,
    )

    report = chat_completion(
        settings,
        SYSTEM_ZH,
        user_prompt,
        temperature=0.4,
        flow_stage="LLM：生成中文文献报告（研究趋势）",
    )
    title = f"「研究趋势分析」{keyword}（{mindate}–{maxdate}）"
    flow_info("开始 | 写入 PDF 文件")
    path = write_report_pdf(settings, title, report, output_pdf)
    flow_info(f"完成 | 写入 PDF 文件：{path.resolve()}")
    return path


def run_author(
    settings: Settings,
    name: str,
    *,
    raw_query: str | None,
    retmax: int,
    output_pdf: Path,
) -> Path:
    safe = name.strip().replace("[", "").replace("]", "")
    if raw_query:
        term = raw_query.strip()
        flow_info("已使用手工检索式（--raw-query），跳过「自然语言 → PubMed 检索式」的 LLM。")
    else:
        term = natural_language_to_pubmed_query(settings, name, mode="author")

    _emit_final_search_term(term)

    entrez_client.configure_entrez(settings.entrez_email, settings.ncbi_api_key)
    result = entrez_client.search_pubmed(term, retmax=retmax, sort="pub_date")

    snap = save_retrieved_articles_to_logs(
        result,
        mode="author",
        extra_meta={"user_input": safe},
    )
    flow_info(f"已保存检索文献快照（LLM 分析前）：{snap.resolve()}")

    user_prompt = build_author_user_prompt(term, result.total_count, result.articles)

    report = chat_completion(
        settings,
        SYSTEM_ZH,
        user_prompt,
        temperature=0.35,
        flow_stage="LLM：生成中文文献报告（作者画像）",
    )
    title = f"「作者研究画像」{safe}"
    flow_info("开始 | 写入 PDF 文件")
    path = write_report_pdf(settings, title, report, output_pdf)
    flow_info(f"完成 | 写入 PDF 文件：{path.resolve()}")
    return path


def warn_if_no_cjk_font(settings: Settings) -> None:
    from pubmed_reporter.font_utils import resolve_chinese_font

    if resolve_chinese_font(settings) is None:
        print(
            "警告：未找到可用的中文字体文件，PDF 可能无法正确显示中文。"
            "请设置环境变量 CHINESE_FONT_PATH 指向 .ttf/.ttc 字体。",
            file=sys.stderr,
        )

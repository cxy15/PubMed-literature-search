"""三种工作模式：综述、趋势、作者分析。"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pubmed_reporter import entrez_client
from pubmed_reporter.config import Settings
from pubmed_reporter.llm_client import chat_completion
from pubmed_reporter.models import PubMedArticle
from pubmed_reporter.pdf_report import write_report_pdf


SYSTEM_ZH = (
    "你是一名生物医学科研助理。请根据用户提供的 PubMed 文献列表（仅标题、作者、摘要等）"
    "进行严谨、客观的整理与分析。使用简体中文输出。不要编造未在材料中出现的结论。"
    "若摘要缺失，请如实说明并降低推断强度。"
    "报告正文请使用 Markdown 格式输出（如 ## 小节标题、**粗体**、列表、表格等），便于排版。"
)


def _articles_bundle(articles: list[PubMedArticle], max_chars: int = 120_000) -> str:
    parts: list[str] = []
    total = 0
    for i, a in enumerate(articles, 1):
        block = f"--- 文献 {i} ---\n{a.to_llm_text()}\n"
        if total + len(block) > max_chars:
            parts.append(f"\n（其余 {len(articles) - i + 1} 篇因长度限制省略）\n")
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)


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
        term = query
    else:
        term = entrez_client.build_review_query(keyword, authoritative_journals)

    entrez_client.configure_entrez(settings.entrez_email, settings.ncbi_api_key)
    result = entrez_client.search_pubmed(term, retmax=retmax, sort="relevance")

    user_prompt = f"""任务：撰写「主题综述简报」。

用户关键词：{keyword}
实际 PubMed 检索式：{term}
检索命中总数（数据库）：{result.total_count}
本次纳入分析的文献数：{len(result.articles)}

请基于下列文献信息输出一份结构化简报，包含：
1. 背景与主题概述
2. 主要研究问题与发现（分点，引用 PMID）
3. 方法学共性或争议（若有）
4. 局限与未解决问题
5. 小结

文献列表：
{_articles_bundle(result.articles)}
"""

    report = chat_completion(settings, SYSTEM_ZH, user_prompt, temperature=0.35)
    title = f"「文献综述简报」{keyword}"
    return write_report_pdf(settings, title, report, output_pdf)


def run_trend(
    settings: Settings,
    keyword: str,
    *,
    years: int,
    retmax: int,
    output_pdf: Path,
) -> Path:
    now = datetime.now().year
    mindate = str(now - years + 1)
    maxdate = str(now)
    term = f"({keyword})"
    entrez_client.configure_entrez(settings.entrez_email, settings.ncbi_api_key)
    result = entrez_client.search_pubmed(
        term,
        retmax=retmax,
        sort="pub_date",
        mindate=mindate,
        maxdate=maxdate,
    )

    by_year: dict[str, list[PubMedArticle]] = defaultdict(list)
    for a in result.articles:
        y = None
        if a.pub_date_parsed:
            y = str(a.pub_date_parsed.year)
        elif a.pub_date:
            import re as _re

            m = _re.match(r"^(\d{4})", a.pub_date.strip())
            if m:
                y = m.group(1)
        if y is None:
            y = "未知年份"
        by_year[y].append(a)

    timeline = []
    for y in sorted(by_year.keys()):
        arts = by_year[y]
        timeline.append(f"## {y} 年（{len(arts)} 篇）\n")
        for a in arts[:8]:
            timeline.append(f"- PMID {a.pmid}: {a.title[:120]}...")
        if len(arts) > 8:
            timeline.append(f"  （另有 {len(arts) - 8} 篇同年文献略）")
        timeline.append("")

    user_prompt = f"""任务：研究趋势分析（近 {years} 年）。

关键词：{keyword}
时间窗：{mindate}–{maxdate}
PubMed 检索式：{term}
检索命中总数：{result.total_count}
本次纳入：{len(result.articles)} 篇（按发表日期排序截断）

请结合下列「按年粗略列表」与完整文献摘要，分析：
1. 该主题近年的总体热度变化（可结合文献数量与主题词）
2. 不同时段的研究重点迁移（例如从机制到临床等，需有摘要依据）
3. 新兴方法、生物标志物或争议点（若有证据）
4. 未来可能的研究方向

按年摘要列表（部分展示）：
{chr(10).join(timeline)}

完整文献信息：
{_articles_bundle(result.articles)}
"""

    report = chat_completion(settings, SYSTEM_ZH, user_prompt, temperature=0.4)
    title = f"「研究趋势分析」{keyword}（{mindate}–{maxdate}）"
    return write_report_pdf(settings, title, report, output_pdf)


def run_author(
    settings: Settings,
    author_name: str,
    *,
    retmax: int,
    output_pdf: Path,
) -> Path:
    # PubMed 作者检索：姓 名[Author]
    safe = author_name.strip().replace("[", "").replace("]", "")
    term = f'"{safe}"[Author]'
    entrez_client.configure_entrez(settings.entrez_email, settings.ncbi_api_key)
    result = entrez_client.search_pubmed(term, retmax=retmax, sort="pub_date")

    user_prompt = f"""任务：作者研究方向分析。

作者检索式：{term}
检索命中总数：{result.total_count}
本次纳入文献数：{len(result.articles)}

请基于下列文献（标题与摘要）分析该作者：
1. 主要研究领域与关键词聚类
2. 时间线上的主题演变（若可辨识）
3. 常合作方向或研究类型（综述/临床试验/基础等，仅在有信息时）
4. 小结：核心贡献方向（谨慎表述，避免过度推断）

文献列表：
{_articles_bundle(result.articles)}
"""

    report = chat_completion(settings, SYSTEM_ZH, user_prompt, temperature=0.35)
    title = f"「作者研究画像」{safe}"
    return write_report_pdf(settings, title, report, output_pdf)


def warn_if_no_cjk_font(settings: Settings) -> None:
    from pubmed_reporter.font_utils import resolve_chinese_font

    if resolve_chinese_font(settings) is None:
        print(
            "警告：未找到可用的中文字体文件，PDF 可能无法正确显示中文。"
            "请设置环境变量 CHINESE_FONT_PATH 指向 .ttf/.ttc 字体。",
            file=sys.stderr,
        )

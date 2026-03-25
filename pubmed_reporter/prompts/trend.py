"""趋势模式：按年摘要列表与用户提示。"""

from __future__ import annotations

import re
from collections import defaultdict

from pubmed_reporter.models import PubMedArticle
from pubmed_reporter.prompts.common import articles_bundle


def format_trend_timeline(articles: list[PubMedArticle]) -> str:
    """按发表年份分组，生成「按年粗略列表」供趋势分析用户提示使用。"""
    by_year: dict[str, list[PubMedArticle]] = defaultdict(list)
    for a in articles:
        y = None
        if a.pub_date_parsed:
            y = str(a.pub_date_parsed.year)
        elif a.pub_date:
            m = re.match(r"^(\d{4})", a.pub_date.strip())
            if m:
                y = m.group(1)
        if y is None:
            y = "未知年份"
        by_year[y].append(a)

    timeline: list[str] = []
    for y in sorted(by_year.keys()):
        arts = by_year[y]
        timeline.append(f"## {y} 年（{len(arts)} 篇）\n")
        for art in arts[:8]:
            timeline.append(f"- PMID {art.pmid}: {art.title[:120]}...")
        if len(arts) > 8:
            timeline.append(f"  （另有 {len(arts) - 8} 篇同年文献略）")
        timeline.append("")

    return "\n".join(timeline)


def build_trend_user_prompt(
    keyword: str,
    years: int,
    mindate: str,
    maxdate: str,
    term: str,
    total_count: int,
    articles: list[PubMedArticle],
) -> str:
    timeline = format_trend_timeline(articles)
    return f"""任务：研究趋势分析（近 {years} 年）。

关键词：{keyword}
时间窗：{mindate}–{maxdate}
PubMed 检索式：{term}
检索命中总数：{total_count}
本次纳入：{len(articles)} 篇（按发表日期排序截断）

请结合下列「按年粗略列表」与完整文献摘要，分析：
1. 该主题近年的总体热度变化（可结合文献数量与主题词）
2. 不同时段的研究重点迁移（例如从机制到临床等，需有摘要依据）
3. 新兴方法、生物标志物或争议点（若有证据）
4. 未来可能的研究方向

按年摘要列表（部分展示）：
{timeline}

完整文献信息：
{articles_bundle(articles)}
"""

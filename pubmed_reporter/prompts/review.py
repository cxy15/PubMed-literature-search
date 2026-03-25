"""综述模式：用户提示。"""

from __future__ import annotations

from pubmed_reporter.models import PubMedArticle
from pubmed_reporter.prompts.common import articles_bundle


def build_review_user_prompt(
    keyword: str,
    term: str,
    total_count: int,
    articles: list[PubMedArticle],
) -> str:
    return f"""任务：撰写「主题综述简报」。

用户关键词：{keyword}
实际 PubMed 检索式：{term}
检索命中总数（数据库）：{total_count}
本次纳入分析的文献数：{len(articles)}

请基于下列文献信息输出一份结构化简报，包含：
1. 背景与主题概述
2. 主要研究问题与发现（分点，引用 PMID）
3. 方法学共性或争议（若有）
4. 局限与未解决问题
5. 小结

文献列表：
{articles_bundle(articles)}
"""

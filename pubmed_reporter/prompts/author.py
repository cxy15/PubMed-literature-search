"""作者模式：用户提示。"""

from __future__ import annotations

from pubmed_reporter.models import ArticleRelevance, PubMedArticle
from pubmed_reporter.prompts.common import articles_bundle, weighting_task_note


def build_author_user_prompt(
    term: str,
    total_count: int,
    articles: list[PubMedArticle],
    relevances: list[ArticleRelevance] | None = None,
) -> str:
    return f"""任务：作者研究方向分析。

作者检索式：{term}
检索命中总数：{total_count}
本次纳入文献数：{len(articles)}

{weighting_task_note()}

请基于下列文献（标题与摘要）分析该作者：
1. 主要研究领域与关键词聚类（优先依据高权重文献归纳）
2. 时间线上的主题演变（若可辨识）
3. 常合作方向或研究类型（综述/临床试验/基础等，仅在有信息时）
4. 小结：核心贡献方向（谨慎表述，避免过度推断）

文献列表：
{articles_bundle(articles, relevances=relevances)}
"""

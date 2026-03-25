"""向 LLM 提问的系统提示与用户提示构建（便于集中编辑提示词）。"""

from __future__ import annotations

from pubmed_reporter.prompts.author import build_author_user_prompt
from pubmed_reporter.prompts.common import SYSTEM_ZH, articles_bundle
from pubmed_reporter.prompts.review import build_review_user_prompt
from pubmed_reporter.prompts.trend import build_trend_user_prompt, format_trend_timeline
from pubmed_reporter.prompts.query_translate import (
    SYSTEM_PUBMED_QUERY,
    build_pubmed_query_user_prompt,
    normalize_llm_pubmed_query,
)

__all__ = [
    "SYSTEM_ZH",
    "SYSTEM_PUBMED_QUERY",
    "articles_bundle",
    "build_author_user_prompt",
    "build_pubmed_query_user_prompt",
    "build_review_user_prompt",
    "build_trend_user_prompt",
    "format_trend_timeline",
    "normalize_llm_pubmed_query",
]

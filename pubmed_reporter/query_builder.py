"""自然语言 → PubMed 检索式（调用 LLM）。"""

from __future__ import annotations

from pubmed_reporter.config import Settings
from pubmed_reporter.entrez_client import AUTHORITATIVE_JOURNALS_QUERY
from pubmed_reporter.llm_client import chat_completion
from pubmed_reporter.prompts.query_translate import (
    SYSTEM_PUBMED_QUERY,
    Mode,
    build_pubmed_query_user_prompt,
    normalize_llm_pubmed_query,
)


def natural_language_to_pubmed_query(
    settings: Settings,
    natural_language: str,
    *,
    mode: Mode,
    years: int | None = None,
    authoritative_journals: bool = False,
) -> str:
    """
    将自然语言转为 PubMed 检索式；失败或空结果时抛出 ValueError。
    authoritative_journals: 仅 review 有效，在检索式后追加权威期刊过滤。
    """
    user = build_pubmed_query_user_prompt(natural_language, mode, years=years)
    raw = chat_completion(
        settings,
        SYSTEM_PUBMED_QUERY,
        user,
        temperature=0.15,
        flow_stage="LLM：自然语言 → PubMed 检索式",
    )
    q = normalize_llm_pubmed_query(raw)
    if not q:
        raise ValueError("模型未返回可用的 PubMed 检索式，请重试或改用 --raw-query 手工指定。")

    if mode == "review" and authoritative_journals:
        return f"({q}) AND {AUTHORITATIVE_JOURNALS_QUERY}"
    if mode == "trend":
        return f"({q})"
    return q

"""LLM 共用：系统提示与文献列表拼装。"""

from __future__ import annotations

from pubmed_reporter.models import PubMedArticle

SYSTEM_ZH = (
    "你是一名生物医学科研助理。请根据用户提供的 PubMed 文献列表（仅标题、作者、摘要等）"
    "进行严谨、客观的整理与分析。使用简体中文输出。不要编造未在材料中出现的结论。"
    "若摘要缺失，请如实说明并降低推断强度。"
    "文献块以「文献 k/n | PMID …」分隔，综述或分点引用时必须对应同一 PMID 下的标题与摘要，勿张冠李戴。"
    "报告正文请使用 Markdown 格式输出（如 ## 小节标题、**粗体**、列表、表格等），便于排版。"
)


def articles_bundle(articles: list[PubMedArticle], max_chars: int = 120_000) -> str:
    """将多篇文献拼接为送入用户提示的文本块（超长时截断并提示省略篇数）。"""
    parts: list[str] = []
    total = 0
    n = len(articles)
    for i, a in enumerate(articles, 1):
        pmid = (a.pmid or "").strip() or "未知"
        block = f"--- 文献 {i}/{n} | PMID {pmid} ---\n{a.to_llm_text()}\n"
        if total + len(block) > max_chars:
            parts.append(f"\n（其余 {len(articles) - i + 1} 篇因长度限制省略）\n")
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)

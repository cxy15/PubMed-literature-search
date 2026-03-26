"""LLM 共用：系统提示与文献列表拼装。"""

from __future__ import annotations

from pubmed_reporter.models import ArticleRelevance, PubMedArticle

SYSTEM_ZH = (
    "你是一名生物医学科研助理。请根据用户提供的 PubMed 文献列表（仅标题、作者、摘要等）"
    "进行严谨、客观的整理与分析。使用简体中文输出。不要编造未在材料中出现的结论。"
    "若摘要缺失，请如实说明并降低推断强度。"
    "每篇文献前会标注「相对检索式的相关性：等级 + 权重」。权重越高表示与本次检索式越相关；"
    "请在综合结论、分点论述与篇幅分配上优先依据高权重文献，对低权重文献仅作补充或简述，并在必要时说明其相关性较弱。"
    "文献块以「文献 k/n | PMID …」分隔，综述或分点引用时必须对应同一 PMID 下的标题与摘要，勿张冠李戴。"
    "报告正文请使用 Markdown 格式输出（如 ## 小节标题、**粗体**、列表、表格等），便于排版。"
)


def articles_bundle(
    articles: list[PubMedArticle],
    max_chars: int = 120_000,
    relevances: list[ArticleRelevance] | None = None,
) -> str:
    """将多篇文献拼接为送入用户提示的文本块（超长时截断并提示省略篇数）。

    relevances 与 articles 等长时，在每篇前标注相关性等级与权重，供下游加权分析。
    """
    parts: list[str] = []
    total = 0
    n = len(articles)
    for i, a in enumerate(articles, 1):
        pmid = (a.pmid or "").strip() or "未知"
        head = f"--- 文献 {i}/{n} | PMID {pmid} ---\n"
        if relevances is not None and i - 1 < len(relevances):
            r = relevances[i - 1]
            head += (
                f"相对检索式相关性：{r.level}（权重 {r.weight:.2f}，1.0 为最高）\n"
                f"分级理由：{r.rationale}\n"
            )
        block = head + f"{a.to_llm_text()}\n"
        if total + len(block) > max_chars:
            parts.append(f"\n（其余 {len(articles) - i + 1} 篇因长度限制省略）\n")
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)


def weighting_task_note() -> str:
    """各模式用户提示中说明加权分析要求的共用段落。"""
    return (
        "相关性分级说明：下列每篇文献已按「本次 PubMed 检索式」由模型预先评为 高/中/低 三档，"
        "并映射为权重（高=1.0，中=0.55，低=0.25）。"
        "撰写报告时请让高权重文献占据主要论证与引用篇幅，中权重作支撑，低权重仅简要提及或标注为边缘相关。"
    )

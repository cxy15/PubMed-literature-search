"""相关性分级：相对 PubMed 检索式，为每篇文献打高/中/低等级。"""

from __future__ import annotations

from pubmed_reporter.models import PubMedArticle


SYSTEM_RELEVANCE_ZH = (
    "你是生物医学文献检索评估助手。用户会给出一条 PubMed 检索式，以及若干篇该次检索返回的文献（标题与摘要）。"
    "请逐篇判断每篇文献与「该检索式所表达的信息需求」的贴合程度，并给出等级与一句理由。"
    "等级仅允许三档：高、中、低。"
    "「高」：主题、人群、干预、结局或方法学与检索意图高度一致，摘要足以支撑纳入分析。"
    "「中」：部分相关、范围较宽、或仅标题/摘要一侧较贴题。"
    "「低」：明显偏离检索意图、仅边缘相关、或信息过少难以判断（仍须标注为低并说明）。"
    "不要编造摘要中不存在的内容。输出必须是合法 JSON 数组，不要 Markdown 围栏以外的多余文字。"
)


def _compact_block(a: PubMedArticle, index: int, total: int) -> str:
    abs_text = (a.abstract or "").strip()
    if len(abs_text) > 2000:
        abs_text = abs_text[:2000] + "…（摘要截断）"
    pmid = (a.pmid or "").strip() or "未知"
    title = (a.title or "").strip() or "（无标题）"
    return (
        f"[{index}/{total}] PMID={pmid}\n"
        f"标题: {title}\n"
        f"摘要:\n{abs_text if abs_text else '（无摘要）'}\n"
    )


def build_relevance_user_prompt(term: str, articles: list[PubMedArticle]) -> str:
    n = len(articles)
    blocks = [_compact_block(a, i, n) for i, a in enumerate(articles, start=1)]
    return f"""PubMed 检索式（请作为相关性判据）：
{term.strip()}

共 {n} 篇文献，请为每一篇输出一个 JSON 对象，字段如下：
- "pmid": 字符串，与下方文献块中的 PMID 完全一致
- "level": 字符串，必须是 "高"、"中"、"低" 之一
- "rationale": 字符串，一句话说明理由（中文）

将所有对象放入一个 JSON 数组，顺序与文献列表顺序一致，且必须覆盖全部 {n} 篇（不得遗漏）。

文献列表：
{"".join(blocks)}
"""


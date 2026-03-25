"""自然语言 → PubMed 检索式（供首次检索前单独调用 LLM）。"""

from __future__ import annotations

import re
from typing import Literal

Mode = Literal["review", "trend", "author"]

__all__ = [
    "Mode",
    "SYSTEM_PUBMED_QUERY",
    "build_pubmed_query_user_prompt",
    "normalize_llm_pubmed_query",
]

SYSTEM_PUBMED_QUERY = (
    "你是 PubMed / MEDLINE 检索助手。你的唯一任务是：根据用户的自然语言描述，"
    "写出合法、可执行的 PubMed 检索表达式（单行）。"
    "不要输出解释、寒暄或 Markdown 排版；不要编造不存在的 MeSH 正式主题词；"
    "不确定时优先使用 [Title/Abstract] 与常见英文关键词组合。"
)


def build_pubmed_query_user_prompt(
    natural_language: str,
    mode: Mode,
    *,
    years: int | None = None,
) -> str:
    """构建「仅生成检索式」的用户提示。"""
    text = natural_language.strip()
    if mode == "review":
        return f"""用户的检索意图（可为中文或英文自然语言）：
{text}

请将其转换为一条可在 PubMed 使用的检索表达式（单行字符串）。
要求：
- 仅输出检索式本身，不要序号、不要前后缀说明。
- 合理使用字段标签，如 [Title/Abstract]、[MeSH Terms]、[Publication Type] 等；用 AND、OR、括号组合。
- 主题可适当同义词 OR 扩展；避免单条过宽导致大量无关文献。"""

    if mode == "trend":
        y = years if years is not None else 5
        return f"""用户的检索意图（可为中文或英文自然语言）：
{text}

请将其转换为一条 PubMed 检索表达式（单行字符串）。
说明：本程序会在检索时**单独**限定近 {y} 年的发表日期，你不要在检索式里写日期范围。
要求：
- 仅输出检索式本身。
- 聚焦主题与人群/疾病/干预等同义词扩展，用 AND/OR 与字段标签组织。"""

    # author
    return f"""用户描述（可为中文或英文；可能只有作者姓名，也可能包含研究方向、机构等）：
{text}

请转换为一条 PubMed 检索表达式（单行字符串）。
要求：
- 仅输出检索式本身。
- 若主要是作者检索，使用 "Lastname Initials"[Author] 形式（姓与名首字母按 PubMed 惯例）；若同时限定主题，用 AND 连接主题条件。
- 若用户写的是中文姓名，请合理转换为英文发表时常见拼写或仅姓+名的检索策略。"""


def normalize_llm_pubmed_query(raw: str) -> str:
    """从模型输出中提取单行 PubMed 检索式。"""
    s = raw.strip()
    if not s:
        return ""

    m = re.match(r"^```(?:\w*)?\s*\n([\s\S]*?)\n```\s*$", s)
    if m:
        s = m.group(1).strip()

    line = s.split("\n", 1)[0].strip()
    for prefix in ("PubMed:", "检索式:", "Query:", "Answer:", "表达式:"):
        if line.lower().startswith(prefix.lower()):
            line = line[len(prefix) :].strip()

    if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
        inner = line[1:-1].strip()
        if inner and "\n" not in inner:
            line = inner

    return line.strip()

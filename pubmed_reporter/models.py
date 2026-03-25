"""文献记录数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PubMedArticle:
    """单篇 PubMed 文献（不含全文）。"""

    pmid: str
    title: str
    abstract: str
    authors: list[str]
    journal: str
    pub_date: str  # 原始字符串，如 "2024 Jan 15" 或 "2024"
    pub_date_parsed: date | None = None
    doi: str | None = None

    def to_llm_text(self) -> str:
        lines = [
            f"PMID: {self.pmid}",
            f"标题: {self.title}",
            f"期刊: {self.journal}",
            f"发表日期: {self.pub_date}",
            f"作者: {', '.join(self.authors) if self.authors else '未知'}",
        ]
        if self.doi:
            lines.append(f"DOI: {self.doi}")
        lines.append("")
        lines.append("摘要:")
        lines.append(self.abstract.strip() if self.abstract else "（无摘要）")
        return "\n".join(lines)


@dataclass
class SearchResult:
    """一次检索结果。"""

    query: str
    total_count: int
    retrieved_ids: list[str]
    articles: list[PubMedArticle] = field(default_factory=list)

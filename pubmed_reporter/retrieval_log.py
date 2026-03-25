"""将 NCBI 拉取到的文献在送 LLM 前落盘到 logs/，便于核对 PMID 与顺序。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pubmed_reporter.models import PubMedArticle, SearchResult


def _format_article_block(article: PubMedArticle, index: int, total: int) -> str:
    """单篇文献：固定字段顺序，便于人工与程序核对。"""
    pmid = article.pmid.strip() if article.pmid else "（缺失）"
    doi = article.doi.strip() if article.doi else "（无）"
    title = article.title.replace("\r", " ").replace("\n", " ").strip() or "（无标题）"
    journal = article.journal.replace("\r", " ").replace("\n", " ").strip() or "（无）"
    pub_date = article.pub_date.replace("\r", " ").replace("\n", " ").strip() or "（无）"
    authors = ", ".join(article.authors) if article.authors else "（无）"
    abstract = article.abstract.strip() if article.abstract else "（无摘要）"

    lines = [
        "=" * 78,
        f"序号: {index} / {total}",
        f"PMID: {pmid}",
        f"DOI: {doi}",
        f"标题: {title}",
        f"期刊: {journal}",
        f"发表日期: {pub_date}",
        f"作者: {authors}",
        "摘要:",
        abstract,
    ]
    return "\n".join(lines) + "\n"


def _pmid_alignment_notes(
    retrieved_ids: list[str], articles: list[PubMedArticle]
) -> list[str]:
    notes: list[str] = []
    n = min(len(retrieved_ids), len(articles))
    mismatches = 0
    for i in range(n):
        rid = retrieved_ids[i].strip()
        aid = (articles[i].pmid or "").strip()
        if rid and aid and rid != aid:
            mismatches += 1
            notes.append(f"  位置 {i + 1}: IdList={rid}  Medline PMID={aid}")
    if len(retrieved_ids) != len(articles):
        notes.append(
            f"  条数不一致: esearch 返回 PMID 数={len(retrieved_ids)}，"
            f"efetch 解析条数={len(articles)}"
        )
    if mismatches:
        notes.insert(0, f"  PMID 与 IdList 不一致的条目数: {mismatches}")
    return notes


def save_retrieved_articles_to_logs(
    result: SearchResult,
    *,
    mode: str,
    extra_meta: dict[str, str] | None = None,
) -> Path:
    """
    将本次检索得到的文献写入 logs/retrieved_{mode}_{时间戳}.txt。
    写入顺序与 result.articles 一致，且与送入 LLM 的 articles_bundle 顺序一致。
    """
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = log_dir / f"retrieved_{mode}_{stamp}.txt"

    articles = result.articles
    total = len(articles)
    iso_now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    align = _pmid_alignment_notes(result.retrieved_ids, articles)
    align_section = "是（IdList 与逐条 PMID 一致）"
    if align:
        align_section = "存在差异，见下方「一致性说明」"

    header_lines = [
        "# PubMed 检索快照（在调用「报告生成 LLM」之前写入）",
        "# 字段与文献顺序与送入 LLM 的列表一致，便于核对分析是否错位。",
        f"#",
        f"generated_at_local: {iso_now}",
        f"mode: {mode}",
        f"pubmed_query: {result.query.replace(chr(10), ' ').strip()}",
        f"database_count_total: {result.total_count}",
        f"esearch_returned_pmids: {len(result.retrieved_ids)}",
        f"efetch_parsed_articles: {total}",
        f"pmid_order_matches_idlist: {align_section}",
    ]
    if extra_meta:
        for k, v in extra_meta.items():
            header_lines.append(f"{k}: {v}")

    id_preview = ", ".join(result.retrieved_ids[:50])
    if len(result.retrieved_ids) > 50:
        id_preview += f", ...（共 {len(result.retrieved_ids)} 个）"
    header_lines.append(f"esearch_idlist_order: {id_preview}")

    blocks: list[str] = ["\n".join(header_lines) + "\n"]
    if align:
        blocks.append("----- 一致性说明 -----\n" + "\n".join(align) + "\n\n")

    blocks.append("----- 文献列表（序号与 LLM 输入一致） -----\n\n")
    for i, art in enumerate(articles, start=1):
        blocks.append(_format_article_block(art, i, total))

    text = "".join(blocks)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path

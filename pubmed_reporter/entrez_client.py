"""NCBI E-utilities：PubMed 检索与 Medline 解析。

说明（与官方一致）：
  - email：NCBI 要求提供的联系信息（Entrez.email），用于政策与追踪，不是 API 鉴权凭证。
  - api_key：可选。在 https://www.ncbi.nlm.nih.gov/account/settings/ 申请后，请求 URL 会带上
    api_key=YOUR_KEY（Biopython 中设置 Entrez.api_key），无 key 时仍可用但速率限制更严。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from Bio import Entrez, Medline

from pubmed_reporter.flow_log import flow_info
from pubmed_reporter.models import PubMedArticle, SearchResult

# NCBI 建议单次 efetch 不超过约 200 条
EFETCH_BATCH = 200


def configure_entrez(email: str, ncbi_api_key: str | None = None) -> None:
    Entrez.email = email
    Entrez.tool = "pubmed_reporter"
    # 对应 eutils URL 中的 &api_key=…；未设置时为 None（Biopython 不附加该参数）
    Entrez.api_key = ncbi_api_key.strip() if ncbi_api_key else None


def _parse_medline_date(dp: str | None) -> tuple[str, date | None]:
    if not dp:
        return "", None
    s = dp.strip()
    # 常见格式: "2024 Jan 15" / "2024 Jan" / "2024"
    m = re.match(r"^(\d{4})\s+([A-Za-z]{3})(?:\s+(\d{1,2}))?", s)
    if m:
        y, mon_s, d = m.group(1), m.group(2), m.group(3)
        months = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }
        mo = months.get(mon_s[:3].title(), 1)
        day = int(d) if d else 1
        try:
            return s, date(int(y), mo, day)
        except ValueError:
            return s, None
    m2 = re.match(r"^(\d{4})$", s)
    if m2:
        y = int(m2.group(1))
        return s, date(y, 1, 1)
    return s, None


def _first(rec: dict[str, Any], key: str) -> str:
    v = rec.get(key)
    if v is None:
        return ""
    if isinstance(v, list):
        return v[0] if v else ""
    return str(v)


def _list_field(rec: dict[str, Any], key: str) -> list[str]:
    v = rec.get(key)
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()] if str(v).strip() else []


def medline_record_to_article(rec: dict[str, Any]) -> PubMedArticle:
    pmid = _first(rec, "PMID") or ""
    title = _first(rec, "TI") or _first(rec, "BTI") or ""
    abstract = _first(rec, "AB") or ""
    authors = _list_field(rec, "AU")
    journal = _first(rec, "JT") or _first(rec, "TA") or ""
    dp_raw = _first(rec, "DP")
    dp_str, parsed = _parse_medline_date(dp_raw or None)
    doi = None
    for aid in _list_field(rec, "AID"):
        if "[doi]" in aid.lower():
            doi = aid.split("[", 1)[0].strip()
            break

    return PubMedArticle(
        pmid=pmid,
        title=title.replace("\n", " ").strip(),
        abstract=abstract.replace("\n", " ").strip(),
        authors=authors,
        journal=journal,
        pub_date=dp_str,
        pub_date_parsed=parsed,
        doi=doi or None,
    )


def search_pubmed(
    term: str,
    *,
    retmax: int = 100,
    sort: str = "relevance",
    mindate: str | None = None,
    maxdate: str | None = None,
) -> SearchResult:
    """
    检索 PubMed。

    :param term: PubMed 检索式
    :param retmax: 单次返回的最大条数（上限可调，受 NCBI 政策限制建议勿过大）
    :param sort: relevance | pub_date（近期优先用 pub_date）
    :param mindate/maxdate: 可选，格式 YYYY 或 YYYY/MM/DD
    """
    esearch_params: dict[str, Any] = {
        "db": "pubmed",
        "term": term,
        "retmax": min(retmax, 10000),
        "sort": sort,
        "retmode": "xml",
    }
    if mindate:
        esearch_params["mindate"] = mindate
    if maxdate:
        esearch_params["maxdate"] = maxdate
    if mindate or maxdate:
        esearch_params["datetype"] = "pdat"

    date_hint = ""
    if mindate or maxdate:
        date_hint = f" 日期范围 {mindate or '…'}–{maxdate or '…'} (pdat)"
    preview = term.replace("\n", " ").strip()
    if len(preview) > 600:
        preview = preview[:597] + "..."
    flow_info(
        "开始 | PubMed 检索（NCBI E-utilities：esearch + efetch）\n"
        f"  sort={sort}  retmax={retmax}{date_hint}\n"
        f"  检索式：{preview}"
    )

    handle = Entrez.esearch(**esearch_params)
    try:
        summary = Entrez.read(handle)
    finally:
        handle.close()

    id_list = summary.get("IdList", [])
    total = int(summary.get("Count", 0))

    articles: list[PubMedArticle] = []
    for i in range(0, len(id_list), EFETCH_BATCH):
        batch = id_list[i : i + EFETCH_BATCH]
        if not batch:
            break
        fhandle = Entrez.efetch(
            db="pubmed",
            id=",".join(batch),
            rettype="medline",
            retmode="text",
        )
        try:
            for rec in Medline.parse(fhandle):
                articles.append(medline_record_to_article(rec))
        finally:
            fhandle.close()

    flow_info(
        "完成 | PubMed 检索\n"
        f"  数据库命中总数（Count）：{total}\n"
        f"  本批检索式返回 PMID 数：{len(id_list)}\n"
        f"  已拉取 Medline 详情条数：{len(articles)}"
    )

    return SearchResult(
        query=term,
        total_count=total,
        retrieved_ids=id_list,
        articles=articles,
    )


# 综述模式：权威生物医学期刊（可随需扩展）
AUTHORITATIVE_JOURNALS_QUERY = (
    '("Nature"[Journal] OR "Science"[Journal] OR "Cell"[Journal] OR '
    '"New England Journal of Medicine"[Journal] OR "The Lancet"[Journal] OR '
    '"JAMA"[Journal] OR "BMJ"[Journal] OR "Nature Medicine"[Journal] OR '
    '"Nature Biotechnology"[Journal] OR "Cell Metabolism"[Journal] OR '
    '"Immunity"[Journal] OR "Nature Immunology"[Journal] OR '
    '"Circulation"[Journal] OR "Journal of Clinical Investigation"[Journal] OR '
    '"Gastroenterology"[Journal] OR "Annals of Internal Medicine"[Journal])'
)


def build_review_query(keyword: str, authoritative_only: bool) -> str:
    base = f"({keyword})"
    if authoritative_only:
        return f"{base} AND {AUTHORITATIVE_JOURNALS_QUERY}"
    return base

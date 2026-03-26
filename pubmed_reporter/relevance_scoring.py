"""检索完成后：按 PubMed 检索式对文献做相关性分级，供后续加权分析。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pubmed_reporter.config import Settings
from pubmed_reporter.flow_log import flow_info
from pubmed_reporter.llm_client import chat_completion
from pubmed_reporter.models import ArticleRelevance, PubMedArticle
from pubmed_reporter.prompts.relevance_grade import (
    SYSTEM_RELEVANCE_ZH,
    build_relevance_user_prompt,
)

_LEVEL_WEIGHT = {"高": 1.0, "中": 0.55, "低": 0.25}


def _normalize_level(s: str | None) -> str:
    if not s:
        return "中"
    t = str(s).strip()
    if t in _LEVEL_WEIGHT:
        return t
    if t in ("高", "中", "低"):
        return t
    # 常见变体
    if t.upper() in ("HIGH", "H"):
        return "高"
    if t.upper() in ("MEDIUM", "MID", "M"):
        return "中"
    if t.upper() in ("LOW", "L"):
        return "低"
    return "中"


def _extract_json_array(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _parse_relevance_raw(raw: str) -> list[dict]:
    blob = _extract_json_array(raw)
    data = json.loads(blob)
    if not isinstance(data, list):
        raise ValueError("相关性输出应为 JSON 数组")
    out: list[dict] = []
    for item in data:
        if isinstance(item, dict):
            out.append(item)
    return out


def align_relevances_to_articles(
    articles: list[PubMedArticle],
    parsed: list[dict],
) -> list[ArticleRelevance]:
    """按 PMID 对齐；缺失的条目默认「中」。"""
    by_pmid: dict[str, dict] = {}
    for row in parsed:
        pid = str(row.get("pmid", "")).strip()
        if pid:
            by_pmid[pid] = row

    result: list[ArticleRelevance] = []
    for a in articles:
        pmid = (a.pmid or "").strip() or "未知"
        row = by_pmid.get(pmid)
        level = _normalize_level(row.get("level") if row else None)
        rationale = ""
        if row and row.get("rationale"):
            rationale = str(row["rationale"]).strip()
        if not rationale:
            rationale = "（模型未给出理由，已按默认等级处理）" if not row else "（无）"
        w = _LEVEL_WEIGHT.get(level, 0.55)
        result.append(
            ArticleRelevance(
                pmid=pmid,
                level=level,
                weight=w,
                rationale=rationale,
            )
        )
    return result


def score_articles_relevance(
    settings: Settings,
    term: str,
    articles: list[PubMedArticle],
) -> list[ArticleRelevance]:
    if not articles:
        return []

    user = build_relevance_user_prompt(term, articles)
    raw = chat_completion(
        settings,
        SYSTEM_RELEVANCE_ZH,
        user,
        temperature=0.2,
        flow_stage="LLM：文献相关性分级（相对检索式）",
    )
    try:
        parsed = _parse_relevance_raw(raw)
    except (json.JSONDecodeError, ValueError) as e:
        flow_info(f"相关性 JSON 解析失败，将全部按「中」处理：{e}")
        return [
            ArticleRelevance(
                pmid=(a.pmid or "").strip() or "未知",
                level="中",
                weight=_LEVEL_WEIGHT["中"],
                rationale="（分级输出解析失败，默认中等相关）",
            )
            for a in articles
        ]

    aligned = align_relevances_to_articles(articles, parsed)
    if len(aligned) != len(articles):
        flow_info("相关性条目数与文献数不一致，已按 PMID 重对齐。")
    return aligned


def save_relevance_to_logs(
    term: str,
    *,
    mode: str,
    articles: list[PubMedArticle],
    relevances: list[ArticleRelevance],
    extra_meta: dict[str, str] | None = None,
) -> Path:
    """写入 logs/relevance_{mode}_{时间戳}.txt。"""
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = log_dir / f"relevance_{mode}_{stamp}.txt"

    iso_now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines: list[str] = [
        "# 文献相关性分级（相对本次 PubMed 检索式）",
        f"# generated_at_local: {iso_now}",
        f"# mode: {mode}",
        f"# pubmed_query: {term.replace(chr(10), ' ').strip()}",
        "#",
        "# 等级与权重映射（固定）：高=1.0，中=0.55，低=0.25",
        "#",
    ]
    if extra_meta:
        for k, v in extra_meta.items():
            lines.append(f"# {k}: {v}")
    lines.append("#")
    lines.append("序号\tPMID\t等级\t权重\t理由")
    n = len(articles)
    pairs = list(zip(articles, relevances))
    for i, (a, r) in enumerate(pairs, start=1):
        pmid = (a.pmid or "").strip() or "未知"
        rationale = (r.rationale or "").replace("\t", " ").replace("\n", " ")
        lines.append(f"{i}\t{pmid}\t{r.level}\t{r.weight:.2f}\t{rationale}")

    if n == 0:
        lines.append("（无文献）")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path

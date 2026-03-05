#!/usr/bin/env python3
"""citation_finder.py — 学术文献发现工具

搜索 Semantic Scholar + OpenAlex API，返回真实已发表的 SCI/SSCI 期刊论文。
零外部依赖（仅用 stdlib）。

用法:
    python citation_finder.py "query1" ["query2"] [--limit 10] [--bibtex]
    python citation_finder.py --cite-network <DOI> [--depth 1]
    python citation_finder.py --theory-map "concept" [--limit 20]

输出: JSON 格式的论文列表（stdout），进度信息输出到 stderr。
"""

import urllib.request
import urllib.parse
import json
import sys
import time
import re
import os
import hashlib
from pathlib import Path
from typing import Optional

# ── 缓存 ─────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / ".citation_cache"
CACHE_TTL = 86400 * 7  # 7天过期

# ── 期刊质量数据库 ───────────────────────────────────────────────

_JOURNAL_DB = None  # lazy load


def _load_journal_db() -> dict:
    """加载期刊质量数据库（lazy，首次调用时加载）。"""
    global _JOURNAL_DB
    if _JOURNAL_DB is not None:
        return _JOURNAL_DB

    db_path = Path(__file__).parent / "journal_quality.json"
    if not db_path.exists():
        print("  [WARN] journal_quality.json 不存在，跳过质量过滤",
              file=sys.stderr)
        _JOURNAL_DB = {}
        return _JOURNAL_DB

    with open(db_path) as f:
        raw = json.load(f)

    # 构建统一的 venue→tier 映射（小写归一化）
    tiers = {}
    for j in raw.get("utd24", []):
        tiers[j.lower()] = "UTD24"
    for j in raw.get("ft50", []):
        tiers.setdefault(j.lower(), "FT50")
    for j in raw.get("abs4", []):
        tiers.setdefault(j.lower(), "ABS4")
    for j in raw.get("abs3", []):
        tiers.setdefault(j.lower(), "ABS3")
    for j in raw.get("jcr_q1_extra", []):
        tiers.setdefault(j.lower(), "JCR-Q1")

    _JOURNAL_DB = tiers
    print(f"  [质量库] {len(tiers)} 本期刊已加载", file=sys.stderr)
    return _JOURNAL_DB


def _match_venue(venue: str) -> Optional[str]:
    """模糊匹配期刊名到质量层级。

    返回 tier 字符串（如 "UTD24", "ABS3"）或 None。
    策略：精确匹配 → 包含匹配（长度保护）→ 归一化匹配。
    """
    if not venue:
        return None
    db = _load_journal_db()
    if not db:
        return None

    v = venue.lower().strip()

    # 1. 精确匹配
    if v in db:
        return db[v]

    # 2. 包含匹配（要求较短串长度 >= 15 字符，且覆盖率 >= 70%）
    for journal, tier in db.items():
        shorter = min(len(journal), len(v))
        longer = max(len(journal), len(v))
        if shorter >= 15 and shorter / longer >= 0.6:
            if journal in v or v in journal:
                return tier

    # 3. 归一化匹配（去冠词、连接词）
    def _clean(s):
        return (s.replace("the ", "").replace(" of ", " ")
                .replace(" and ", " ").replace(" & ", " ")
                .replace(" for ", " ").strip())

    v_clean = _clean(v)
    for journal, tier in db.items():
        j_clean = _clean(journal)
        if j_clean == v_clean:
            return tier
        shorter = min(len(j_clean), len(v_clean))
        longer = max(len(j_clean), len(v_clean))
        if shorter >= 15 and shorter / longer >= 0.6:
            if j_clean in v_clean or v_clean in j_clean:
                return tier

    return None


def filter_by_quality(papers: list[dict]) -> list[dict]:
    """过滤并标注期刊质量层级。

    只保留 UTD24/FT50/ABS3+/JCR-Q1 期刊的论文。
    每篇论文增加 'tier' 字段。
    """
    filtered = []
    for p in papers:
        tier = _match_venue(p.get("venue", ""))
        if tier:
            p["tier"] = tier
            filtered.append(p)
    return filtered


def _cache_key(prefix: str, query: str) -> Path:
    h = hashlib.md5(query.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{prefix}_{h}.json"


def _cache_get(prefix: str, query: str) -> Optional[list]:
    path = _cache_key(prefix, query)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL:
        path.unlink(missing_ok=True)
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _cache_set(prefix: str, query: str, data: list):
    CACHE_DIR.mkdir(exist_ok=True)
    _cache_key(prefix, query).write_text(
        json.dumps(data, ensure_ascii=False))


# ── Semantic Scholar API ──────────────────────────────────────────

def search_semantic_scholar(query: str, limit: int = 10,
                            year_from: int = None) -> list[dict]:
    """搜索 Semantic Scholar（语义搜索，质量高）。"""
    cache_q = f"{query}|y{year_from}" if year_from else query
    cached = _cache_get("s2", cache_q)
    if cached is not None:
        print(f"  [缓存] S2: {query}", file=sys.stderr)
        return cached

    base = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "title,authors,year,venue,abstract,citationCount,externalIds,url"
    p = {"query": query, "limit": limit, "fields": fields}
    if year_from:
        p["year"] = f"{year_from}-"
    params = urllib.parse.urlencode(p)
    url = f"{base}?{params}"

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "citation-finder/1.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("data") or []
            _cache_set("s2", cache_q, results)
            return results
    except Exception as e:
        print(f"  [WARN] Semantic Scholar: {e}", file=sys.stderr)
        return []


# ── OpenAlex API ──────────────────────────────────────────────────

def _reconstruct_abstract(inverted_index: dict) -> str:
    """从 OpenAlex 倒排索引重建摘要文本。"""
    if not inverted_index:
        return ""
    words = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words.keys()))


def search_openalex(query: str, limit: int = 10,
                    year_from: int = None) -> list[dict]:
    """搜索 OpenAlex（覆盖面广，可过滤期刊论文）。"""
    cache_q = f"{query}|y{year_from}" if year_from else query
    cached = _cache_get("oa", cache_q)
    if cached is not None:
        print(f"  [缓存] OA: {query}", file=sys.stderr)
        return cached

    base = "https://api.openalex.org/works"
    filt = "type:article"
    if year_from:
        filt += f",from_publication_date:{year_from}-01-01"
    params = urllib.parse.urlencode({
        "search": query,
        "per_page": limit,
        "filter": filt,
        "sort": "cited_by_count:desc",
    })
    url = f"{base}?{params}"

    req = urllib.request.Request(url)
    req.add_header("User-Agent",
                    "citation-finder/1.0 (mailto:academic-tool@example.com)")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results") or []
            _cache_set("oa", cache_q, results)
            return results
    except Exception as e:
        print(f"  [WARN] OpenAlex: {e}", file=sys.stderr)
        return []


# ── 结果归一化与去重 ─────────────────────────────────────────────

def _normalize(ss_results: list, oa_results: list) -> list[dict]:
    """合并两个来源的结果，按 DOI 去重，按引用量排序。"""
    papers = {}

    # Semantic Scholar
    for p in ss_results:
        doi = (p.get("externalIds") or {}).get("DOI")
        key = (doi or "").lower() or p.get("title", "").lower().strip()
        if not key:
            continue
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        papers[key] = {
            "title": p.get("title", ""),
            "authors": authors,
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "doi": doi,
            "citations": p.get("citationCount", 0) or 0,
            "abstract": p.get("abstract", "") or "",
            "url": f"https://doi.org/{doi}" if doi else p.get("url", ""),
            "source": "S2",
        }

    # OpenAlex
    for p in oa_results:
        doi_raw = p.get("doi", "") or ""
        doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None
        key = (doi or "").lower() or (p.get("title") or "").lower().strip()
        if not key:
            continue

        if key in papers:
            cites = p.get("cited_by_count", 0) or 0
            if cites > papers[key]["citations"]:
                papers[key]["citations"] = cites
            papers[key]["source"] += "+OA"
            continue

        authors = [
            a.get("author", {}).get("display_name", "")
            for a in (p.get("authorships") or [])
            if a.get("author", {}).get("display_name")
        ]
        loc = p.get("primary_location") or {}
        venue = (loc.get("source") or {}).get("display_name", "")
        abstract = _reconstruct_abstract(
            p.get("abstract_inverted_index"))

        papers[key] = {
            "title": p.get("title", ""),
            "authors": authors,
            "year": p.get("publication_year"),
            "venue": venue,
            "doi": doi,
            "citations": p.get("cited_by_count", 0) or 0,
            "abstract": abstract,
            "url": f"https://doi.org/{doi}" if doi else "",
            "source": "OA",
        }

    return sorted(papers.values(),
                  key=lambda x: x["citations"], reverse=True)


# ── 引用网络探索 ─────────────────────────────────────────────────

def get_paper_by_doi(doi: str) -> Optional[dict]:
    """通过 DOI 获取 Semantic Scholar 论文详情。"""
    url = (f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
           f"?fields=title,authors,year,venue,abstract,citationCount,"
           f"externalIds,url,citations.title,citations.authors,"
           f"citations.year,citations.venue,citations.citationCount,"
           f"citations.externalIds,references.title,references.authors,"
           f"references.year,references.venue,references.citationCount,"
           f"references.externalIds")
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "citation-finder/1.0")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] S2 paper lookup: {e}", file=sys.stderr)
        return None


def explore_citation_network(doi: str, direction: str = "both",
                             limit: int = 10) -> list[dict]:
    """从一篇种子论文出发，探索引用网络。

    Args:
        doi: 种子论文 DOI
        direction: "citing"(谁引了它) / "cited"(它引了谁) / "both"
        limit: 每个方向返回的论文数
    """
    paper = get_paper_by_doi(doi)
    if not paper:
        return []

    results = []
    if direction in ("citing", "both"):
        for c in (paper.get("citations") or [])[:limit]:
            cdoi = (c.get("externalIds") or {}).get("DOI")
            results.append({
                "title": c.get("title", ""),
                "authors": [a.get("name", "")
                            for a in (c.get("authors") or [])],
                "year": c.get("year"),
                "venue": c.get("venue", ""),
                "doi": cdoi,
                "citations": c.get("citationCount", 0) or 0,
                "abstract": "",
                "url": f"https://doi.org/{cdoi}" if cdoi else "",
                "source": "S2-citing",
            })

    if direction in ("cited", "both"):
        for r in (paper.get("references") or [])[:limit]:
            rdoi = (r.get("externalIds") or {}).get("DOI")
            results.append({
                "title": r.get("title", ""),
                "authors": [a.get("name", "")
                            for a in (r.get("authors") or [])],
                "year": r.get("year"),
                "venue": r.get("venue", ""),
                "doi": rdoi,
                "citations": r.get("citationCount", 0) or 0,
                "abstract": "",
                "url": f"https://doi.org/{rdoi}" if rdoi else "",
                "source": "S2-cited",
            })

    return sorted(results, key=lambda x: x["citations"], reverse=True)


# ── 理论图谱模式 ─────────────────────────────────────────────────

def build_theory_map(concept: str, limit: int = 20) -> dict:
    """为一个理论概念构建经典文献索引。

    返回按年代排序的文献列表 + 高被引经典论文标记。
    """
    print(f"[理论图谱] {concept}", file=sys.stderr)

    # 搜索该概念的核心文献
    ss = search_semantic_scholar(concept, limit)
    time.sleep(1.1)
    oa = search_openalex(concept, limit)
    all_papers = _normalize(ss, oa)

    # 识别经典论文（被引 > 500 或 年份 < 2010 且被引 > 100）
    classics = []
    recent = []
    for p in all_papers:
        cites = p.get("citations", 0)
        year = p.get("year") or 2025
        if cites >= 500 or (year < 2010 and cites >= 100):
            p["tier"] = "classic"
            classics.append(p)
        else:
            p["tier"] = "recent"
            recent.append(p)

    return {
        "concept": concept,
        "total": len(all_papers),
        "classics": sorted(classics, key=lambda x: x.get("year", 0)),
        "recent": sorted(recent,
                         key=lambda x: x["citations"], reverse=True)[:10],
    }


# ── 金句提取 ─────────────────────────────────────────────────────

def extract_key_quotes(papers: list[dict]) -> list[dict]:
    """从论文摘要中提取可引用的关键句。

    策略：提取包含因果/发现/结论关键词的句子。
    """
    signal_words = [
        "we find", "results show", "evidence suggests",
        "we demonstrate", "our findings", "this study shows",
        "significantly", "contributes to", "we provide evidence",
        "the results indicate", "our analysis reveals",
        "we document", "consistent with", "in contrast",
    ]

    enriched = []
    for p in papers:
        abstract = p.get("abstract", "")
        if not abstract:
            continue
        sentences = re.split(r'(?<=[.!?])\s+', abstract)
        quotes = []
        for s in sentences:
            s_lower = s.lower()
            if any(w in s_lower for w in signal_words):
                quotes.append(s.strip())
        if quotes:
            enriched.append({
                "doi": p.get("doi"),
                "title": p.get("title"),
                "authors": p.get("authors", [])[:3],
                "year": p.get("year"),
                "key_quotes": quotes[:3],  # 最多3句
            })
    return enriched


# ── BibTeX 生成 ──────────────────────────────────────────────────

def _make_citekey(paper: dict) -> str:
    """生成 BibTeX cite key: FirstAuthorLastName + Year。"""
    authors = paper.get("authors") or []
    if authors:
        last = authors[0].split()[-1] if authors[0] else "Unknown"
        last = re.sub(r"[^a-zA-Z]", "", last)
    else:
        last = "Unknown"
    year = paper.get("year") or "XXXX"
    return f"{last}{year}"


def to_bibtex(papers: list[dict]) -> str:
    """将论文列表转为 BibTeX 字符串。"""
    entries = []
    seen_keys = set()
    for p in papers:
        key = _make_citekey(p)
        if key in seen_keys:
            key += "b"
        seen_keys.add(key)

        authors_str = " and ".join(p.get("authors") or ["Unknown"])
        doi_field = f'  doi = {{{p["doi"]}}},' if p.get("doi") else ""
        entry = (
            f"@article{{{key},\n"
            f'  title = {{{p.get("title", "")}}},\n'
            f"  author = {{{authors_str}}},\n"
            f'  journal = {{{p.get("venue", "")}}},\n'
            f'  year = {{{p.get("year", "")}}},\n'
            f"{doi_field}\n"
            f"}}"
        )
        entries.append(entry)
    return "\n\n".join(entries)


# ── CLI 入口 ─────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # 模式标志
    bibtex_mode = "--bibtex" in args
    if bibtex_mode:
        args.remove("--bibtex")
    quotes_mode = "--quotes" in args
    if quotes_mode:
        args.remove("--quotes")
    # 质量过滤：默认开启，--no-quality 关闭
    quality_mode = "--no-quality" not in args
    if not quality_mode:
        args.remove("--no-quality")

    limit = 10
    if "--limit" in args:
        idx = args.index("--limit")
        limit = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    year_from = None
    if "--year" in args:
        idx = args.index("--year")
        year_from = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    # 引用网络模式
    if "--cite-network" in args:
        idx = args.index("--cite-network")
        doi = args[idx + 1]
        direction = "both"
        if "--direction" in args:
            di = args.index("--direction")
            direction = args[di + 1]
        results = explore_citation_network(doi, direction, limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # 理论图谱模式
    if "--theory-map" in args:
        idx = args.index("--theory-map")
        concept = args[idx + 1]
        tmap = build_theory_map(concept, limit)
        print(json.dumps(tmap, ensure_ascii=False, indent=2))
        return

    queries = [a for a in args if not a.startswith("-")]
    if not queries:
        print("用法:", file=sys.stderr)
        print("  搜索:   python citation_finder.py <query> [query2] "
              "[--limit N] [--bibtex] [--quotes] [--no-quality]",
              file=sys.stderr)
        print("  引用网: python citation_finder.py --cite-network "
              "<DOI> [--direction citing|cited|both]", file=sys.stderr)
        print("  图谱:   python citation_finder.py --theory-map "
              '"concept" [--limit 20]', file=sys.stderr)
        print("  质量过滤默认开启（仅保留 UTD24/FT50/ABS3+/JCR-Q1），"
              "--no-quality 关闭", file=sys.stderr)
        sys.exit(1)

    all_ss, all_oa = [], []
    for q in queries:
        print(f"[搜索] {q}", file=sys.stderr)
        all_ss.extend(search_semantic_scholar(q, limit, year_from))
        time.sleep(1.1)
        all_oa.extend(search_openalex(q, limit, year_from))
        time.sleep(0.2)

    results = _normalize(all_ss, all_oa)[:40]  # 取更多以便过滤后仍有足够结果
    print(f"[结果] {len(results)} 篇去重后论文", file=sys.stderr)

    # 质量过滤
    if quality_mode:
        results = filter_by_quality(results)
        print(f"[质量过滤] {len(results)} 篇通过 "
              "(UTD24/FT50/ABS3+/JCR-Q1)", file=sys.stderr)

    if quotes_mode:
        quotes = extract_key_quotes(results)
        print(json.dumps(quotes, ensure_ascii=False, indent=2))
    elif bibtex_mode:
        print(to_bibtex(results))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

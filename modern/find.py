"""Fuzzy hymn-title search over the modern/all_hymns.pdf manifest.

Usage:
    python3.10 -m modern.find <query>

- Loads modern/all_hymns_manifest.json (preferred, has page numbers once the
  build agent emits them). Falls back to app/lead_sheets.json (no page info)
  with a warning if the manifest is missing.
- If <query> is all digits, it is treated as a hymn number and the matching
  record is printed directly (no fuzzy matching).
- Otherwise difflib.get_close_matches is used with cutoff=0.5 on a cleaned,
  case-insensitive title; top 5 matches are printed in a fixed-width format.

Standard library only.
"""

import argparse
import difflib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(REPO_ROOT, "modern", "all_hymns_manifest.json")
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
PAGE_INDEX_PATH = os.path.join(REPO_ROOT, "modern", "all_hymns_page_index.md")

FUZZY_CUTOFF = 0.5
TOP_N = 5


def clean_title(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy matching."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _page_of(rec: Dict[str, Any]) -> Optional[int]:
    """Extract a page number from a manifest record, if present."""
    for key in ("page_start", "pages", "page"):
        if key not in rec:
            continue
        val = rec[key]
        if isinstance(val, int):
            return val
        if isinstance(val, list) and val:
            try:
                return int(val[0])
            except (TypeError, ValueError):
                return None
        if isinstance(val, str):
            m = re.search(r"\d+", val)
            if m:
                return int(m.group(0))
    return None


def load_records() -> Tuple[List[Dict[str, Any]], bool]:
    """Return (records, have_pages). Falls back to lead_sheets.json if needed."""
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="ascii", errors="replace") as f:
            data = json.load(f)
        have_pages = any(_page_of(r) is not None for r in data)
        if not have_pages:
            sys.stderr.write(
                "warning: manifest has no page numbers yet "
                "(build not yet complete)\n"
            )
        return data, have_pages

    sys.stderr.write(
        "warning: modern/all_hymns_manifest.json missing "
        "(build not yet complete); falling back to app/lead_sheets.json\n"
    )
    if not os.path.exists(LEAD_SHEETS_PATH):
        sys.stderr.write("error: neither manifest nor lead_sheets.json found\n")
        return [], False
    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8", errors="replace") as f:
        raw = json.load(f)
    records: List[Dict[str, Any]] = []
    for r in raw:
        records.append(
            {
                "n": str(r.get("n", "")),
                "title": r.get("t", ""),
                "key": r.get("key", ""),
                "tempo": "",
            }
        )
    return records, False


def format_row(rec: Dict[str, Any], have_pages: bool) -> str:
    n = str(rec.get("n", ""))
    title = str(rec.get("title", ""))
    key = str(rec.get("key", ""))
    tempo = str(rec.get("tempo", ""))
    page = _page_of(rec)
    page_str = "(page ?)" if not have_pages else (
        f"(page {page})" if page is not None else "(page -)"
    )
    # ASCII-only, fixed-ish columns
    return f"n={n:<5} {title:<40} key={key:<3} tempo={tempo:<10} {page_str}"


def find_by_number(records: List[Dict[str, Any]], n: str) -> Optional[Dict[str, Any]]:
    for r in records:
        if str(r.get("n", "")) == n:
            return r
    return None


def fuzzy_search(
    records: List[Dict[str, Any]], query: str, cutoff: float = FUZZY_CUTOFF,
    top_n: int = TOP_N,
) -> List[Dict[str, Any]]:
    cleaned = clean_title(query)
    titles_cleaned = [clean_title(r.get("title", "")) for r in records]
    # Pass-1: substring hits (get_close_matches misses these when cleaned query
    # is much shorter than the candidate, e.g. "silent" vs "silent night").
    sub_hits = [r for r, t in zip(records, titles_cleaned) if cleaned and cleaned in t]
    matches = difflib.get_close_matches(cleaned, titles_cleaned, n=top_n * 3, cutoff=cutoff)
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for r in sub_hits:
        key = str(r.get("n", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= top_n:
            return out
    for m in matches:
        for r, t in zip(records, titles_cleaned):
            if t == m and str(r.get("n", "")) not in seen:
                seen.add(str(r.get("n", "")))
                out.append(r)
                break
        if len(out) >= top_n:
            break
    return out


def write_page_index(records: List[Dict[str, Any]], path: str) -> int:
    """Write sorted markdown table of successfully rendered hymns. Returns row count."""
    rows = []
    for r in records:
        page = _page_of(r)
        if page is None:
            continue
        rows.append((page, str(r.get("n", "")), str(r.get("title", "")),
                     str(r.get("key", "")), str(r.get("tempo", ""))))
    rows.sort(key=lambda x: (x[0], x[1]))
    lines = [
        "| page | n | title | key | tempo |",
        "| ---: | ---: | --- | --- | --- |",
    ]
    for page, n, title, key, tempo in rows:
        # Escape pipes in title for markdown safety.
        safe_title = title.replace("|", "\\|")
        lines.append(f"| {page} | {n} | {safe_title} | {key} | {tempo} |")
    with open(path, "w", encoding="ascii", errors="replace") as f:
        f.write("# all_hymns.pdf page index\n\n")
        if rows:
            f.write("\n".join(lines) + "\n")
        else:
            f.write(
                "_No page numbers in manifest yet (build not complete)._\n"
            )
    return len(rows)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="modern.find",
        description="Fuzzy hymn-title search against modern/all_hymns.pdf manifest.",
    )
    p.add_argument("query", help="Hymn title fragment, or hymn number (all digits).")
    p.add_argument(
        "--write-index", action="store_true",
        help="(Re)write modern/all_hymns_page_index.md and exit.",
    )
    args = p.parse_args(argv)

    records, have_pages = load_records()
    if not records:
        return 2

    if args.write_index:
        count = write_page_index(records, PAGE_INDEX_PATH)
        sys.stdout.write(
            f"wrote {PAGE_INDEX_PATH} ({count} rows)\n"
        )
        return 0

    query = args.query.strip()

    # Always refresh page index opportunistically (cheap; keeps doc in sync).
    try:
        write_page_index(records, PAGE_INDEX_PATH)
    except OSError:
        pass

    if query.isdigit():
        rec = find_by_number(records, query)
        if rec is None:
            sys.stdout.write(f"no hymn with n={query}\n")
            return 1
        sys.stdout.write(format_row(rec, have_pages) + "\n")
        return 0

    hits = fuzzy_search(records, query)
    if not hits:
        sys.stdout.write("no matches\n")
        return 1
    for r in hits:
        sys.stdout.write(format_row(r, have_pages) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

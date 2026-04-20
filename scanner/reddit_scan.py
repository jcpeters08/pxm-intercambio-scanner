#!/usr/bin/env python3
"""
Reddit scanner for Intercambio PXM.

Reads queries.json, hits Reddit's public JSON search API, deduplicates against
existing data/hits.json, and prints a JSON summary of newly found posts on stdout
so a Claude Code Routine can decide which ones to draft responses for.

Usage:
    python scanner/reddit_scan.py
    python scanner/reddit_scan.py --dry-run   # don't modify hits.json
    python scanner/reddit_scan.py --debug     # verbose logging

No API key required — uses the public .json endpoint. A descriptive User-Agent
is sent to avoid being rate-limited.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "scanner" / "queries.json"
DATA_PATH = ROOT / "data" / "hits.json"
DOCS_DATA_PATH = ROOT / "docs" / "hits.json"

USER_AGENT = "pxm-intercambio-scanner/1.0 (contact: jcpeters08@gmail.com)"
REDDIT_BASE = "https://www.reddit.com"


# --------------------------------------------------------------------------- #
# IO helpers
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    with CONFIG_PATH.open() as f:
        return json.load(f)


def load_hits() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open() as f:
        return json.load(f)


def save_hits(hits: list[dict]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w") as f:
        json.dump(hits, f, indent=2)
    # Keep the GitHub Pages copy in sync
    DOCS_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DOCS_DATA_PATH.open("w") as f:
        json.dump(hits, f, indent=2)


# --------------------------------------------------------------------------- #
# Reddit API
# --------------------------------------------------------------------------- #

def reddit_get(path: str, params: dict | None = None, debug: bool = False) -> dict:
    """GET a Reddit .json endpoint and return the parsed body."""
    params = params or {}
    qs = urllib.parse.urlencode(params)
    url = f"{REDDIT_BASE}{path}?{qs}" if qs else f"{REDDIT_BASE}{path}"
    if debug:
        print(f"[debug] GET {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def search_subreddit(sub: str, query: str, debug: bool = False) -> list[dict]:
    body = reddit_get(
        f"/r/{sub}/search.json",
        {"q": query, "restrict_sr": "1", "sort": "new", "limit": 25, "t": "year"},
        debug=debug,
    )
    return [c["data"] for c in body.get("data", {}).get("children", [])]


def search_site_wide(query: str, debug: bool = False) -> list[dict]:
    body = reddit_get(
        "/search.json",
        {"q": query, "sort": "new", "limit": 25, "t": "year"},
        debug=debug,
    )
    return [c["data"] for c in body.get("data", {}).get("children", [])]


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #

def post_matches(post: dict, config: dict) -> bool:
    """Double-check a post is actually relevant before surfacing it."""
    text_blob = " ".join([
        str(post.get("title") or ""),
        str(post.get("selftext") or ""),
        str(post.get("subreddit") or ""),
    ]).lower()

    has_location = any(loc in text_blob for loc in config["location_filter"])
    has_keyword = any(kw in text_blob for kw in config["keyword_filter"])
    # Must hit location AND at least one keyword
    return has_location and has_keyword


def fresh_enough(post: dict, max_age_days: int) -> bool:
    created = post.get("created_utc")
    if not created:
        return False
    age_days = (time.time() - created) / 86400
    return age_days <= max_age_days


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #

def to_hit(post: dict) -> dict:
    created_utc = post.get("created_utc") or 0
    created_iso = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
    return {
        "id": f"reddit:{post.get('id')}",
        "platform": "reddit",
        "subreddit": post.get("subreddit"),
        "title": post.get("title"),
        "summary": (post.get("selftext") or "")[:500],
        "author": post.get("author"),
        "url": f"https://www.reddit.com{post.get('permalink', '')}",
        "created_at": created_iso,
        "found_at": datetime.now(tz=timezone.utc).isoformat(),
        "status": "new",  # states: new, drafted, replied, skipped
        "draft_id": None,
        "notes": "",
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    config = load_config()
    existing = load_hits()
    existing_ids = {h["id"] for h in existing}

    candidates: dict[str, dict] = {}
    errors: list[str] = []

    # Per-subreddit searches
    for sub in config["subreddits"]:
        for query in config["queries"]:
            try:
                for post in search_subreddit(sub, query, debug=args.debug):
                    if not fresh_enough(post, config["max_age_days"]):
                        continue
                    if not post_matches(post, config):
                        continue
                    candidates[post["id"]] = post
                time.sleep(1.1)  # be polite
            except Exception as e:
                errors.append(f"r/{sub} '{query}': {e}")

    # Site-wide searches (catch subs we didn't think of)
    for query in config["site_wide_queries"]:
        try:
            for post in search_site_wide(query, debug=args.debug):
                if not fresh_enough(post, config["max_age_days"]):
                    continue
                if not post_matches(post, config):
                    continue
                candidates[post["id"]] = post
            time.sleep(1.1)
        except Exception as e:
            errors.append(f"site '{query}': {e}")

    new_hits = [to_hit(p) for p in candidates.values() if f"reddit:{p['id']}" not in existing_ids]
    merged = existing + new_hits
    # Newest first
    merged.sort(key=lambda h: h.get("created_at", ""), reverse=True)

    if not args.dry_run:
        save_hits(merged)

    summary = {
        "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
        "candidates_considered": len(candidates),
        "new_hits": len(new_hits),
        "total_hits": len(merged),
        "errors": errors,
        "new": [{"id": h["id"], "title": h["title"], "url": h["url"]} for h in new_hits],
    }
    print(json.dumps(summary, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())

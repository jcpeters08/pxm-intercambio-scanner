#!/usr/bin/env python3
"""
Reddit scanner for Intercambio PXM.

Reads queries.json, hits Reddit's search API, deduplicates against existing
data/hits.json, and prints a JSON summary of newly found posts on stdout.

Two modes:

  1. OAuth (recommended, required in cloud environments).
     Set these environment variables:
         REDDIT_CLIENT_ID       (from https://www.reddit.com/prefs/apps)
         REDDIT_CLIENT_SECRET
         REDDIT_USERNAME        (Reddit account for the app; ideally a
                                 dedicated no-2FA account)
         REDDIT_PASSWORD

     In OAuth mode the scanner calls oauth.reddit.com with a Bearer token.
     Reddit rate limit: 100 requests/minute.

  2. Public JSON (fallback, only works from non-datacenter IPs).
     No env vars needed. Calls www.reddit.com/*.json directly.
     Does NOT work from Anthropic's cloud Routine runtime — Reddit blocks
     datacenter IPs with HTTP 403.

Usage:
    python scanner/reddit_scan.py
    python scanner/reddit_scan.py --dry-run   # don't modify hits.json
    python scanner/reddit_scan.py --debug     # verbose logging
"""

from __future__ import annotations

import argparse
import base64
import json
import os
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

USER_AGENT = "pxm-intercambio-scanner/1.1 (by /u/{user}; contact: jcpeters08@gmail.com)"
REDDIT_AUTH_HOST = "https://www.reddit.com"
REDDIT_OAUTH_HOST = "https://oauth.reddit.com"
REDDIT_PUBLIC_HOST = "https://www.reddit.com"


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
# Auth
# --------------------------------------------------------------------------- #

class Client:
    """Dispatches Reddit requests via OAuth or public JSON depending on env."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.mode = "public"
        self.token: str | None = None
        self.user_agent = USER_AGENT.format(user="unknown")
        self._authenticate()

    def _authenticate(self) -> None:
        cid = os.environ.get("REDDIT_CLIENT_ID")
        csec = os.environ.get("REDDIT_CLIENT_SECRET")
        username = os.environ.get("REDDIT_USERNAME")
        password = os.environ.get("REDDIT_PASSWORD")

        if not all([cid, csec, username, password]):
            if self.debug:
                print("[auth] Missing Reddit OAuth env vars → public JSON mode", file=sys.stderr)
            return

        self.user_agent = USER_AGENT.format(user=username)
        basic = base64.b64encode(f"{cid}:{csec}".encode()).decode()
        body = urllib.parse.urlencode({
            "grant_type": "password",
            "username": username,
            "password": password,
        }).encode()
        req = urllib.request.Request(
            f"{REDDIT_AUTH_HOST}/api/v1/access_token",
            data=body,
            headers={
                "Authorization": f"Basic {basic}",
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.load(resp)
            token = payload.get("access_token")
            if not token:
                raise RuntimeError(f"No access_token in response: {payload}")
            self.token = token
            self.mode = "oauth"
            if self.debug:
                print(f"[auth] OAuth token acquired for u/{username}", file=sys.stderr)
        except Exception as e:
            print(f"[auth] OAuth failed ({e}) → falling back to public JSON", file=sys.stderr)

    def _headers(self) -> dict:
        h = {"User-Agent": self.user_agent}
        if self.mode == "oauth":
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get(self, path: str, params: dict | None = None) -> dict:
        params = params or {}
        host = REDDIT_OAUTH_HOST if self.mode == "oauth" else REDDIT_PUBLIC_HOST
        # OAuth host omits the `.json` suffix; public host requires it.
        if self.mode == "public" and not path.endswith(".json"):
            # Paths we call: /r/x/search, /search. Append .json.
            path_with_suffix = path + ".json"
        else:
            path_with_suffix = path
        qs = urllib.parse.urlencode(params)
        url = f"{host}{path_with_suffix}" + (f"?{qs}" if qs else "")
        if self.debug:
            print(f"[debug] [{self.mode}] GET {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)


# --------------------------------------------------------------------------- #
# Reddit calls
# --------------------------------------------------------------------------- #

def search_subreddit(client: Client, sub: str, query: str) -> list[dict]:
    body = client.get(
        f"/r/{sub}/search",
        {"q": query, "restrict_sr": "1", "sort": "new", "limit": "25", "t": "year"},
    )
    return [c["data"] for c in body.get("data", {}).get("children", [])]


def search_site_wide(client: Client, query: str) -> list[dict]:
    body = client.get(
        "/search",
        {"q": query, "sort": "new", "limit": "25", "t": "year"},
    )
    return [c["data"] for c in body.get("data", {}).get("children", [])]


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #

def post_matches(post: dict, config: dict) -> bool:
    text_blob = " ".join([
        str(post.get("title") or ""),
        str(post.get("selftext") or ""),
        str(post.get("subreddit") or ""),
    ]).lower()
    has_location = any(loc in text_blob for loc in config["location_filter"])
    has_keyword = any(kw in text_blob for kw in config["keyword_filter"])
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
        "status": "new",
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

    client = Client(debug=args.debug)
    if args.debug:
        print(f"[main] Running in {client.mode} mode", file=sys.stderr)

    # OAuth allows 100 req/min; public allows 60. We sleep 1.1s either way.
    request_delay = 0.65 if client.mode == "oauth" else 1.1

    candidates: dict[str, dict] = {}
    errors: list[str] = []

    for sub in config["subreddits"]:
        for query in config["queries"]:
            try:
                for post in search_subreddit(client, sub, query):
                    if not fresh_enough(post, config["max_age_days"]):
                        continue
                    if not post_matches(post, config):
                        continue
                    candidates[post["id"]] = post
                time.sleep(request_delay)
            except Exception as e:
                errors.append(f"r/{sub} '{query}': {e}")

    for query in config["site_wide_queries"]:
        try:
            for post in search_site_wide(client, query):
                if not fresh_enough(post, config["max_age_days"]):
                    continue
                if not post_matches(post, config):
                    continue
                candidates[post["id"]] = post
            time.sleep(request_delay)
        except Exception as e:
            errors.append(f"site '{query}': {e}")

    new_hits = [to_hit(p) for p in candidates.values() if f"reddit:{p['id']}" not in existing_ids]
    merged = existing + new_hits
    merged.sort(key=lambda h: h.get("created_at", ""), reverse=True)

    if not args.dry_run:
        save_hits(merged)

    summary = {
        "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
        "auth_mode": client.mode,
        "candidates_considered": len(candidates),
        "new_hits": len(new_hits),
        "total_hits": len(merged),
        "errors": errors,
        "new": [{"id": h["id"], "title": h["title"], "url": h["url"]} for h in new_hits],
    }
    print(json.dumps(summary, indent=2))
    # Exit 2 only if we had errors AND found no new hits (hard-fail). If we got
    # some hits despite errors, exit 0 so the Routine can proceed.
    if errors and not new_hits:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

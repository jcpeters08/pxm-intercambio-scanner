# CLAUDE.md — Intercambio PXM Social Scanner

If you're a new Claude session opening this repo, read this first.

## What this is

Weekly automation that finds people asking "where can I practice Spanish in Puerto Escondido?" across Reddit + Gmail-routed Google Alerts, drafts a reply pointing them at Jacob's Saturday class, and stashes each draft in Gmail for review. Dashboard published to GitHub Pages.

Live dashboard: https://jcpeters08.github.io/pxm-intercambio-scanner/

## Architecture

```
┌──────────────────────┐   weekly   ┌─────────────────────┐
│  Claude Code Routine │───────────▶│  reddit_scan.py     │── OAuth ─▶ oauth.reddit.com
│  (runs in cloud)     │            └─────────┬───────────┘
│                      │                      │
│                      │  Gmail MCP           ▼
│                      │───────▶ Google Alerts threads ──┐
│                      │                                 │
│                      │  Gmail MCP          ┌───────────▼──────┐
│                      │───────▶ create_draft │  data/hits.json  │
└──────────┬───────────┘                     └────────┬─────────┘
           │                                          │ copied to
           ▼                                          ▼
┌──────────────────────┐                   ┌──────────────────────┐
│  Gmail drafts        │                   │  docs/index.html     │
│  (one per hit)       │                   │  (GitHub Pages)      │
└──────────────────────┘                   └──────────────────────┘
```

## Critical conventions — DON'T BREAK

1. **OAuth is required in the cloud.** Reddit blocks unauthenticated requests from datacenter IPs (Anthropic's Routine runtime). `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD` must be set on the routine. Public mode works locally only.
2. **No 2FA on the Reddit account.** Password grant flow doesn't support OTP reliably. Use a dedicated no-2FA account.
3. **Drafts only, never sends.** Routine creates Gmail drafts addressed to Jonathan; he reviews + sends manually. Safety feature.
4. **Don't scrape FB / IG / TikTok.** Those are manual-only via `manual-intake/WEEKLY_CHECKLIST.md`.
5. **`data/hits.json` is canonical.** `docs/hits.json` mirrors it for the GitHub Pages dashboard.

## Glossary

- **PXM** — Puerto Escondido (Oaxaca, MX)
- **Intercambio** — language exchange (Spanish/English meetups)
- **Jacob's Saturday class** — the language exchange class being promoted
- **Google Alerts → Gmail label `Google-Alerts`** — captures blog posts, Tripadvisor, Medium, indexed web mentions
- **Claude Code Routine** — cloud-scheduled agent at https://claude.ai/code/routines

## Schema highlights

- `data/hits.json` — `{platform, url, title, snippet, status, date}` per hit
- `scanner/queries.json` — subreddits + keyword sets
- `templates/reply_en.md` / `reply_es.md` — reply scaffolding
- `ROUTINE_PROMPT.md` — exact prompt body to paste into Claude Code Routines

## Operational pointers

- **Schedule**: Weekly Monday 8:00 AM America/Chicago
- **Routine config**: claude.ai/code/routines → attach repo + Gmail connector + env vars
- **Local smoke test**: `python3 scanner/reddit_scan.py --dry-run --debug` (works in public mode from Mac IP)
- **GitHub Pages**: serves from `/docs` folder on `main` branch
- **Reddit script-app setup**: `prefs/apps` → script type → `redirect_uri = http://localhost:8080`

## Known quirks / gotchas

- **Reddit datacenter-IP block** — never remove env vars from the routine config or it'll silently 403.
- **2FA breaks password grant** — if you enable 2FA on the scanner Reddit account, OAuth will start failing.
- **Manual intake is non-negotiable** — FB/IG/TikTok hits arrive only via the weekly checklist + manual paste into `data/hits.json`.

## Where to look for more

- `README.md` — full setup walkthrough, deploy steps, Reddit + Gmail config
- `ROUTINE_PROMPT.md` — the prompt body
- `manual-intake/WEEKLY_CHECKLIST.md` — the 10-min FB/IG/TikTok walkthrough
- `git log --oneline -30`

## CLAUDE.md update workflow

On material changes (new platforms, new env var, schedule shift), the active session proactively offers an update.

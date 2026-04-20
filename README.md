# Intercambio PXM — Social Scanner

Finds people asking "where can I practice Spanish in Puerto Escondido?" across
social media, drafts a reply pointing them at Jacob's Saturday class, and
stashes each draft in Gmail for review.

## What it does

1. **Scans Reddit** (fully automated, free, no API key) across ~11 subreddits
   and 8+ queries, plus site-wide searches.
2. **Guides a weekly manual pass** over Facebook groups, Instagram, and
   TikTok — these platforms can't be safely automated.
3. **Creates a Gmail draft** for every relevant hit, each addressed to
   Jonathan so he can review before sending.
4. **Publishes a dashboard** at GitHub Pages showing all hits with filters by
   platform, status, date, and a free-text search.

## Architecture

```
  ┌──────────────────────┐          ┌─────────────────────┐
  │  Claude Code Routine │  weekly  │  Python scanner     │
  │  (runs in cloud)     ├─────────▶│  reddit_scan.py     │
  └──────────┬───────────┘          └─────────┬───────────┘
             │                                │
             │ uses Gmail MCP                 ▼
             │                        ┌───────────────────┐
             │                        │  data/hits.json   │
             │                        └────────┬──────────┘
             │                                 │ copied to
             ▼                                 ▼
  ┌──────────────────────┐           ┌──────────────────────┐
  │  Gmail drafts        │           │  docs/index.html     │
  │  (one per hit)       │           │  (GitHub Pages)      │
  └──────────────────────┘           └──────────────────────┘
```

## Repo layout

```
pxm-intercambio-scanner/
├── README.md                      ← you are here
├── ROUTINE_PROMPT.md              ← paste this into Claude Code Routines
├── scanner/
│   ├── reddit_scan.py             ← fully automated Reddit scanner (stdlib only)
│   ├── queries.json               ← subreddits + keywords (edit freely)
│   └── requirements.txt
├── data/
│   └── hits.json                  ← canonical dataset
├── docs/                          ← GitHub Pages serves this directory
│   ├── index.html                 ← dashboard
│   └── hits.json                  ← mirror of data/hits.json
├── manual-intake/
│   └── WEEKLY_CHECKLIST.md        ← 10-min FB/IG/TikTok walkthrough
├── templates/
│   ├── reply_en.md
│   └── reply_es.md
└── .gitignore
```

## One-time setup

### 1. Install Claude Code (if you haven't)
```bash
npm install -g @anthropic-ai/claude-code
```
Run `claude` from any terminal once to authenticate.

### 2. Put this project on GitHub
```bash
cd pxm-intercambio-scanner
git init
git add .
git commit -m "initial scaffold"
gh repo create pxm-intercambio-scanner --public --source=. --push
```
(`gh` is the GitHub CLI; `brew install gh` if you don't have it.)

### 3. Enable GitHub Pages
- Repo → Settings → Pages
- **Source:** Deploy from a branch
- **Branch:** `main` / folder `/docs`
- Save. Give it ~1 minute, then visit
  `https://jcpeters08.github.io/pxm-intercambio-scanner/`

### 4. Smoke-test the scanner locally
```bash
python scanner/reddit_scan.py --dry-run --debug
```
Should print a JSON summary. No output = no hits yet, which is normal.

### 5. Create the Claude Code Routine
- Go to <https://claude.ai/code/routines>
- **New routine** → attach `pxm-intercambio-scanner` repo → connect Gmail
- **Schedule:** weekly, Monday 8:00am America/Chicago
- Paste the prompt from `ROUTINE_PROMPT.md` (everything between the `====`
  markers) as the routine's instructions
- Save + run once manually to confirm it works

## Weekly flow (Monday morning)

1. Routine runs automatically at 8am CT.
2. You get Gmail drafts in your inbox ready to review — one per new relevant
   hit.
3. Open <https://jcpeters08.github.io/pxm-intercambio-scanner/> to see the
   full dashboard.
4. Run the `manual-intake/WEEKLY_CHECKLIST.md` for FB/IG/TikTok (~10 min),
   paste any hits into `data/hits.json`, push — next week's routine picks
   them up.

## Tuning

- **More/fewer subreddits or keywords:** edit `scanner/queries.json` and push.
- **Different tone in replies:** edit `templates/reply_en.md` and `_es.md`.
- **Different Gmail routing:** edit step 4 in `ROUTINE_PROMPT.md` (e.g., to
  send each draft to Jacob instead of you, or to send one digest email).

## Caveats

- **Reddit's public JSON endpoint** is rate-limited. The scanner sleeps 1.1s
  between requests and uses a descriptive User-Agent, which is generally
  sufficient. If you hit 429s, register a Reddit app and switch to PRAW.
- **Facebook / Instagram / TikTok** are not automated on purpose. Don't
  attempt to scrape them — risk of account lock > value of the posts.
- **The routine drafts replies, it never sends them.** You review + send
  yourself. This is a safety feature, not a limitation.

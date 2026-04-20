# Intercambio PXM — Social Scanner

Finds people asking "where can I practice Spanish in Puerto Escondido?" across
social media and open web, drafts a reply pointing them at Jacob's Saturday
class, and stashes each draft in Gmail for review.

## What it does

1. **Scans Reddit** via the OAuth API across ~20 subreddits and 10+ queries,
   plus site-wide searches.
2. **Ingests Google Alerts** from Gmail — catches blog posts, forum threads,
   Medium, Tripadvisor, any indexed web mention.
3. **Guides a weekly manual pass** over Facebook groups, Instagram, and
   TikTok — these platforms can't be safely automated.
4. **Creates a Gmail draft** for every relevant hit, each addressed to you so
   you can review before sending.
5. **Publishes a dashboard** at GitHub Pages showing all hits with filters by
   platform, status, date, and a free-text search.

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

## Repo layout

```
pxm-intercambio-scanner/
├── README.md                      ← you are here
├── ROUTINE_PROMPT.md              ← paste into Claude Code Routines
├── scanner/
│   ├── reddit_scan.py             ← Reddit scanner (OAuth + public fallback)
│   ├── queries.json               ← subreddits + keywords
│   └── requirements.txt
├── data/hits.json                 ← canonical dataset
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

### 1. Install Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```
Run `claude` once to authenticate.

### 2. Push this project to GitHub
```bash
cd ~/Git/pxm-intercambio-scanner
git init
git add .
git commit -m "initial scaffold"
gh repo create pxm-intercambio-scanner --public --source=. --push
```

### 3. Enable GitHub Pages
- Repo → Settings → Pages
- **Source:** Deploy from a branch
- **Branch:** `main` / folder `/docs`
- Wait ~60 seconds, visit
  `https://jcpeters08.github.io/pxm-intercambio-scanner/`

### 4. Create a Reddit script app (3 minutes — required)

Reddit blocks unauthenticated requests from datacenter IPs (including
Anthropic's Routine runtime). The scanner must use OAuth when it runs in
the cloud.

1. **Recommended:** create a dedicated Reddit account without 2FA for the
   scanner — or use your personal account but disable 2FA on it (since the
   password grant flow doesn't support OTP reliably). If you need 2FA on
   your personal account, create a throwaway.
2. Go to <https://www.reddit.com/prefs/apps>.
3. Scroll down, click **"are you a developer? create an app..."**.
4. Fill in:
   - **name:** `pxm-intercambio-scanner`
   - **type:** select **script** (critical — must be "script", not "web app")
   - **description:** `weekly PXM intercambio scanner`
   - **about url:** leave blank
   - **redirect uri:** `http://localhost:8080` (required but unused for script apps)
5. Click **create app**.
6. You now see:
   - The app's **client ID** (the short string right under "personal use script")
   - The **client secret**
7. Record four values for the next step:
   - `REDDIT_CLIENT_ID` = the client ID
   - `REDDIT_CLIENT_SECRET` = the client secret
   - `REDDIT_USERNAME` = the Reddit account username
   - `REDDIT_PASSWORD` = that account's password

### 5. Set up Google Alerts + Gmail filter (5 minutes)

1. Go to <https://www.google.com/alerts> (must be signed in as
   jcpeters08@gmail.com).
2. Create these alerts, one at a time. For each, set **How often = "At most
   once a day"**, **Sources = Automatic**, **Region = Any region**,
   **How many = All results**, **Deliver to = your email**:
   - `"Puerto Escondido" "language exchange"`
   - `"Puerto Escondido" intercambio`
   - `"Puerto Escondido" "learn Spanish"`
   - `"Puerto Escondido" "Spanish tutor"`
   - `"Puerto Escondido" "practice Spanish"`
3. In Gmail, create a filter:
   - **From:** `googlealerts-noreply@google.com`
   - **Apply label:** `Google-Alerts` (create the label if it doesn't exist)
   - Optional: **Skip the Inbox** (so they don't clutter your main view)
4. Wait 24 hours for the first alerts to start arriving, then verify the
   label is getting populated.

### 6. Smoke-test the scanner locally
```bash
cd ~/Git/pxm-intercambio-scanner
python3 scanner/reddit_scan.py --dry-run --debug
```
From your Mac (non-datacenter IP), the scanner works in `public` mode
without any env vars. Output should show `"auth_mode": "public"` and a JSON
summary.

To test OAuth locally too, export the env vars first:
```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USERNAME="..."
export REDDIT_PASSWORD="..."
python3 scanner/reddit_scan.py --dry-run --debug
```
Should output `"auth_mode": "oauth"`.

### 7. Create the Claude Code Routine
1. Go to <https://claude.ai/code/routines>
2. **New routine** → attach `pxm-intercambio-scanner` repo → connect Gmail
3. Set these environment variables / secrets on the routine:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USERNAME`
   - `REDDIT_PASSWORD`
4. **Schedule:** weekly, Monday 8:00am America/Chicago
5. Paste the prompt from `ROUTINE_PROMPT.md` (everything between the `====`
   markers) as the routine's instructions
6. **Save** then **Run now** once to confirm end-to-end works. Output
   should show `auth_mode: oauth` and at least some new hits (or at least
   no 403 errors).

## Weekly flow (Monday morning)

1. Routine runs automatically at 8am CT.
2. You get Gmail drafts ready to review — one per relevant hit (Reddit or
   web alert).
3. Open <https://jcpeters08.github.io/pxm-intercambio-scanner/> for the
   dashboard.
4. Run `manual-intake/WEEKLY_CHECKLIST.md` for FB/IG/TikTok (~10 min),
   paste any hits into `data/hits.json`, push — next week's routine picks
   them up.

## Tuning

- **More/fewer subreddits or keywords:** edit `scanner/queries.json` and push.
- **Different reply tone:** edit `templates/reply_en.md` / `_es.md`.
- **Different Gmail routing:** edit step 5 in `ROUTINE_PROMPT.md`.
- **More Google Alerts:** add at <google.com/alerts>, the Gmail filter catches
  them automatically.

## Caveats

- **Reddit datacenter-IP block:** the scanner requires OAuth in cloud runtimes.
  Don't remove the env vars from the routine config.
- **FB / IG / TikTok** are not automated on purpose. Don't scrape them.
- **The routine drafts replies, never sends them.** You review + send
  yourself. Safety feature, not a limitation.
- **2FA on Reddit breaks password grant.** Use a dedicated no-2FA account
  for the scanner.

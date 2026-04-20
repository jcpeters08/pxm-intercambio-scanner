# Claude Code Routine — Paste this into your weekly routine

Copy the prompt between the `====` markers into a new Routine on
[claude.ai/code/routines](https://claude.ai/code/routines) and attach this repo
to it. Suggested schedule: **Mondays at 8:00am America/Chicago**.

## Required

- **GitHub connector** with read/write access to `jcpeters08/pxm-intercambio-scanner`
- **Gmail connector** (for creating drafts AND reading Google Alerts)
- **Environment variables / secrets** on the Routine:
  - `REDDIT_CLIENT_ID` — from a script-type app at <https://www.reddit.com/prefs/apps>
  - `REDDIT_CLIENT_SECRET` — same page
  - `REDDIT_USERNAME` — the Reddit account tied to the app (ideally a dedicated no-2FA account)
  - `REDDIT_PASSWORD` — that account's password

  Without these, Reddit calls will get HTTP 403 from any datacenter IP,
  including Anthropic's Routine runtime. See README for the 3-minute Reddit
  app setup.

=========================== COPY BELOW ===========================

You are the Intercambio PXM social-scanner routine. You run once a week. Your
job is to surface new people asking about language exchange in Puerto
Escondido (across Reddit and Google Alerts), draft a reply for each, and stash
those drafts in Gmail so Jonathan can review and send them Monday morning.

Repository layout (assume you are at the repo root):
- `scanner/reddit_scan.py` — Python scanner; uses OAuth via env vars
- `scanner/queries.json` — search config (subreddits, queries, filters)
- `data/hits.json` — canonical dataset (also mirrored to `docs/hits.json`)
- `docs/index.html` — GitHub Pages dashboard
- `manual-intake/WEEKLY_CHECKLIST.md` — FB/IG/TikTok checklist Jonathan does by hand
- `templates/reply_en.md` and `templates/reply_es.md` — base reply drafts

Do exactly these steps, in order:

1. **Run the Reddit scanner.**
   ```
   python scanner/reddit_scan.py
   ```
   It prints a JSON summary on stdout. Capture `auth_mode`, `new_hits`, and
   the `new` list. If `auth_mode` is `"public"` and there are errors, the
   Reddit env vars aren't set correctly — log that loudly in the commit
   message and run output. If `auth_mode` is `"oauth"`, proceed.

2. **Ingest Google Alerts from Gmail.** Use the Gmail connector to search
   threads:
   ```
   from:googlealerts-noreply@google.com newer_than:7d
   ```
   For each thread found in the last 7 days:
   - Fetch the full body (HTML).
   - Extract every link that matches the pattern
     `https://www.google.com/url?q=<ACTUAL_URL>&...` — decode the
     `q` parameter to get the real destination URL.
   - For each distinct real URL:
     - Skip if the domain is `reddit.com` (the Reddit scanner already
       covers those and would produce duplicates).
     - Skip if the URL is already in `data/hits.json` (check by URL).
     - Add a new hit with:
       ```json
       {
         "id": "alert:<md5-of-url-first-12-chars>",
         "platform": "web",
         "subreddit": null,
         "title": "<link text from the alert email>",
         "summary": "<the snippet Google Alerts showed>",
         "author": "<domain name of the URL>",
         "url": "<real destination URL>",
         "created_at": "<Alert email Date header, ISO format>",
         "found_at": "<now, ISO format>",
         "status": "new",
         "draft_id": null,
         "notes": "Found via Google Alerts"
       }
       ```

3. **Triage all new hits (from Reddit + Alerts).** For each:
   - If it's a Reddit post, read the full body (fetch `{url}.json` or use the
     Reddit connector).
   - If it's a web page from an alert, fetch the page content via web tools.
   - Decide: is the OP genuinely asking how to practice Spanish / find a
     language exchange / take Spanish lessons in Puerto Escondido, or is a
     Mexican local asking about English practice? If not, set the hit's
     `status` to `"skipped"` and add a short reason in `notes`.
   - If relevant, continue.

4. **Draft a reply.** Start from `templates/reply_en.md` (or `_es.md` if the
   post is in Spanish). Adapt to the OP's actual question — don't just
   copy-paste. Keep it short (< 180 words), warm, no emoji flood.

   For web-page hits (blog comments, forum threads, Tripadvisor), skip
   drafting a reply and set status to `"skipped"` with note
   `"web page — reply manually if relevant"`. We draft replies only for
   platforms where we know the reply mechanism.

5. **Create a Gmail draft.** For each hit you're drafting a reply for:
   - Subject: `[Intercambio PXM] <platform> — <short title>`
   - To: `jcpeters08@gmail.com`
   - Body:
     1. One-line "what to do": e.g. `"Reply on Reddit here: <url>"`.
     2. Post summary (2–4 lines).
     3. The drafted reply, delimited with `---` fences.
   - Capture the returned draft ID. Set `hit.draft_id` and
     `hit.status = "drafted"` in `data/hits.json`.

6. **Regenerate the dashboard data.** Copy `data/hits.json` over
   `docs/hits.json`.

7. **Commit and push.**
   - Branch: `main`
   - Commit message: `weekly scan — +<N> new (<R> reddit, <A> alerts), <M> drafted, <K> skipped`
   - Push.

8. **Post a summary in your run output:**
   - Auth mode (should be `oauth`)
   - Total hits in dataset
   - New this run, split by platform, with titles + links
   - Drafted, with Gmail draft IDs
   - Skipped, with reasons
   - Any errors from the scanner
   - Reminder: *"Run the manual intake checklist for FB/IG/TikTok — see manual-intake/WEEKLY_CHECKLIST.md"*

Rules:
- Never send email, never DM anyone — always stop at "drafted".
- Never commit secrets. Reddit creds come from env vars, never from files.
- Never automate FB/IG/TikTok scraping. Jonathan does that by hand.

=========================== COPY ABOVE ===========================

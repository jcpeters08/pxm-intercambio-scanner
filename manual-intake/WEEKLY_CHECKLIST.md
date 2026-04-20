# Weekly Manual Intake — FB / IG / TikTok

Reddit is fully automated. Facebook, Instagram, and TikTok cannot be safely scraped — their ToS prohibits it and public search APIs are locked down. So we do this part by hand, ~10 minutes once a week.

The Routine will ask you to run this checklist and paste any relevant URLs into `data/hits.json` (instructions below).

---

## Monday morning checklist (10 minutes)

### 1. Facebook (5 min)
Open each group in a logged-in browser session and search within it:

- [ ] **Puerto Escondido Expats / Expat Community** (search: "language exchange", "intercambio", "learn Spanish")
- [ ] **Puerto Escondido For Sale, Services, Recommendations** (search: "Spanish class", "tutor")
- [ ] **Digital Nomads Puerto Escondido** (search: "Spanish", "intercambio")
- [ ] **Puerto Escondido Community** (search: "language", "Spanish")
- [ ] Any other PXM-focused groups Jonathan is in

For each hit: copy the post URL, the OP's name, a 1–2 sentence summary of what they're asking.

### 2. Instagram (3 min)
Search these hashtags and sort by **recent**:
- [ ] `#puertoescondido` (skim last 24 posts for anyone asking in captions)
- [ ] `#pxm`
- [ ] `#puertoescondidomexico`
- [ ] `#learnspanish` (filter to PXM location if you can)

IG doesn't let you DM strangers who don't follow you without requesting — note that as friction.

### 3. TikTok (2 min)
Search these in the TikTok app and sort by recent:
- [ ] `puerto escondido spanish`
- [ ] `learn spanish mexico`
- [ ] `intercambio puerto escondido`

TikTok is mostly video creators, not Q&A. Low expected hit rate.

---

## How to add a hit to the dataset

Open `data/hits.json` and append a new object to the array:

```json
{
  "id": "facebook:EXPATGROUP-2026-04-19-alice",
  "platform": "facebook",
  "subreddit": null,
  "title": "Alice asking about Spanish classes in La Punta",
  "summary": "Posted in Puerto Escondido Expats group: 'Just moved here, looking for a language exchange or affordable Spanish classes...'",
  "author": "Alice R.",
  "url": "https://www.facebook.com/groups/.../posts/...",
  "created_at": "2026-04-18T14:00:00+00:00",
  "found_at": "2026-04-19T09:30:00+00:00",
  "status": "new",
  "draft_id": null,
  "notes": "Alice said she's here for 6 weeks."
}
```

Rules:
- **id** must be unique. Use pattern `<platform>:<slug>`.
- **created_at** should be the post's actual date (approximate is fine).
- **platform** must be one of: `reddit`, `facebook`, `instagram`, `tiktok`.
- **status** starts as `"new"`.

The Routine will pick these up on the next run and create Gmail drafts for them.

---

## Why manual?

| Platform | Why automation isn't safe |
|----------|---------------------------|
| Facebook | Group content requires a logged-in session. Graph API doesn't expose public-group search. Selenium-based scraping violates ToS and triggers account locks. |
| Instagram | Scraping violates ToS. `instagram-private-api` libraries routinely break and risk account suspension. |
| TikTok  | No public search API. Unofficial scrapers are short-lived and unreliable. |

If you eventually want any of these automated, the legitimate path is to run paid ads that drive people to a landing page — not scraping.

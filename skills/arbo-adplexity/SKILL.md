---
name: arbo-adplexity
description: Use AdPlexity ads as inspiration for new titles. AdPlexity is an ad intelligence service; CK pulls from it, every day, Facebook image ads of other advertisers that send traffic to arbitrage (search feed / RSOC) networks such as Tonic, System1, Sedo or Predicto, so they are competitors running the same business. Explains what the data is and its filters, then finds the angles those advertisers keep running, checks them against this division and writes new titles (get_adplexity_overview, search_adplexity_ads, list_adplexity_pages, mark_adplexity_ads_used). Use when the user mentions AdPlexity, asks what arbitrage competitors or RSOC advertisers are running, wants title ideas or inspiration from AdPlexity or from other arbitrage advertisers, or asks which Facebook pages or sites are scaling arbitrage traffic.
---

# AdPlexity title inspiration

You read the AdPlexity ads that CK has saved, find the angles other arbitrage advertisers keep paying for, and turn them into new titles for this division.

**Needs:** the CK MCP tools. Nothing else: the tools read data CK has already saved, so they never call AdPlexity and cost no AdPlexity credits.

## What AdPlexity is

AdPlexity is a paid ad intelligence service. It crawls ads, follows them to their landing pages and detects which arbitrage network the landing page monetises with (search feed / RSOC partners like Tonic, System1, Sedo, DomainActive, Yahoo, Media.net, Codefuel, AFS, Predicto, Aporia, Inuvo, Compado...). Advertisers on these networks run the same model as us: an informational article whose revenue comes from search ad clicks. Their long-running ads are a free signal of which topics and hooks pay.

## What CK saves

A daily CK task pulls from AdPlexity:
- only **Facebook image ads** (no videos);
- only ads on a **known arbitrage network** (ads AdPlexity could not attribute to a network are skipped);
- only ads that had already been **running at least 3 days** when pulled;
- **newest first**, stopping at the first ad already saved, within a **monthly AdPlexity credit budget** (about 1 credit per ad). So the store is a sample of the newest qualifying ads, not every ad on the market. `get_adplexity_overview` shows the budget and what was spent.

Each saved ad has:

| Field | Meaning |
|---|---|
| `adId` | AdPlexity id of the ad |
| `title` | the ad headline |
| `description` | the ad primary text |
| `caption` | the display link / domain shown on the ad |
| `countries` | country codes where AdPlexity saw it |
| `networks` | arbitrage networks detected on its landing page |
| `daysRunning`, `firstSeen`, `lastSeen` | how long it has run, as of the pull |
| `isActive` | whether the Facebook ad was still active at the pull |
| `facebookPageId`, `facebookPageName` | the page that runs it |
| `landingPageUrl` | the advertiser's article. Its path and query (slug, `adtitle=`) usually spell out the article title. Looked up once per Facebook page, so most ads carry their page's link (`linkFromPage: true`); a few have none yet |
| `usedForTitles` | this division already used it (see step 6). Other divisions track their own |

`daysRunning` is a snapshot from the day of the pull; ads are not refreshed later.

## Tools

- `get_adplexity_overview`: totals, ads not yet used by this division, first-seen date range, ads per network and per country, credit budget. Call it first.
- `search_adplexity_ads`: the ads. Filters (all optional, combined with AND):
  - `countries`: any of the codes, e.g. `["US","GB"]`;
  - `networks`: any of the names, partial and case insensitive, e.g. `["Tonic"]`;
  - `text`: searched in title, description, caption and page name;
  - `facebookPageId`: one page's ads;
  - `minDaysRunning`: only ads that ran at least N days;
  - `firstSeenInLastDays`: only recent ads;
  - `unusedOnly`: skip ads this division already used;
  - `orderBy`: `newest` (default) or `longest`;
  - `maxResults` (default 50, max 200) and `skip` for paging.
- `list_adplexity_pages`: Facebook pages by number of saved ads, with the site they send to. Filters: `text` (page name or site), `minAds`.
- `mark_adplexity_ads_used`: marks ads as used by this division, with a note (reference or tag).

Pull in pages of 50 to 100 and summarise; never dump hundreds of ads into the chat.

## Shared memory

If the `memory_*` tools are available (see the **arbo-memory** skill): at the start call `memory_briefing` with your agent name and `scopeLinks` for the verticals/countries you will touch, follow active objectives (new titles fall under `new-titles`), and read the journal so you don't repeat another agent's titles. At the end, after a submit, write one `Journal` entry (count, verticals, countries, reference or tag); for a generation launch also a review `Task` about 3 days out, linked to the tag.

**Verticals and themes.** These are the same thing: the topic a title, article and adset belongs to. They are split into two kinds only for legacy reasons.
- A **vertical** is top level (`isTopLevel: true` in `get_verticals`), for example `Sale` or `Jobs`.
- A **theme** (`isTopLevel: false`) is a child of exactly one vertical, named in `parentVertical`. It narrows that vertical and can never go beyond its scope.
- Wherever a vertical name is asked for, a theme name works the same way: in title payloads, in the stats, and as `Vertical.Name` in queries. Names are unique across both kinds. Prefer the most specific entry that fits.
- In rare cases nothing fits. Don't force the closest vertical. Say so, and recommend a new top-level vertical with a PascalCase name and a one-sentence description. The user adds verticals by hand in CK. New themes are created with `create_theme`, only when the user explicitly asks.

## 1. Scope

Ask (or take from the request) which countries, verticals or networks to look at. Default: the countries this division spends in (one stats query, see step 3) and `unusedOnly: true`.

## 2. Find the angles

1. `get_adplexity_overview` to see which networks and countries have data.
2. `search_adplexity_ads` for the scope, `minDaysRunning: 5` or more and `orderBy: "longest"` first: ads that keep running are the ones paying. Then a `newest` pass for fresh angles.
3. Signals, strongest first:
   - **the same article or angle run as many ads, by several pages or in several countries;**
   - a page with many saved ads (`list_adplexity_pages`) is scaling: look at its ads;
   - high `daysRunning`, still `isActive`.
4. For each angle note: the topic, the hook (what's replacing X, warning signs, how much it costs, what it may look like in 2027, a named city or public programme...), the markets, and what makes it concrete. Read the landing page slug: it is usually the article title behind the ad.
5. Map each angle to the most specific vertical or theme of this division (`get_verticals`). Note angles that fit no vertical, and sub-topics that are being scaled inside a vertical but that none of its themes covers. Propose those separately (parent vertical, PascalCase name, one or two sentence description, evidence); create a theme only when the user explicitly asks.

## 3. Check against the division

Only bring angles we don't already run:
- Where it spends: one stats query (arbo-stat-queries skill) grouping 14 days by `Vertical.Name` and `Country` with spend and ROI. Place titles in verticals × countries that perform.
- Overlap: one query over 30 days matching each candidate angle as a regex on `Title` (all verticals), returning count, spend, ROI and two sample titles per angle. Skip angles already well covered; treat an angle that clearly lost for us as weak evidence when it only spent a few dollars.

## 4. Write titles

Follow **all** rules of the **arbo-title-creator** skill (hard rules, intellectual property, production-ready language, years, self-check). These rules are absolute, even when the AdPlexity ad breaks them:
- **Neutral third-party voice: no seller offers, no promises.** Every title is the headline of an independent informational article. We do not sell, ship, finance, book or provide anything. In any language, never:
  - speak as the seller or provider: "we", "our", "us", "my", "shop our", "we offer", "buy from us", "official sale";
  - mention a condition only a seller can give: free delivery or shipping, installments, pay in X months, 0% financing, pay later, free returns, a warranty, promo codes, "in stock", free trial, "purchase conditions";
  - promise anything: guaranteed results or approval, savings, a price or availability the reader will get;
  - tell the reader to buy: "buy", "order", "shop", "book now", "apply now".

  Something free or covered by a public service or insurance ("Free eye tests on the NHS") is fine.
- **Finance topics, never loan offers.** Loans and credit are allowed as informational articles, never with an amount, duration, repayment term or rate.
- **Never name** a bank or other financial institution, a store, retailer or marketplace, a fashion or cosmetics brand, or a service chain. Use the generic subject.
- **No demographic targeting** ("over 60", "for seniors", ...), even though arbitrage ads use it constantly. Keep the subject, drop the audience.
- No prescription drugs, no emojis, no exclamation marks, no ALL-CAPS words.

AdPlexity copy is evidence of the angle, never text to copy. Rewrite every title in your own words, localise it to the target country and language with real local values, and spread the set across verticals and countries.

Show a table: #, vertical, country, title, English, source (adIds, page, days running). Let the user drop or change rows.

## 5. Submit (only on the user's explicit go)

- **Default: recommendations.** `set_new_article_titles` with `referenceName: "claude-adplexity"`, unless the user names another reference. No money is spent; the automatic pipeline picks them up when the country × vertical performs.
- **Generation only when the user explicitly asks** to launch / generate ads: `submit_titles_for_generation`. It creates real articles and adsets that spend budget: say so once, and follow arbo-title-creator step 7 (affiliate for every title from `get_affiliate_providers`, never guessed; tag suggested as `t:adplexity-YYYYMMDD`; budget, cap, account, image prompt and search query only if the user gives them). Show the final list with affiliate and tag and get a clear yes.
- One invalid row rejects the whole batch: validate vertical names, country and language codes first. Fix skipped titles as their reason says and resubmit only after the user agrees.

## 6. Mark the source ads

Right after a successful submit, call `mark_adplexity_ads_used` with the adIds behind the accepted titles (leave out skipped ones) and a note with the reference or tag. Later runs with `unusedOnly: true` then bring only new material. Marking is per division; it never hides ads from other divisions.

---
name: arbo-competitor-scout
description: Scout competitors' Meta (Facebook) Ad Library ads for title inspiration. Pulls a competitor's longest-running, highest-impression ads through the browser into a local db (so later scans only bring new ads), finds the angles they are scaling, checks them against this division's verticals, themes and live titles, recommends missing themes (and, rarely, missing verticals), writes new titles and submits them as recommendations (reference claude-competitors) or, when asked, for generation. Use when the user asks to scan, sync or pull a competitor (domain, Facebook page id or Ad Library link), add one to the list, see what competitors are running, or wants title ideas from competitors or ideas for new themes.
---

# Competitor scout

You pull competitors' ads from the Meta Ad Library, keep them in a local database, and turn the angles competitors are scaling into new titles for this division.

**Needs:** a local agent that can run `python3`, the CK MCP tools, and a browser tool that can navigate and run JavaScript in a page (the Claude desktop built-in browser, Claude in Chrome, or similar). It does not work in a chat without a browser.

## Where things live

- **This skill's folder is read-only.** It comes from the shared arbo-skills repo that users only pull. Never create, edit or delete anything in it (or anywhere in that repo), and never suggest doing so; changes there cause pull conflicts. If the skill or the extractor needs a fix, tell the user what is wrong so they can report it to the skill owner.
- **`SYNC`** below means `python3 <this skill's folder>/sync.py`, run from the user's own project folder (where they work with you, e.g. their stats repo). The script also refuses to write into the skills repo.
- **The data folder** is `./competitors/` in that project folder (or `--data <folder>` / `$ARBO_COMPETITORS_DIR` if the user wants it elsewhere). It is the user's own and is created on first use, seeded with the shared competitor list:
  - `competitors.json`: the competitors (`id`, `domain` or `page_id`, optional `country`, `query`, `notes`; `last_sync`, `dropped` are set by the script).
  - `db/ads.json`: every ad pulled, keyed by Ad Library ID, with when it was first and last seen, whether it was analysed (vertical, angle) and used for a title.
  - `db/scans.json`: every scan (when, which competitor, how many ads loaded / new / already known).
  - `db/recommendations.json`: every title submitted from competitor ads (mode, reference or tag, source ads), so nothing is repeated.
  - `verticals.json`: this division's verticals, refreshed from the MCP every run.
  - `drafts/`, `insights/`: title batches before submitting, analysis notes.
  Never edit the db files by hand; use `SYNC`. Files you write for handoff (extractor output, logs) go to your scratch/temp folder.

## Shared memory

If the `memory_*` tools are available (see the **arbo-memory** skill): at the start call `memory_briefing` with your agent name and `scopeLinks` for the verticals/countries you will touch, follow active objectives (new titles fall under `new-titles`), and read the journal so you don't repeat another agent's titles. At the end, after a submit, write one `Journal` entry (count, verticals, countries, reference or tag); for a generation launch also a review `Task` about 3 days out, linked to the tag.

**Verticals and themes.** These are the same thing: the topic a title, article and adset belongs to. They are split into two kinds only for legacy reasons.
- A **vertical** is top level (`isTopLevel: true` in `get_verticals`), for example `Sale` or `Jobs`.
- A **theme** (`isTopLevel: false`) is a child of exactly one vertical, named in `parentVertical`. It narrows that vertical and can never go beyond its scope. A theme under `Sale` can be about a kind of sale, but never about jobs or anything else outside sales.
- Wherever a vertical name is asked for, a theme name works the same way: in title payloads, in the stats, and as `Vertical.Name` in queries. Names are unique across both kinds. Prefer the most specific entry that fits.
- In rare cases nothing fits. Don't force the closest vertical. Say so, and recommend a new top-level vertical with a PascalCase name and a one-sentence description. The user adds verticals by hand in CK; there is no tool for it. New themes are created with `create_theme`, and only when the user explicitly asks.

## 1. Pick competitors

- `SYNC list` shows the competitors with ads pulled and last scan (`--all` includes dropped ones). `SYNC scans` shows the scan history.
- The user may name listed competitors, or give a new **domain**, **Facebook page id** or **Ad Library / page link**: `SYNC add <it> [--country CC]` (it prints the id to use). A domain is searched as a keyword and the extractor keeps only ads that link to it; use a page id when the user cares about one page.
- Only scan what the user asks for. Never scan the whole list unasked (it is long and each scan takes a minute).

## 2. Scan (per competitor)

1. `SYNC url <id>` → navigate the browser there. The link shows active ads, all countries, sorted by total impressions, so the top is what has grown.
2. Check the page shows results (page text). A login wall or CAPTCHA: stop and ask the user to handle it in the browser. Never log in or solve a CAPTCHA.
3. `SYNC js <id> [--limit N]` (default 100; 60 is enough for a first look) → run the printed snippet verbatim in the page with the browser's JavaScript tool. It scrolls, then returns compact TSV: a `#loaded=.. off_domain=.. known=..` header and one line per ad not yet in the db.
   - `REINSTALL` means this tab doesn't have the current extractor yet: run the output of `SYNC js <id> --mode install` once in the tab, then the run snippet again. (The extractor is kept in the tab's `window.name`; Facebook clears unknown localStorage keys and its CSP blocks eval, so the snippet loads it as a blob script.)
4. Write the returned string exactly as the tool printed it (outer quotes included) to a temp file, then `SYNC merge <id> <file>`. This stores the new ads, refreshes `last_seen` of known ones and logs the scan.
5. **No ads:** the library shows no results, or `loaded` > 0 but every ad is `off_domain`. For a subdomain (`sub.example.com`), first set `"query": "example.com"` on that entry in `competitors.json` and retry (the filter still uses the full host). Still nothing: `SYNC drop <id> --reason "..."`. Dropped competitors are never scanned again unless the user asks for that one by name.
6. If `new` is 0 on a page that clearly has ads you haven't stored, the Ad Library layout changed: tell the user the extractor needs an update from the skill owner (don't patch it in the skills folder).

Report one line per competitor (new / already known / total), nothing more.

## 3. Analyse

`SYNC pending [--competitor id] [--min-days N]` lists ads running at least N days (default 7) that nobody has analysed yet, grouped per article (landing URL). Younger ads stay in the db and show up on a later scan once they have grown.

Signals, strongest first:
- **one article run as many ads / on many pages** (`ads`, `pages`): they are scaling it;
- `max_days` still active;
- `best_rank` in the impressions sort.

Find the angles: topic, hook ("what's replacing X", "warning signs", "how much it costs", "may look like in 2027", named city or public programme), the markets (landing language), and what makes it concrete. Then:
- `SYNC verticals <file>` with the output of `get_verticals` saved to a temp file (every run; the division decides the verticals).
- For every article you judged: `SYNC mark <ids...> --vertical <exact vertical or theme | none> --angle "<short angle>"`. Pick the most specific entry whose name and description fit: a theme when one covers the article, otherwise its top-level vertical. Use `none` only when no vertical fits at all. Later ads for an analysed article inherit it.
- **Missing themes.** Look for a sub-topic that competitors are scaling, falls clearly inside one top-level vertical, and that none of its themes covers. That means several articles, or one article run as many ads or on many pages, that you could only mark with the top-level vertical. `get_verticals` with `vertical: "<parent>"` shows the existing themes. Propose each one with:
  - the parent vertical;
  - a PascalCase name that is not used by any vertical or theme;
  - a one or two sentence description of what is in scope and how it differs from its sibling themes;
  - the evidence: competitors, articles, ads, pages and days running.

  Never propose a theme outside its parent's scope. If the sub-topic doesn't belong to any vertical, it is a missing vertical, not a theme.
- **Missing verticals (rare).** When big angles stay `none`, propose a new top-level vertical with a name, a description and the evidence. The user adds it by hand in CK.
- Write a short note to `insights/YYYY-MM-DD-<topic>.md` in the data folder (patterns per competitor, what we can't use and why). Keep chat short.

Show proposed themes and verticals to the user as a short table, separate from the titles. Create a theme only when the user explicitly asks. Use `create_theme` with the confirmed vertical, name and description, following arbo-title-creator step 8. Then refresh with `SYNC verticals` and re-mark the source articles with the new theme, so titles from them use it.

## 4. Check against the division

Before writing titles, find out what this division already runs, so you only bring new angles:
- Where it spends: one stats query (arbo-stat-queries skill) grouping 14 days by `Vertical.Name` and `Country` with spend and ROI. Place titles in verticals × countries that perform.
- Overlap: one query over 30 days matching each candidate angle as a regex on `Title` (all verticals), returning count, spend, ROI and two sample titles per angle. Skip angles that are already well covered; treat an angle that clearly lost for us as weak evidence (say so) rather than a hard no when it only spent a few dollars.
- `SYNC rec-list [--vertical V] [--country C]`: titles already submitted from competitors. Never resubmit the same or a near-duplicate (same subject and country, synonyms or reordering only).
- `SYNC ideas [--vertical V]` lists analysed articles mapped to verticals that haven't fed a title yet.

## 5. Write titles

Follow **all** rules of the **arbo-title-creator** skill (hard rules, intellectual property, production-ready language, years, self-check). On top of them, these house rules are absolute, even when a competitor or one of our own winners breaks them:
- **No loan offers:** never show a loan with an amount, duration, repayment term or rate ("80 000 Ft loan without a job", "6-month repayment", "5,000 euro credit limit"). Facebook flags them.
- **Never name a financial institution:** banks, lenders, card issuers, payment / buy-now-pay-later companies, credit bureaus (e.g. Schufa), insurers, or a government finance institution (pension fund, tax office, development bank). Use the generic subject.
- **Never name a retailer or marketplace:** supermarkets, discounters, DIY, furniture, electronics and department stores, online marketplaces (Lidl, Walmart, Amazon, IKEA, Temu...).
- **No demographic targeting:** no "over 60", "for seniors", "70+", "for retirees", even though competitors use it constantly. Keep the subject, drop the audience.
- No prescription drugs (competitors push GLP-1 injections; skip them).

Competitor copy is evidence of the angle, never text to copy. Localise to the target country with real local values, and spread the set across verticals and countries.

Save the batch to `drafts/YYYY-MM-DD-<name>.json` in the data folder before showing it:
```json
{"mode": "recommendation", "reference": "claude-competitors", "status": "draft",
 "titles": [{"vertical": "Health", "countryCode": "GB", "languageCode": "en", "title": "...", "titleInEnglish": "...", "source_ids": ["<library ids>"]}]}
```
Show a table: #, vertical, country, title, English, source (competitor, ads / pages / days running). Let the user drop or change rows.

## 6. Submit (only on the user's explicit go)

- **Default: recommendations.** `set_new_article_titles` with `referenceName: "claude-competitors"`, unless the user names another reference. No money is spent; the automatic pipeline picks them up when the country × vertical performs.
- **Generation only when the user explicitly asks** to launch / generate ads: `submit_titles_for_generation`. It creates real articles and adsets that spend budget: say so once, and follow arbo-title-creator step 7 (affiliate for every title from `get_affiliate_providers`, never guessed; tag suggested as `t:competitors-YYYYMMDD`; budget, cap, account and image prompt only if the user gives them). Show the final list with affiliate and tag and get a clear yes.
- One invalid row rejects the whole batch: validate vertical names (`verticals.json`), country and language codes first.
- Right after a successful submit, log exactly what was accepted (leave out skipped titles): set `mode` (`recommendation` / `generation`), `reference` or `tag` and `affiliate` in the draft file, then `SYNC rec-log <file>`. This marks the source ads as used so `ideas` won't offer them again.
- If Arbo is down, keep the draft and submit it later.

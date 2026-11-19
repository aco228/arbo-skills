---
name: arbo-adplexity
description: Use AdPlexity ads as inspiration for new titles. AdPlexity is an ad intelligence service; CK pulls from it, every day (and when someone captures searches in the browser), Facebook image ads of other advertisers that send traffic to arbitrage (search feed / RSOC) networks such as Tonic, System1, Sedo or Predicto, so they are competitors running the same business. Also covers CK's own Facebook ad library scrape: image ads of competitor Facebook pages we follow, organized in scrape groups. Explains what the data is and its filters, then finds the angles those advertisers keep running, checks them against this division and writes new titles (get_adplexity_overview, search_adplexity_ads, list_adplexity_pages, mark_adplexity_ads_used, get_facebook_scrape_overview, search_facebook_scrape_ads, list_facebook_scrape_pages, mark_facebook_scrape_ads_used). Use when the user mentions AdPlexity, the Facebook ad library scrape, scrape groups or followed competitor pages, asks what arbitrage competitors or RSOC advertisers are running, wants title ideas or inspiration from AdPlexity or from other arbitrage advertisers, or asks which Facebook pages or sites are scaling arbitrage traffic.
---

# AdPlexity title inspiration

You read the competitor ads that CK has saved (from AdPlexity and from CK's own Facebook ad library scrape), find the angles other arbitrage advertisers keep paying for, and turn them into new titles for this division.

**Needs:** the CK MCP tools. Nothing else: the tools read data CK has already saved, so they never call AdPlexity or Facebook and cost no AdPlexity credits.

## What AdPlexity is

AdPlexity is a paid ad intelligence service. It crawls ads, follows them to their landing pages and detects which arbitrage network the landing page monetises with (search feed / RSOC partners like Tonic, System1, Sedo, DomainActive, Yahoo, Media.net, Codefuel, AFS, Predicto, Aporia, Inuvo, Compado...). Advertisers on these networks run the same model as us: an informational article whose revenue comes from search ad clicks. Their long-running ads are a free signal of which topics and hooks pay.

## What CK saves

Ads come in two ways:
1. A daily CK task pulls from AdPlexity:
   - only **Facebook image ads** (no videos);
   - only ads on a **known arbitrage network** (ads AdPlexity could not attribute to a network are skipped);
   - only ads that had already been **running at least 3 days** when pulled;
   - **newest first**, stopping at the first ad already saved, within a **monthly AdPlexity credit budget** (about 1 credit per ad). `get_adplexity_overview` shows the budget and what was spent.
2. People browsing AdPlexity search with a browser extension that captures every search result they see and sends it to CK. These ads follow the searches people ran (any filters), cost no credits, and have no landing page link of their own (their Facebook page's link is used when known).

Ads whose caption (display link) is just facebook.com are skipped in both ways and deleted if already saved: they have no real destination to learn from.

So the store is a sample of qualifying ads, not every ad on the market. Only image ads are kept. An ad already saved is never updated. **Ads are deleted 30 days after they were saved.**

Shortly after an ad is saved, CK analyzes it: it reads the text written on the image (OCR), detects the language from all of the ad's text, and classifies its vertical from all of the ad's text. Until then `imageText`, `language` and `vertical` are empty; `get_adplexity_overview` shows how many ads still wait (`notAnalyzedAds`).

Each saved ad has:

| Field | Meaning |
|---|---|
| `adId` | AdPlexity id of the ad |
| `title` | the ad headline |
| `description` | the ad primary text |
| `caption` | the display link / domain shown on the ad |
| `imageText` | the text written on the ad image, read by OCR. Usually the strongest inspiration of all fields (see below). Empty when the image has no text |
| `language` | ISO 639-1 code (`EN`, `DE`) detected from the headline, primary text and image text together, not from the countries the ad runs in |
| `vertical` | the topic, classified from all of the ad's text, as an exact **Coinis vertical name**: Auto, Beauty, Education, Employment, Finance, Health, Home Improvement, Law, Lifestyle, Miscellaneous, Real Estate, Services, Shopping, Technology, Travel. `Unknown` when the classifier was not sure |
| `countries` | country codes where AdPlexity saw it |
| `networks` | arbitrage networks detected on its landing page |
| `daysRunning`, `firstSeen` | how long it had run when saved, and when AdPlexity first saw it |
| `isActive` | whether the Facebook ad was still active when saved |
| `facebookPageId`, `facebookPageName` | the page that runs it |
| `landingPageUrl` | the advertiser's article. Its path and query (slug, `adtitle=`) usually spell out the article title. Looked up once per Facebook page, so most ads carry their page's link (`linkFromPage: true`); a few have none yet |
| `imageUrl` | link of the ad image, only when the search passes `includeImageUrls: true` (our stored copy once the ad is analyzed, AdPlexity's link before that) |
| `usedForTitles` | this division already used it (see step 6). Other divisions track their own |

`daysRunning` and `isActive` are a snapshot from the day the ad was saved; ads are not refreshed later.

**Image text is the most important field, and it is not reliable.**
- On arbitrage ads the text on the image is practically the title of the article the ad sends to: the headline and primary text are often short or generic, while the image carries the real hook. Weigh it above the headline and primary text when you look for angles and write titles.
- It is machine-read (OCR), so it can be wrong: misread letters and words, words that are not on the image at all, random text picked from the background (signs, logos, product labels, watermarks), lines in the wrong order or cut in half.
- It holds everything written on the image, not only the hook. Find the main message (usually the biggest text, the first line or a question, e.g. `ROOF REPLACEMENT COST`) and treat the rest as decoration: lists of states, cities or brands, button text ("See Prices", "Learn More", "Click Here"), prices, arrows and labels. For example `ROOF REPLACEMENT COST Texas See Prices Florida See Prices California See Prices` is the topic "roof replacement cost"; the states and "See Prices" are layout, not the angle (the list of places only tells you the ad targets several regions).
- Use it for the idea, never as exact wording. Trust it when it reads as a coherent sentence and agrees with the headline, primary text or landing page slug; ignore fragments that make no sense with the rest of the ad.

The ad `vertical` is a Coinis vertical name, a fixed list shared by every division. It is **not** this division's vertical or theme (see below): use it to narrow the ads to a topic, then map each angle to this division's own vertical or theme yourself.

### The ad verticals (both sources)

Every ad of both sources gets one of these, picked by an AI classifier from all of the ad's text (headline, primary text, caption, image text) by what the person who clicks ultimately wants: an ad about SUV models is Auto, about a trip is Travel, about dental implants is Health.

| Vertical | Covers |
|---|---|
| Auto | cars and vehicles: new or used cars, SUVs, trucks, EVs, motorcycles, models, prices, leasing, parts, maintenance |
| Beauty | beauty and fashion: cosmetics, skincare, hair, makeup, clothes, shoes, fashion trends, beauty treatments |
| Education | schools, universities, degrees, online courses, certifications, scholarships, studying abroad, language learning |
| Employment | jobs, careers, wages and salaries, hiring, job types, where to apply, work abroad |
| Finance | loans, credit cards, banking, insurance, investing, crypto, mortgages as a financial product, debt, taxes, pensions |
| Health | medical treatments, hospitals, clinics, doctors, dental, medications, therapies, conditions, senior care, hearing, vision |
| Home Improvement | renovation, solar panels, roofing, windows, heating, DIY, furniture, appliances, gardening, contractors |
| Law | laws and regulations, legal rights, lawyers, lawsuits, claims, compensation, immigration law |
| Lifestyle | fitness, yoga, coaching, hobbies, food, dating, pets, wellness, leisure activities |
| Real Estate | homes and apartments for sale or rent, property prices, neighbourhoods, housing markets |
| Services | local or online services: cleaning, moving, repairs, internet and phone plans, delivery, storage, pest control |
| Shopping | products to buy, consumer goods, electronics as purchases, online shopping, product comparisons, marketplaces |
| Technology | software, apps, gadgets, phones, computers, AI tools, internet, cybersecurity, tech how-tos |
| Travel | destinations, trips, holidays, cruises, flights, hotels, tours, tickets, travel packages |
| Miscellaneous | nothing else clearly fits |
| Unknown | the classifier's top pick was too weak to trust |

How to use them:
- Neighbours overlap (Services / Home Improvement, Finance / Real Estate for mortgages, Shopping / Technology for gadgets). When a topic sits on a border, filter with both verticals, or use `text` instead.
- `Unknown` and `Miscellaneous` ads are not junk: search them with `text` when a topic doesn't fit the list.
- An ad is classified once, shortly after it is saved, and never re-classified.
- Map to this division: a division vertical or theme (`get_verticals`, for example `Sale` or `Jobs`) is the division's own topic and has no Coinis name in the tool output. Pick the one or two ad verticals that cover it by the table above (e.g. a `Jobs` vertical ⇒ `Employment`; a `Solar` theme ⇒ `Home Improvement`), and narrow further with `text` when the theme is a small part of the vertical.

## Second source: the Facebook ad library scrape

CK also scrapes the public Facebook ad library itself, for competitor pages people chose to follow.
- Pages are organized in **scrape groups**: a named competitor or competitor type (for example one arbitrage network's advertisers). A page belongs to one group only.
- Each followed page is scraped about once a day at most, a few screens of its active ads, most-shown first. Pages whose last scrape found no new ads are scraped less often. A page with no active ads is paused (keeps its ads, not scraped).
- People can also scrape a landing domain by hand: its ads come in, and unknown pages running them are added to the group.
- Only **image ads** are kept (carousels keep the first card's image); video ads and product-catalog ads are skipped.
- An ad is saved once, the first time it is seen, and never updated. Ads are kept until their page is disabled; there is no 30-day limit.
- The image is copied when the ad is saved, then the same analysis as for AdPlexity runs: `imageText` (OCR), `language`, `vertical` (Coinis name). The image text rules above apply the same way.

Differences from AdPlexity:
- **No countries** and no arbitrage network per ad: use `language` for the market and the scrape group for the competitor.
- `startDate` / `daysRunning` come from Facebook (when the ad started), `copies` is how many copies of the same ad Facebook groups together (many copies = the advertiser is scaling it).
- `landingPageUrl` and `domain` are the ad's own link.

Fields of a scraped ad: `adId` (Facebook ad library id), `title`, `body`, `caption`, `imageText`, `language`, `vertical`, `startDate`, `daysRunning`, `copies`, `savedDate`, `scrapeGroup`, `facebookPageId`, `facebookPageName`, `landingPageUrl`, `domain`, `imageUrl` (only with `includeImageUrls: true`, our stored copy), `usedForTitles`.

## Tools

- `get_adplexity_overview`: totals, ads not yet used by this division, first-seen date range, ads per network, per country, per vertical and per language, ads not analyzed yet, credit budget. Call it first.
- `search_adplexity_ads`: the ads. Filters (all optional, combined with AND):
  - `countries`: any of the codes, e.g. `["US","GB"]`;
  - `networks`: any of the names, partial and case insensitive, e.g. `["Tonic"]`;
  - `text`: searched in title, description, image text, caption and page name;
  - `languages`: any of the language codes, e.g. `["DE"]` (the ad's own language, a stronger signal than `countries` for which market the copy is written for);
  - `verticals`: any of the Coinis vertical names, exact, e.g. `["Home Improvement", "Finance"]`;
  - `facebookPageId`: one page's ads;
  - `minDaysRunning`: only ads that ran at least N days;
  - `firstSeenInLastDays`: only recent ads;
  - `unusedOnly`: skip ads this division already used;
  - `orderBy`: `newest` (default) or `longest`;
  - `maxResults` (default 50, max 200) and `skip` for paging;
  - `includeImageUrls`: `true` adds `imageUrl` to every ad. Off by default to keep results small; turn it on only when the images will be looked at (for example as references for an image prompt).
- `list_adplexity_pages`: Facebook pages by number of saved ads, with the site they send to. Filters: `text` (page name or site), `minAds`.
- `mark_adplexity_ads_used`: marks ads as used by this division, with a note (reference or tag).

Facebook ad library scrape:
- `get_facebook_scrape_overview`: totals, ads not yet used by this division, saved date range, scrape groups (id, name, description, active and paused pages, ads), ads per vertical, per language and per landing domain, ads not analyzed yet. Call it first.
- `search_facebook_scrape_ads`: the ads. Filters (all optional, combined with AND):
  - `scrapeGroupIds`: any of the group ids from the overview;
  - `text`: searched in title, body, image text, caption and page name;
  - `languages`, `verticals`: as for AdPlexity;
  - `facebookPageId`: one page's ads; `domain`: one landing domain;
  - `minDaysRunning`: only ads running at least N days (from their start date);
  - `savedInLastDays`: only recently saved ads;
  - `unusedOnly`: skip ads this division already used;
  - `orderBy`: `newest` (default), `longest` (earliest start first) or `copies` (most copies first);
  - `maxResults` (default 50, max 200) and `skip` for paging;
  - `includeImageUrls`: as for AdPlexity.
- `list_facebook_scrape_pages`: followed pages by number of saved ads, with group, status, last scrape and new ads found by it. Filters: `scrapeGroupId`, `text`, `minAds`, `includeInactive`.
- `mark_facebook_scrape_ads_used`: marks scraped ads as used by this division, with a note. Ad ids of the two sources are different: mark each ad with the tool of its own source.

All these tools only read (except the two mark tools, which only record usage). Adding pages, groups or domain scrapes is done by people in CK.

Pull in pages of 50 to 100 and summarise; never dump hundreds of ads into the chat.

## Shared memory

If the `memory_*` tools are available (see the **arbo-memory** skill): at the start call `memory_briefing` with your agent name and `scopeLinks` for the verticals/countries you will touch, follow active objectives (new titles fall under `new-titles`), and read the journal so you don't repeat another agent's titles. At the end, after a submit, write one `Journal` entry (count, verticals, countries, reference or tag); for a generation launch also a review `Task` about 3 days out, linked to the tag.

**Verticals and themes.** These are the same thing: the topic a title, article and adset belongs to. They are split into two kinds only for legacy reasons.
- A **vertical** is top level (`isTopLevel: true` in `get_verticals`), for example `Sale` or `Jobs`.
- A **theme** (`isTopLevel: false`) is a child of exactly one vertical, named in `parentVertical`. It narrows that vertical and can never go beyond its scope.
- Wherever a vertical name is asked for, a theme name works the same way: in title payloads, in the stats, and as `Vertical.Name` in queries. Names are unique across both kinds. Prefer the most specific entry that fits.
- In rare cases nothing fits. Don't force the closest vertical. Say so, and recommend a new top-level vertical with a PascalCase name and a one-sentence description. The user adds verticals by hand in CK. New themes are created with `create_theme`, only when the user explicitly asks.

## 1. Scope

Ask (or take from the request) which countries, languages, verticals or networks to look at. Default: the countries this division spends in (one stats query, see step 3) and `unusedOnly: true`.

## 2. Find the angles

1. `get_adplexity_overview` to see which networks and countries have data, and `get_facebook_scrape_overview` to see which scrape groups, languages and verticals have data. Use both sources unless the user names one.
2. `search_adplexity_ads` for the scope, `minDaysRunning: 5` or more and `orderBy: "longest"` first: ads that keep running are the ones paying. Then a `newest` pass for fresh angles. For a topic, filter with `verticals` (Coinis names); for a market, combine `countries` with `languages`.
3. Signals, strongest first:
   - **the same article or angle run as many ads, by several pages or in several countries;**
   - a page with many saved ads (`list_adplexity_pages`) is scaling: look at its ads;
   - high `daysRunning`, still `isActive`;
   - in the Facebook scrape: many `copies`, a long `daysRunning`, the same angle across pages of a group (`orderBy: "copies"` or `"longest"`).
4. For each angle note: the topic, the hook (what's replacing X, warning signs, how much it costs, what it may look like in 2027, a named city or public programme...), the markets, and what makes it concrete. Start from the `imageText`: it is usually the article title behind the ad, so it weighs more than the headline (skip it when it is garbled or random, see above). The landing page slug confirms it.
5. Map each angle to the most specific vertical or theme of this division (`get_verticals`). Note angles that fit no vertical, and sub-topics that are being scaled inside a vertical but that none of its themes covers. Propose those separately (parent vertical, PascalCase name, one or two sentence description, evidence); create a theme only when the user explicitly asks.

## 3. Check against the division

Only bring angles we don't already run:
- Where it spends: one stats query (arbo-stat-queries skill) grouping 14 days by `Vertical.Name` and `Country` with spend and ROI. Place titles in verticals × countries that perform.
- Overlap: one query over 30 days matching each candidate angle as a regex on `Title` (all verticals), returning count, spend, ROI and two sample titles per angle. Skip angles already well covered; treat an angle that clearly lost for us as weak evidence when it only spent a few dollars.

## 4. Write titles

Follow **all** rules of the **arbo-title-creator** skill (hard rules, intellectual property, production-ready language, years, self-check). These rules are absolute, even when the AdPlexity ad breaks them:
- **Neutral third-party voice: no seller offers, no promises.** Every title is the headline of an independent informational article. We do not sell, ship, finance, book or provide anything. In any language, never:
  - speak as the seller or provider: "we", "our", "us", "my", "shop our", "we offer", "buy from us", "official sale";
  - mention a condition only a seller can give: free delivery or shipping, 0% financing, free returns, a warranty, promo codes, "in stock", free trial, "purchase conditions";
  - promise anything: guaranteed results or approval, savings, a price or availability the reader will get;
  - tell the reader to buy: "buy", "order", "shop", "book now", "apply now".

  Something free or covered by a public service or insurance ("Free eye tests on the NHS") is fine.
- **Finance topics, never loan offers.** Loans and credit are allowed as informational articles, never with an amount, duration, repayment term or rate.
- **Never name** a bank or other financial institution, a store, retailer or marketplace, a fashion or cosmetics brand, or a service chain. Use the generic subject.
- **No demographic targeting** ("over 60", "for seniors", ...), even though arbitrage ads use it constantly. Keep the subject, drop the audience.
- No prescription drugs, no emojis, no exclamation marks, no ALL-CAPS words.

AdPlexity copy is evidence of the angle, never text to copy. Rewrite every title in your own words, localise it to the target country and language with real local values, and spread the set across verticals and countries.

**Separate primary text (only when the user asks for it).** Then each title gets a `PrimaryText` (with `PrimaryTextInEnglish`) for the ad image. Follow the "Primary text" section of arbo-title-creator. These are hard rules:
- **Both from one ad.** The title is written from that ad's headline, `title` (from its `description`/`body` only when it has no headline), the primary text from the text on the same ad's image, `imageText`. Never combine texts of different ads. Keep the source ad id with every pair.
- **They must never differ in subject**: same topic, product or service, and place. The primary text never mentions anything the article named by the title would not cover. Read the primary text and then the title: one ad leading to one article.
- The ad has no text on its image, or the image hook doesn't fit the title: leave the primary text empty (the title then goes on the image). Never invent a hook.
- Image texts are full of seller offers, prices and calls to buy: keep only the hook, under the same hard rules as the title. Never copy it word for word.

Add a primary text column (native and English) to the table.

Show a table: #, vertical, country, title, English, source (AdPlexity or Facebook scrape, adIds, page, days running). Let the user drop or change rows.

## 5. Submit (only on the user's explicit go)

- **Default: recommendations.** `set_new_article_titles` with `referenceName: "claude-adplexity"`, unless the user names another reference. No money is spent; the automatic pipeline picks them up when the country × vertical performs.
- **Generation only when the user explicitly asks** to launch / generate ads: `submit_titles_for_generation`. It creates real articles and adsets that spend budget: say so once, and follow arbo-title-creator step 7 (affiliate for every title from `get_affiliate_providers`, never guessed; tag suggested as `t:adplexity-YYYYMMDD`; budget, cap, account, image prompt and search query only if the user gives them). Show the final list with affiliate and tag and get a clear yes.
- With a separate primary text, pass `PrimaryText` and `PrimaryTextInEnglish` on each title in either tool (both or neither).
- One invalid row rejects the whole batch: validate vertical names, country and language codes first. Titles failing the banned-word, brand or length checks are inserted and listed with a reason: the article keeps the title, and the ad image and ad texts get a compliant rewrite on import. Still write compliant titles yourself.

## 6. Mark the source ads

Right after a successful submit, call `mark_adplexity_ads_used` (AdPlexity ads) and `mark_facebook_scrape_ads_used` (scraped ads) with the adIds behind the accepted titles (leave out skipped ones) and a note with the reference or tag. Later runs with `unusedOnly: true` then bring only new material. Marking is per division; it never hides ads from other divisions.

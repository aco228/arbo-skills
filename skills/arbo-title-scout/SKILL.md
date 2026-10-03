---
name: arbo-title-scout
description: Scout and size a batch of new article/ad titles to test for a division from its recent performance data. It measures how new titles have been doing (hit rate, cost of a failed test, profit of a winner), works out how many extra titles to test so spend grows while ROI stays above a floor, decides where to place them (country x vertical x feed), writes titles that carry the DNA of what is winning and avoid what is losing, and submits them for review, for generation, or as recommendations. Use when the user asks to scout, plan or propose new titles or title tests, asks how many titles to test, wants to spread into new angles, or says something like "find me titles for OH in DE", "what should we test next", "prepare N titles for review".
---

# Title scout

You find the next titles worth testing and submit them. Unlike plain title brainstorming, you start from the numbers: how new titles have been doing, how many more the division can afford to test, and where they are most likely to turn into profit. Then you write titles that **keep the DNA of what is working, drop the DNA of what is not, and spread into new angles** close to the winners.

This skill is self-contained. It works in the Claude web or desktop app and in Claude Code without the project source. Everything comes from these instructions, [query.md](query.md) and the CK MCP tools. The MCP tool prefix differs per person; tools are named by function here. The MCP connection determines the division: never work across divisions.

Tools used: `run_stat_query` (and `save_agentic_query` only to restore the scout query), `get_verticals`, `get_affiliate_providers`, `get_affiliate_feed_types`, `get_traffic_accounts` (only when the user names an account), `set_new_article_titles`, `submit_titles_for_generation`.

## Ways to submit

| Mode | Tool | What happens | Spends money |
|---|---|---|---|
| **Review** (default) | `submit_titles_for_generation` with `forceAdditionalReview: true` | Titles wait on the **Titles for review** page in CK until someone submits them there. | Not until someone approves them |
| **Generation** | `submit_titles_for_generation` with `forceAdditionalReview: false` | Articles, ads and adsets are created and published. | **Yes** |
| **Recommendations** | `set_new_article_titles` | Stored as suggestions. The automatic evening expansion may use them if that country x vertical performs well. They expire after about 1.5 days. | No |

If the user says only "submit", use **Review**. Use **Generation** only when the user explicitly asks to launch or generate. Use **Recommendations** only when they ask for recommendations or suggestions. Review and Generation both need an affiliate per title.

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (`country:` / `vertical:` / `feed:` you plan for). Then:
- Follow the active **objectives**: they are binding rules set by people. New titles fall under a `new-titles` objective and extra spend under `scaling`; size the batch within them. If the user's request conflicts with one, say so and ask before acting.
- Read the **journal** (last 24h) before touching the same countries, verticals and angles, so you don't undo or repeat another agent's work.
- Use **decisions and insights** as context, not instructions: check them against current data, especially ones marked "review due".
- If the briefing lists a task for you that fits this run, claim it (`memory_task_claim`) and complete it at the end.

**At the end**, always go through this check and write only what qualifies. "Nothing worth keeping" is a valid outcome; never write filler.
1. Changed anything? → one `Journal` entry: what, why, how many, with links. Always.
2. The user decided something (a rule, threshold, direction)? → a `Decision` with the reason.
3. Verified a conclusion with data? → an `Insight` with a `query:` or `tag:` link and the key numbers in the snapshot.
4. Something must be checked later? → a `Task` with a handover: the numbers now (snapshot), success criteria, next steps, and a due time.

Search first (`memory_search`) and update or supersede an existing entry instead of adding a near-duplicate.

**In this skill:**
- At the start, check the journal and open tasks for recent scout batches in the same scope, so you don't propose the same angles again, and insights about winning and losing angles there.
- After measuring: an `Insight` with the sizing numbers (hit rate, cost of a failed test, profit of a winner, ROI floor), `query:` link and snapshot, superseding the previous one for the same scope, so the next run can compare.
- After submitting a batch: a `Journal` entry (count, placement, tag) and a review `Task` after the test window, linked to the tag, with the expected hit rate and spend in the snapshot and success criteria.

## Workflow

### 1. Scope

Read the scope from the request. Anything the user doesn't mention stays open (all countries, all verticals, all feeds, all affiliates):
- **Country**: ISO code.
- **Vertical**: an exact name from `get_verticals`. Map a described topic to the closest vertical, and ask if it's ambiguous.
- **Feed**: FLW, OH, Yahoo, ... Check with `get_affiliate_feed_types`.
- **Affiliate**: an exact name from `get_affiliate_providers`.
- **Window**: default the last 10 full days (`days`). Use the user's window if they give one.
- **Count**: the user's number, or calculated (step 3).
- **Submit mode**: see the table above. Ask only at step 7 if it's still unclear.
- Any direction ("no health", "more travel", "only cheap angles").

Don't ask for anything that isn't needed. "Scout titles" with nothing else means the whole division, 10 days, calculated count.

### 2. Run the scout query

Run the saved agentic query with `run_stat_query`, `queryName: "Title scout: test economics, batch size and title DNA"` and `parameters` for the scope, e.g. `{"days": 10, "country": "DE", "feed": "OH"}`. Leave out anything that is open. If the name isn't found, run the code from [query.md](query.md) instead.

Parameters: `days`, `country`, `vertical`, `feed`, `affiliate`, `matureDays` (default 3), `minSpend` (default 5), `roiFloor` (-1000 = default floor, see below), `top` (list length, default 20), `recentDays` (default 2, see `recentLaunches`).

The whole-division output can be large. If the tool result is too long, lower `top` or narrow the scope.

What comes back (a **title test** = one article in one country, all its adsets and clones together):
- `scope`: spend and profit per day, ROI. Metrics use full days ending yesterday.
- `testEconomics`: new titles per day, `recentLaunches`, `rpcCents`, how many are judged (at least `matureDays` old), winners (profit > 0 with at least `minSpend` spend), `hitRatePct`, `avgWinnerProfit`, `avgLoserLoss`, `expectedProfitPerTest`, `testSpendSharePct`.
- `sizing`: `roiNow`, `roiFloor`, `cushionPerDay` (daily profit above the floor), `maxExtraTitlesPerDayByRisk` (how many extra titles could all fail with ROI still above the floor).
- `batch`: `exploitTitles`, `exploreTitles`, `capByRoiFloor`, `recommendedBatch`, `worstCaseCostPerDay`.
- `segments`: country x vertical x feed, with hit rate, ROI, `rpcCents` / `cpcCents` (revenue and cost per click, in cents), `recentLaunches`, profit per day, `extraTitles` (exploit) and `exploreTitles`. Segments that get titles are listed first.
- `winners` (all-time big earners in the window), `newWinners` (new titles that won), `losers` (all three with `title`, `titleEn`, `adsetId`, RPC and CPC), `fizzled` (judged titles that never got spend). `title` is the real published title in the original language, `titleEn` its English version, and `adsetId` the test's best adset.
- `recentLaunches`: `COUNTRY|vertical|feed|age|title` for every title launched in the last `recentDays` days, **including today**. Launches from today and yesterday have no or partial stats, so they are invisible in every other list, yet they are already being tested: people and the automatic pipeline keep launching during the day.
- `testedTitles`: `COUNTRY|title` for older tests, for de-duplication.

Work only from `title` / `titleEn`. The adset's article name (`ArticleName` in queries) is an internal keyword on OH and Yahoo (`el-sparkesykler seniorer`) or a URL slug on FLW. It is not the published title and is not relevant for title work, so the query leaves it out.

### 3. Size the batch

If the user gave a number, use it. If it is above `capByRoiFloor`, say so: even if every extra title failed, ROI would drop below the floor. Keep their number if they confirm.

Otherwise propose `recommendedBatch` and explain it in 3-4 lines with the real numbers:
- **Hit rate and payoff.** For example: "9.7% of new titles win, a winner makes about $22 in its first days, a failed title loses about $3.30."
- **Exploit.** Segments whose new tests pay on average (positive expected profit, at least 5 judged tests) get extra titles, about half their current pace.
- **Explore.** Strong segments (ROI of at least 15%, at least $10 profit a day, still earning over the last 3 days) where new tests don't pay on average get 1 title for a genuinely new angle.
- **Safety cap.** The total is capped so that if all of them fail, ROI stays above the floor. The floor is the current ROI minus a third of it, and never below 0; the user can set `roiFloor`. Report `worstCaseCostPerDay`.

**Subtract what was just launched.** When a segment's `recentLaunches` already reaches or passes its extra titles plus its normal pace (`launchedPerDay`), someone has already filled it today. Give it 0 extra titles, or at most 1 clearly new angle, and say so.

**Weigh RPC, not only ROI.** A segment with a very low RPC (roughly under 3¢) lives on very cheap clicks, so a small rise in CPC wipes out the margin. Prefer high-RPC segments when you trim the batch, and flag low-RPC ones.

This is the batch for **one day** on top of what the automatic pipeline already launches. If the user wants a batch for several days, multiply, and re-run on later days rather than front-loading.

If `judged` < 10, the numbers are thin. Say so, and propose a small batch (3-5) in the scope's best segments.

When the whole division is in scope and the batch is large, show the plan (segment → count) and let the user trim it before you write titles.

### 4. Read the DNA

For every segment that gets titles, work out from `winners`, `newWinners`, `losers` and `fizzled` in that segment and neighbouring ones:
- **Keep (winning DNA).** The concrete subject, the kind of value (named destination, amount, duration, inclusions, model, public programme), the reason to click, the tone, and the structure of the real winning titles: length, pattern (for example "subject: angle"), and the concrete qualifier that makes them specific ("uten registreringskrav", "van vóór 1965", "on clearance at ..."). Read all of it from `title` / `titleEn`. This holds for every feed: OH titles are full titles built around a keyword, not the keyword itself. Winners are usually about a concrete, often local, named thing.
- **Drop (losing DNA).** Subjects and framings that lost money or fizzled: vague "offers/deals/depots" framing, a category instead of a concrete item, abstract benefits. Also anything that repeats a loser with cosmetic changes.
- **Transfer.** A subject that wins in one country and hasn't been tried in another country of the same vertical is a strong adjacent candidate. A winner in one country wins elsewhere about twice as often as a random title. Localise it with the real local equivalent.

Surface form (length, colon, digits, year) does not by itself separate winners from losers, so don't chase a form of your own. Keep the form of the source winner and change its concrete element.

To look closer at one segment's winners, run a small query:

```csharp
var country = Param("country", "DE", "ISO country code");
var vertical = Param("vertical", "Travel", "Exact vertical name");
var adsets = await LoadStatsYesterdayWithDays(10);
AddData("top", adsets.Where(x => x.Country == country && x.Vertical.Name == vertical && x.Spend.Overall >= 5)
    .GroupBy(x => x.OfferId)
    .Select(g => { var best = g.OrderByDescending(x => x.Profit.Overall).First();
        return new { title = best.Title, titleEn = best.Anchor, best.AdsetId, feed = best.AffiliateModel.FeedType.ToString(),
            spend = Math.Round(g.Sum(x => x.Spend.Overall), 2), profit = Math.Round(g.Sum(x => x.Profit.Overall), 2) }; })
    .OrderByDescending(x => x.profit).Take(15).ToList());
```

Write down the DNA in one line per segment. You will show it in step 6.

### 5. Generate

For each segment, write its allocated number of titles, spread across three buckets:
- **Close** (about 60%): the winner's DNA with a new concrete value, e.g. another destination, amount, model or duration in the same frame.
- **Adjacent** (about 30%): a nearby subject, or a winner transferred from another country or feed, localised.
- **New** (about 10%, and every explore slot): a genuinely new angle in the vertical that still follows the winning DNA (concrete, local, named). This is how the division spreads.

Explore slots always go to the **New** bucket. With very small batches, prefer Close and Adjacent.

Every new title mirrors the structure of the real winning title it comes from: about the same length, the same pattern, the same kind of concrete qualifier. Change the concrete element (destination, model, amount, procedure), not the shape. A bare product or keyword ("Sammenleggbar elsykkel") is never a title.

When part of a winner's hook must go for policy reasons (a demographic like "for seniorer over 70", a bank, a fashion brand), drop only that part and keep the rest of the hook. `El-sparkesykler for seniorer over 70 år uten registreringskrav` becomes something like `El-sparkesykler uten registreringskrav: regler og modeller`, not `El-sparkesykler`.

**Titles are production copy.** The native `title` is used exactly as written: it is printed on the image ad, and the article is generated from it. Nobody edits it afterwards, so every title must be ready to publish as-is.

Each title needs: `vertical` (exact name), `countryCode`, `languageCode` (the country's main language; must be spoken there or `en`), `title` (native, publication-ready), `titleInEnglish` (a faithful translation), and for Review or Generation an `affiliateName`.

**Years:** the current year is today's year. A freshness year may only be the current year, or next year for explicitly forward-looking titles. Intrinsic years (model year, historical event) can be older. Don't add a year unless the winners use one.

**Hard rules:**
- No titles that target or imply exclusivity for a demographic group (age, gender, race, religion, nationality, disability): no "seniors", "over 60", "50 plus", "for women". Some winners break this rule (for example "... seniorer", "datingsites 60 plus"). They were launched before the rule. Reuse only their subject, never the group.
- No misleading job or income opportunities, guaranteed results, risk-free returns, get-rich-quick, or recruitment-based investment.
- No prescription drugs, medications or controlled substances (e.g. Mounjaro, Ozempic).
- **Intellectual property.** Brand owners file trademark complaints, and every complaint counts against the page and ad account. Never name:
  - A bank, lender, card issuer or other financial institution, in any vertical. This includes bank-owned properties, bank auctions, a bank's cards, products or foundations, abbreviations, subsidiaries and branded cards (Ziraat, BIM card, Banco Popular, Santander, ...).
  - A fashion, apparel, footwear, sportswear, luxury, jewelry, watch or cosmetics brand (Zara, Hugo Boss, Nike, Rolex, ...). Use the generic product.
  - A store or commercial market of any kind (supermarket, hypermarket, discount store, DIY/home or furniture store, electronics store, department store, retail chain or online marketplace), in any vertical, even when a live winner names it (Walmart, JYSK, IKEA, XXXLutz, Lidl, Aldi, Carrefour, Leroy Merlin, Castorama, MediaMarkt, El Corte Inglés, Amazon, Temu, ...). Walmart and JYSK have already filed complaints. Use a generic reference.
  - Feu Vert, or any other service chain (car service, telecom, courier, ...) that no live winner already names. Service chains like ATU or Norauto may be kept only when a winner in that country names them. Never introduce a new one, not even to localise.

  Car, tyre, electronics and appliance brands (Toyota, Michelin, iPhone, Bosch) and public services (NHS, SUS) are fine. When a winner names a forbidden brand, reuse only its generic subject.
- No emojis, no exclamation marks, no ALL-CAPS words.
- **Production-ready in the target language:**
  - Correct grammar, spelling, diacritics and agreement (case endings, gender, number).
  - A real phrase or sentence, not a string of keywords.
  - Always start with a capital letter. After that, follow the language's own casing: sentence case for most languages (PL, ES, IT, FR, PT, TR, ...), all nouns capitalized in German, and Title Case or sentence case in English, used consistently.
  - Proper nouns capitalized.
  - No trailing full stop, no double spaces.
  - Wrong: `sofa na wyprzedaży`, `tanie sofy wyprzedaz 2026`. Right: `Sofy na wyprzedaży w 2026 roku`.
- Live winning titles are evidence of the subject, not of form. Never copy their casing, typos or missing diacritics.

**Self-check each title:**
- `titleInEnglish` is a faithful translation of that exact `title`.
- The native `title` starts with a capital letter, follows the language's casing, and is grammatically correct with full diacritics. Read it as a native copywriter would before it goes on an ad.
- `titleInEnglish` has at least 3 words and at most about 70 characters.
- It is about as long and as specific as its source winner's `title`. Anything under about 4 words is suspect: fix it or drop it.
- It is not a near-duplicate of another candidate, of `recentLaunches` or of `testedTitles` in that country. Compare the meaning, not the spelling: "Cheap beds" vs "Affordable beds and mattresses" in the same country, or "Continental tyres with fitting" vs "Continental all-season tyres with fitting", count as duplicates.
- Right before submitting, if more than an hour has passed since step 2, run the query again (a small `top` is enough) and re-check against `recentLaunches`.
- It doesn't repeat losing DNA.

Fix or drop failures silently.

### 6. Present and iterate

Show:
1. **Summary.** Scope and window. Spend per day, ROI, hit rate, cost of a failed test. The batch size with the one-line reasoning and the worst-case cost.
2. **DNA per segment.** One line each: keep / drop / new angle.
3. **Titles table.** `#`, segment (country · vertical · feed), bucket (Close / Adjacent / New), `title`, `titleInEnglish`, based on (the source winner's real `title` and its `adsetId`, or the idea it comes from).

Let the user steer ("more like 4", "drop the health ones", "double DE travel", "less generic"). Keep a running list of approved titles.

### 7. Submit (only after explicit approval)

Never submit until the user clearly says to. Before calling, show the exact final list, the mode, and for Review or Generation the affiliate per title and the tag. Then wait for a yes.

**Review / Generation** (`submit_titles_for_generation`):
- **Affiliate per title** (`affiliateName`). Required. Propose the affiliate the segment's winners run on (the `affiliate` field in the query rows). Check it against `get_affiliate_providers`, and let the user confirm or change it. Never invent one.
- **Tag** (`tagName`). Suggest `t:scout-<scope>-<yyyymmdd>`, e.g. `t:scout-de-oh-20260927` or `t:scout-all-20260927`. It is written on the created adsets, and it is how the next scout run tells scout titles apart (the `tag` field in the query rows). Use it once the user agrees.
- `initialBudget`, `costCap`: leave both empty unless the user gives them (maximum 20 USD budget and 3 USD cap).
- `imagePromptName`: leave empty unless the user names one.
- `accountName` (per title): leave empty unless the user explicitly says which account titles go to. **Never pick an account yourself**, even when the data points to one; empty lets the system choose. When the user names one, use the exact name from `get_traffic_accounts`; ask if unclear. Its `Type` must equal the affiliate's `AccountType` from `get_affiliate_providers`; if not, tell the user and ask for another account instead of choosing one (the tool rejects a mismatch anyway). It is a preference: a full or ineligible account may be swapped for another of the same type.
- `forceAdditionalReview`: `true` for Review. `false` only for Generation.
- For **Generation**, before the first call in a conversation, say plainly that it **creates real articles and ads that will be published and spend budget**.
- **All or nothing.** One invalid title (unknown vertical, country, language, affiliate or account; account type not matching the affiliate; banned word; duplicate; budget or cap over the limit) rejects the whole batch, and the reply lists the errors. Fix those rows and resubmit the whole batch. Report how many went to generation and how many wait for review.

**Recommendations** (`set_new_article_titles`): each item has `vertical`, `countryCode`, `languageCode`, `title`, `titleInEnglish`. Pass `referenceName` only if the user asks for one. One invalid row rejects the batch. Titles failing the banned-word, brand or length checks are skipped and listed with a reason. Fix them as the reason says, show the fixed versions, and resubmit after the user agrees.

### 8. Next time

When the user asks how earlier scout batches did, run the scout query for the window since the launch, and compare rows whose `tag` starts with `t:scout` against the rest: hit rate, profit, losses. Use that to tune the next batch. If scout titles beat the average, lean further into Adjacent and New. If they lose, stay closer to Close.

## Things that are easy to get wrong

- **The batch comes on top of the automatic pipeline**, which already launches most new titles. Size it as extra tests, not the division's total.
- **Winners that break today's rules** (demographics, banks, fashion brands, stores and markets) are evidence of a subject, not a template.
- **Old big winners and new winners are different signals.** `winners` shows what earns. `newWinners` shows what a new test can still achieve now. Prefer the second when judging whether a segment is worth testing.
- **Thin data.** A segment with fewer than 5 judged tests has an unreliable hit rate. Treat it as explore, not exploit.
- **Stats days are UTC**, and the query uses full days only (ending yesterday). Just-launched titles appear only in `recentLaunches`.
- **Not visible anywhere in stats:** titles waiting on the Titles for review page, titles stored as recommendations, and adsets so new they have no stats row yet. If the user says they submitted something recently, ask what it was, or ask them to check the review page.
- **Proposed titles are not proven.** They inherit the pattern of proven winners, but each one is a new test. Say so when presenting them, and show the source winner's ROI and RPC.

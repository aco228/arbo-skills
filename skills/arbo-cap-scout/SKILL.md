---
name: arbo-cap-scout
description: Find test adsets that have proven themselves and clone them into cost cap adsets, quickly and safely. It studies how past cost cap clones turned out to calibrate the thresholds (profit, ROI, conversions, RPC) and the cap, then scans today's active uncapped adsets, applies the clone rules (last cap clone, cap adsets of the offer per account and per country), suggests a cap per adset from its RPC, and submits the approved ones with submit_adset_clones_with_cap / submit_adset_clones_with_cap_and_budget. Use when the user asks to find cost cap candidates or winners to scale, to clone winners into cost cap, to "promote" test adsets, to check which adsets are ready for a cap, or to review how earlier cap clones did.
---

# Cap scout

Cost cap adsets carry much of the profit. The flow is: a new title launches as an adset with a small budget; when it proves itself, it is **cloned into a cost cap adset** with a real daily budget. You do the "when it proves itself" part: read the numbers, find the real winners early, set a good cap, and submit the clones before the moment passes.

A cap clone only makes money if two things hold:
1. **The RPC is real.** The source has enough conversions that its revenue per conversion is not noise, and it isn't collapsing.
2. **The cap sits under that RPC, but not too far under.** Facebook pays at most the cap per conversion, so cap < RPC protects the margin. A cap far below RPC doesn't deliver at all: the clone never spends and is wasted.

This skill is self-contained. It works in the Claude web or desktop app and in Claude Code without the project source. Everything comes from these instructions, [queries.md](queries.md) and the CK MCP tools. The tool prefix differs per person, so tools are named by function. The MCP connection determines the division: never work across divisions.

Tools used: `run_stat_query` (plus `save_agentic_query` only to restore a missing query), `list_pending_adset_actions`, `submit_adset_clones_with_cap`, `submit_adset_clones_with_cap_and_budget`, and optionally `get_adset_details`.

## Terms and units

- **RPC** here = revenue per **conversion**, in cents (`PricePerConversion`). The cost cap is also per conversion, so this is the number the cap is compared with. It is not revenue per click.
- **Cap** is in **cents** (45 = 0.45 USD, allowed 2 to 350). **Budget** is in **USD** (1.5 to 70 for a clone).
- **Source** = the uncapped adset being cloned. **Clone** = the new cost cap adset. The clone goes into the same ad account as the source.
- Stats days are **UTC**. Today is partial. `LocalHour` says how far the country's own day is.

## The clone rules (from the user; apply them always)

1. **Last cap clone.** `LastCloneCapUtcHours` is the number of **days** (despite the name) since a cap clone of this adset was last started. It is set even when the clone never finished (Facebook rejected it, it is still pending, or it never delivered). Don't clone an adset whose last cap clone is younger than the cooldown (default 7 days). If it is recent and no cap adset of the offer is visible, **the earlier clone is pending or failed**: report it, don't clone again.
2. **One cap per offer per account.** If the offer already has a cap adset in the **same ad account** (`OfferCountWithCapAccount` ≥ 1), don't make another one.
3. **At most 3 per offer.** If the offer already has **more than 3** cap adsets in the country across all accounts (`OfferCountWithCap` > 3), skip it.
4. **Cap = RPC − 5 cents** by default, with a floor from the study (see below) so the cap isn't set where clones don't deliver.
5. **Clone budget = 50 USD a day** by default. That is what `submit_adset_clones_with_cap` uses.

The offer counts cover cap adsets seen in the last 6 days, **killed ones included**. A cap that was tried and killed still counts. That is deliberate.

The candidates query applies rules 1 to 4 for you. The thresholds (how much profit, ROI and conversions make a clear signal) are **not fixed**: take them from the study in step 2.

## Workflow

### 1. Scope

Default: the whole division, today. The user can narrow it by country (`country`) or feed (`feed`), or give their own thresholds, cap margin, budget or cooldown. Don't ask for anything that isn't needed. "Find cap candidates" means go.

### 2. Calibrate with the study

Run the saved query with `run_stat_query`, `queryName: "Cap scout: study of past cap clones"`. Default parameters are fine (`days` 30). Add `feed` when the scope is one feed. If the name isn't found, run the study code from [queries.md](queries.md). The query takes about a minute.

It judges every cap clone at least 3 days old against what its source showed on the day of cloning. Each table row has `n`, `winPct` (clone profit > 0), `deliverPct` (clone spent at least 5$), `roi`, `profitPerClone`, `profitPerCloneDay` and `bigWinPct` (clone made ≥ 50$).

Read it like this and choose the parameters for step 3:
- **`minProfit` / `minRoi`.** In `bySourceDayProfit` and `bySourceDayRoi`, find where `winPct`, `deliverPct` and `profitPerCloneDay` jump. Pick the lowest band that is clearly good, not the best tiny band. The `strong...` tables show sources above `strongProfit` / `strongRoi` (10$ / 50% by default). Re-run with other values if the jump is elsewhere.
- **`minConv`.** Use `strongByConversions`. More conversions is not automatically better: very high counts often mean a cheap, low-RPC offer. Pick the level above which outcomes stop being erratic, usually 10 to 20.
- **`minRpc`.** Use `byRpc` / `strongByRpc`. Low-RPC sources (roughly under 15c) have little room between cost and revenue, and caps on them rarely deliver.
- **`minCapRatio`.** Use `byCapToRpc3d` / `strongByCapToRpc3d`. Find the lowest cap/RPC band where `deliverPct` is still decent (around 50% or more). Caps below that band mostly never spend. Keep `capMarginCents` at 5 unless `strongByCapMinusRpc` clearly says otherwise.
- **Source age.** `strongBySourceAge` usually shows that a strong signal on a **young** source (first day or two) is the best clone of all. That is why speed matters.
- **Bursts.** `clonesPerDay` marks mass-cloning days. If `burstVsNormal` shows burst days performing much worse, they are diluting the tables: re-run with `excludeBursts: true` and compare, but keep enough rows.

Treat bands with `n` under about 8 as anecdotes. When the data is thin, stay close to the defaults: `minProfit` 10, `minRoi` 50, `minConv` 10, `minRpc` 15, `capMarginCents` 5, `minCapRatio` 0.8.

Summarise the calibration in 3 to 4 lines with real numbers, e.g. "Sources with ≥10$ profit and ≥50% ROI on the day: 45% of clones win, 6.3$/day each. Caps under 0.7× RPC delivered in 0% of cases, so the floor is 0.8."

If the study already ran in this conversation today, reuse its conclusions and skip to step 3.

### 3. Find candidates

Run `queryName: "Cap scout: winners ready for a cost cap clone"` with the calibrated `parameters`, e.g. `{"minProfit": 10, "minRoi": 50, "minConv": 12, "minRpc": 15, "minCapRatio": 0.8}`. If the name isn't found, use the candidates code from [queries.md](queries.md).

Other parameters: `capMarginCents` (5), `cloneCooldownDays` (7), `maxCapOffer` (3), `maxCapAccount` (0), `historyDays` (21, how far back to look for earlier clones), `country`, `feed`, `top` (25).

What comes back:
- `summary`: active uncapped adsets, how many have a signal, and how many are ready or blocked.
- `ready`: adsets with a signal that pass every rule. `signal` is `today` (today so far) or `yesterday` (a full day, today still positive). The row has today's and yesterday's spend, profit, ROI and conversions, `tProfitPace` (today's profit extrapolated over the UTC day), `rpcToday` / `rpcYesterday` / `rpc3d` / `conv3d`, `rpcBasis`, `suggestedCapCents`, `capToRpc`, budget and `spendPct`, `trend`, `lastCapCloneDays`, `capOffer`, `capAccount`, and `earlierCapClones` (earlier cap clones of this adset: age, cap, status, spend, profit).
- `blocked`: adsets with a signal that break a rule, with `why`. Show the notable ones, especially "cap clone started ... no cap adset visible". That usually means a clone failed, and the user may want to look at it.
- `watch`: no signal yet, but today's pace reaches the threshold. Don't clone these; mention the best few as "check again later today".

### 4. Judge each ready adset

The query applies the rules. You decide whether the signal is **clear**. Keep, adjust or drop each row:
- **RPC stable?** Compare `rpcToday`, `rpcYesterday` and `rpc3d`. The basis already takes the lower of the 3-day and signal-day RPC. If today is far above the 3-day RPC, the cap from the 3-day RPC is the safe one. If today's RPC is collapsing (well under the 3-day RPC, with real volume), drop it or wait.
- **Enough volume?** Few conversions with a high RPC is a lucky streak, not a signal. Prefer `conv3d` well above `minConv`.
- **Still going?** A `yesterday` signal whose `tProfit` is barely positive late in the country's day (`LocalHour` 18+), or a `trend` of `Down`, is weakening. Drop it or say so.
- **Earlier clones** (`earlierCapClones`):
  - An earlier clone that **never delivered** (spend ~0) usually had a cap too far below RPC. A retry after the cooldown is fine, with the cap at or above `minCapRatio` × RPC. Say it is a retry.
  - An earlier clone that **delivered and lost money** is evidence against cloning. Skip it unless RPC has clearly improved since then.
  - An earlier clone that is still **active** at a similar cap means the offer is already being scaled.
- **Budget-limited source.** A test adset with a tiny budget can't show much absolute profit. There, high ROI plus enough conversions is the signal. A source that only reaches the profit bar thanks to a big budget and a thin ROI is weaker.
- **Cap sanity.** Cap in cents, between 2 and 350, below `rpcBasis`, and `capToRpc` not under the calibrated floor. Round to whole cents.

Also run `list_pending_adset_actions` and drop any adset that already has a pending action (the server would reject the whole call).

### 5. Present

1. **Calibration**: the 3 to 4 lines from step 2.
2. **Clones to submit**, one row each: adset id, country · vertical · feed, account, signal (today / yesterday), profit and ROI on the signal day, conversions, RPC basis → **cap in cents (and USD)**, clone budget, and the one-line comment you will send.
3. **Total new daily budget** (count × budget). Compare it with the division's daily profit if you know it.
4. **Blocked, worth knowing**: failed or pending clones, and big earners blocked by the offer rules.
5. **Watch list**: at most 5.

Say plainly that submitting creates real adsets that spend money.

### 6. Submit (only after a clear yes to this exact list)

- 50 USD budget for all → `submit_adset_clones_with_cap` (`adsetId`, `capInCents`, `comment`).
- Any other budget → `submit_adset_clones_with_cap_and_budget` (adds `budgetInUsd`, max 70). Suggest less than 50 (20 to 30) for weaker or retry cases. Group the actions per tool.
- **`tagName`: `a:capScout`**, always the same, so later runs can find and judge these clones.
- **`comment`**: the reason in one line, e.g. `"today 24$ profit, ROI 160%, 99 conv, RPC 3d 38c stable"` or `"retry: earlier clone at 0.5x RPC never delivered"`. Don't repeat the adset id, country, cap or budget; those are stored anyway.
- `forceAdditionalReview`: `false`, unless the user asks for the clones to wait for manual review.
- **All or nothing.** If one action is invalid, nothing is saved and every error comes back. Fix or drop the listed rows with the user's agreement, then resubmit the whole list.
- The reply says whether the clones were **executed** or are **waiting for review** (the division decides). Report counts, the tag, and which one happened.

Never add adsets the user didn't see. If the user changes anything, show the list again before submitting.

**Unattended runs** (for example a scheduled task): only when the user set that up explicitly. Then submit with `forceAdditionalReview: true`, so nothing is created until someone approves the clones on the **Adset actions for review** page, and report what was queued.

### 7. How did earlier clones do?

When the user asks, run a small query over clones tagged `a:capScout` (tags are on the adsets; filter `x.Tags.Any(t => t.Name == "a:capScout")` and `x.CostCap.Value > 0` or origin `TrafficAdsetCloneWithCap`) for the last 14 to 30 days. Report delivered %, win %, profit, ROI and profit per clone per day, compared with the study's overall numbers. Use it to tighten or loosen the thresholds next time. The **arbo-stat-queries** skill covers writing such queries.

## Things that are easy to get wrong

- **Cap in cents, budget in USD.** 0.38 USD = 38 cents. Show both in the plan.
- **RPC is per conversion**, not per click. Revenue per click (`RevenuePerVisit`) is much lower and would give caps that never deliver.
- **A cap far below RPC is not "safe".** It usually never spends. Clones from mass-cloning days show this: caps at half the RPC, killed after spending 1$.
- **`LastCloneCapUtcHours` is in days**, and `double.MaxValue` when never cloned (the query shows null).
- **A recent clone with nothing visible** is pending, rejected or silent. Never clone the same adset again in that state.
- **Offer counts include killed caps** from the last 6 days, and clones that never had a stats row are invisible everywhere. If the user says they just cloned something, believe them over the stats.
- **Today is partial.** A `today` signal at 10:00 UTC is strong evidence; a `yesterday` signal with a weak today is weaker. Say which it is.
- **Don't clone the same offer twice in one batch** in the same account. The offer rule only sees existing caps, not the other rows of your list.
- **Speed matters, but so does the yes.** Keep the table short and the reasoning to one line per row, so the user can confirm in seconds.

# Preset reference

## Top-level fields

| Field | Meaning |
|---|---|
| `title` | Unique name within the division. |
| `category` | Group heading in the Presets list, for example `Kill` or `Scale`. |
| `description` | One sentence. It is also written as the comment on every adset the automation changes. |
| `isAutomated` | Read only for agents. Only a person turns it on or off. |
| `filter` | Which adsets are kept. See below. |
| `orderBy` / `orderByDirection` | Order of the kept adsets, which matters together with `limit`. `orderByDirection` is `DESC` (default) or `ASC`. |
| `limit` | Maximum number of adsets that go into the action. `0` means all. |
| `areKilledIncluded` | Whether killed or terminated adsets may go into the action. Default false. Set it to true only for Activate-type presets meant to bring killed adsets back. |
| `actionType` / `actionValues` | The action group. See [Actions](#actions). Without them the preset is filter-only. |
| `automationSource` | `TodayStats` (default), `YesterdayStats` or `AllStats` (both runs). |
| `automationFromHour` / `automationToHour` | Hour window in **server time (CET/CEST, not UTC)**. From is inclusive (0–23), to is exclusive (1–23). `-1` means no limit. The window never wraps past midnight. |
| `automationDelayHours` | Minimum hours between two automated today-runs that built an action group. Default 0.5; allowed 0–48. Yesterday runs ignore it. |
| `automationLastExecutionUtc` | Read only. The last today-run that built an action group. |

`orderBy` takes one of these values:

- **Profit:** `ByProfit` (today), `ByProfitAvg`, `ByOverallProfit`, `ByYesterdayProfit`, `ByIntradayProfit`
- **ROI:** `ByROI` (default), `ByIntradayROI`, `ByOverallROI`, `ByROINumberOfDays`
- **Spend and budget:** `ByRevenue`, `ByBudget`, `BySpent`, `BySpentPercentage`, `BySpentOverall`
- **Rates and ratios:** `ByCPM`, `ByRPM`, `ByCTR`, `ByCTROverall`, `ByRPC`, `ByPPC`, `ByCR`, `ByMargin`, `ByRpcCpcRatio`, `ByPTQS`
- **Other:** `ByCreated`, `ByLastChange`, `None`

## Filter

An adset must pass **every** set field. Lists that are omitted or empty don't filter.

| Field | Meaning |
|---|---|
| `nameFilter` | Comma-separated texts. Keeps adsets whose name contains one of them, or whose offer id, adset id or campaign id equals one. A leading `!` turns it into an exclude. |
| `countries` | Comma-separated 2-letter codes to keep, for example `"DE, AT"`. `!` excludes a code: `"!US, !GB"`. Unknown codes are rejected. |
| `languages` | Article language codes to keep, for example `["DE","EN"]`. |
| `onlyNotGeoLocked` | true keeps only adsets that are not geo-locked. |
| `onlyWhereAllOfferAdsetsArePositive` | true keeps only adsets whose offer's adsets are all positive. |
| `statuses` | Adset statuses to keep: `Active`, `Paused`, `Killed`, `Terminated`, `Scheduled`, `Initialized`. Usually `["Active"]`, or `["Active","Paused"]`. |
| `trends` | Day-by-day ROI history type: `MinimumNotMet`, `Mixed`, `MoreNegative`, `MorePositive`, `AlwaysPositive`, `AlwaysNegative`. |
| `profitTrends` | Profit direction: `Flat`, `Up`, `Down`. |
| `trafficProviders` | `Facebook`, `Tiktok`, `Taboola`. |
| `adsetOrigins` | How the adset was created: `RegularPublish`, `LostAndFound`, `AiCloneAdset`, `AiCloneWithCap`, `AiReplicate`, `TrafficAdsetClone`, `TrafficAdsetCloneWithCap`, `TrafficAdsetCloneToCountry`, `TransferToAccount`, `TransferToTiktok`, `Ui_CountryPublish`. |
| `accountTypes` | Account family of the adset's feed: `FLW`, `OH`, `Yahoo`, `MiraSearch`, `YahooTaku`, `YahooMediaWave`. |
| `affiliates` | Feed (affiliate) ids, from `get_affiliate_providers`. |
| `trafficAccountNames` | Exact traffic account names. Avoid these in automated presets. |
| `tagNames` | Keeps adsets that carry at least one of these tags. |
| `comparators` | Comparator name → condition. See below. |

### Condition syntax

A condition is one or more comparisons. `&` (or `&&`) means AND, and `|` (or `||`) means OR. AND binds tighter, so `">10&<50|>100"` means (above 10 and below 50) or above 100. Spaces are ignored.

Each comparison has three parts, written together with no spaces: `[source]operator value`.

**Operators:** `>`, `>=`, `<`, `<=`, `=`, `!` (not equal).

**Source prefix.** This only matters for the comparators marked **D** (day metrics) below. It picks which day's value is compared:

| Prefix | Value compared |
|---|---|
| none | Today, or the newest loaded day |
| `y` | Yesterday (the second-newest day with data) |
| `a` | Average of the daily values over the loaded days. Write `a`, never `avg`. |
| `o` | Overall: the sum for additive metrics, or the ratio of totals for ratio metrics |

For example, `"y<0"` means "yesterday's value is below 0".

**Value.** Usually a number with `.` as the decimal point. A `*` before the number floors both sides first: `">=*3"`. Instead of a number you can compare against:

- the same metric on another day, on **D** comparators: `y` (yesterday), `a` (average), `o` (overall). For example, `"<y"` means "today below yesterday".
- the adset's own ROI or CPM: `roi`, `y-roi`, `o-roi`, `cpm`.

Examples:

| Condition | Meaning |
|---|---|
| `">20"` | Today above 20 |
| `"<-30&y<-30"` | Today and yesterday below -30 |
| `"a>10"` | Average above 10 |
| `">=5&<=50"` | Between 5 and 50 |
| `"<y"` | Today below yesterday |

A comparator with an empty condition (or `"0"` on non-D comparators) doesn't filter. The tools refuse conditions that would never match.

### Comparators

**D** means a day metric, so the `y` / `a` / `o` prefixes work. Money is in **USD** unless noted otherwise.

**Profit and spend**

| Comparator | Compares |
|---|---|
| `ProfitComparator` | Profit (D) |
| `AvgProfitComparator` | Average daily profit |
| `OverallProfitComparator` | Profit over all loaded days |
| `SpendComparator` | Spend (D) |
| `OverallSpendComparator` | Spend over all loaded days |
| `SpendPercentageComparator` | Spend as % of budget (D) |
| `RevenueComparator` | Revenue (D) |
| `BudgetComparator` | Current daily budget |
| `CostCapComparator` | Current cost cap, **in cents**. 0 when there is no cap. |
| `MarginComparator` | Margin %: (IRPM − CPM) / RPM × 100 (D) |

**ROI**

| Comparator | Compares |
|---|---|
| `RoiComparator` | ROI % (D) |
| `OverallRoiComparator` | ROI % over all loaded days |
| `ROINumberOfDaysComparator` | How many newest days in a row have the same ROI sign as today |

**Traffic and rates**

| Comparator | Compares |
|---|---|
| `CTRComparator` | CTR % (D) |
| `OverallCTRComparator` | CTR % overall |
| `CPMComparator` | CPM (D) |
| `RPMComparator` | Revenue per 1000 impressions (D) |
| `IRPMComparator` | Feed revenue per 1000 impressions (D) |
| `ConverionRateComparator` | Conversion rate % (D). The name is spelled this way. |
| `ImpressionsComparator` | Impressions (D) |
| `ClicksComparator` | Clicks (D) |
| `ConversionsComparator` | Conversions (D) |
| `OverallConversionsComparator` | Conversions over all loaded days |
| `ConvCostComparator` | Cost per conversion (D) |
| `ClickCostComparator` | Cost per click (D) |
| `RevenuePerConversionComparator` | Revenue per conversion, RPC (D) |
| `ProfitPerConversionComparator` | Profit per conversion (D) |
| `CostToRevenueRatioComparator` | Cost per conversion / RPC (D) |
| `ClickToRevenueRatioComparator` | Cost per click / RPC (D) |
| `PTQSComparator` | Traffic quality score (D) |

**Age and history**

| Comparator | Compares |
|---|---|
| `DaysStartedComparator` | Days since the adset was created (decimal) |
| `HistoryCountComparator` | Number of loaded days that have data |
| `LocalHourComparator` | Current hour in the adset's country |
| `LastChangeComparator` | Hours since the adset was last changed. 0 when it was never changed. |
| `BudgetIncreaseComparator` | Hours since the last budget increase. Huge when never. |
| `BudgetDecreaseComparator` | Hours since the last budget decrease |
| `BudgetCapIncreaseComparator` | Hours since the last cost cap increase |
| `BudgetCapDecreaseComparator` | Hours since the last cost cap decrease |
| `AdsetLastCloneInHours` | **Days** (despite the name) since the adset was last cloned |
| `AdsetLastCloneWithCapInHours` | **Days** (despite the name) since the adset was last cloned with a cap |
| `AdsetLastTransferInHours` | **Days** (despite the name) since the adset was last transferred to another account |
| `AdsetLastRevenueChangeHours` | Hours since its revenue last changed |

**Offer counts**

| Comparator | Compares |
|---|---|
| `NumberOfActiveComparator` | Active adsets of the same offer |
| `NumberOfPerAccountComparator` | Accounts the offer runs in |
| `NumberOfPerCostCapComparator` | Adsets of the offer that have a cost cap |
| `NumberOfPerAccCostCapComparator` | Adsets with a cost cap of the offer in this account |

**Offer totals.** These only apply when the stats are grouped by offer. Skip them otherwise.

| Comparator | Compares |
|---|---|
| `OfferCombinedAdsetsCount` | Number of the offer's adsets |
| `OfferCombinedPositiveRatio` | Share of the offer's adsets that are positive |
| `OfferCombinedProfit` | The offer's total profit |
| `OfferCombinedAvgProfit` | The offer's average profit |
| `OfferCombinedROI` | The offer's ROI |
| `OfferCombinedRPC` | The offer's revenue per conversion |

**"Since" comparators.** For the budget/cap change, clone, transfer and revenue-change comparators, "never" is a very large number. So `">24"` also keeps adsets where it never happened. Use `"<24"` to mean "happened in the last 24h" (or `"<1"` for the three day-based clone/transfer ones).

## Actions

`actionValues` is a JSON object. Fields you leave out keep their defaults. Unknown fields are rejected, and the error lists the valid fields with their defaults.

**Units:**

- All budgets (`MinimumBudget`, `MaximumBudget`, `NewBudgetValue`, `InitialBudget`, `CollectiveChange` on budget actions, `MinimumIncrease`, `MaximumIncrease`) are in **cents**. 150 = $1.50, 30000 = $300.
- Caps and bids are in **cents**.

**Clamping on the budget actions:**

- A new budget below `MinimumBudget` is raised to it.
- A new budget above both `MaximumBudget` and the current budget is cut to `MaximumBudget`. So an adset already above the max can be cut down even by a "raise".

**`ResetAfterHours`** (0 = never) changes the budget or cap back after that many hours.

### Status

**Kill** — kills the adsets.
- Values: `Limit` (0 = none).
- Skips adsets that are already killed or have a 0 budget.

**Pause** — pauses the adsets. They go back to Active after `ResetAfterHours`.
- Values: `ResetAfterHours` (default 12). 0 means nothing is paused.
- Skips adsets that are already paused or killed.

**Activate** — activates Paused, Scheduled or Initialized adsets, and Killed ones when `areKilledIncluded` is true. The budget is unchanged.
- Values: none, send `{}`.

**ActivateAndChangeBudget** — activates the adsets and changes the budget by `PercentageUpgrade` %, clamped to `MinimumBudget` and `MaximumBudget`.
- Values: `PercentageUpgrade` (default -50), `MinimumBudget` (default 150), `MaximumBudget` (default **500 = $5**; raise it).
- An adset whose budget wouldn't change is skipped, and so is a new budget ≤ 150.

**KillAndReplicate** — kills the adsets and asks for new ads of the same offer in the same account (one request per offer).
- Values: none.

### Budget

**BudgetByPercentage** — new budget = current ± `PercentageUpgrade` %. Use a negative value to cut.
- Values:
  - `PercentageUpgrade` (default 0, which does nothing)
  - `Limit` (0 = none)
  - `MinimumBudget` (150), `MaximumBudget` (30000)
  - `MinimumIncrease` and `MaximumIncrease` (cents, 0 = no limit; they apply to cuts too)
  - `ResetAfterHours` (0)

**BudgetByValue** — new budget = current + `CollectiveChange` cents. Use a negative value to cut.
- Values: `CollectiveChange` (0 does nothing), `MinimumBudget` (150), `MaximumBudget` (30000), `ResetAfterHours` (0).

**NewBudget** — sets every adset's budget to `NewBudgetValue` cents. There is no min/max.
- Values: `NewBudgetValue` (values under 180 do nothing), `ResetAfterHours` (0).

**BudgetByClicksValue** — new budget = current + `CollectiveChange` × cost per click (`CollectiveChange` is a number of clicks).
- Values: `CollectiveChange`, `MinimumBudget`, `MaximumBudget`, `ResetAfterHours`.

**BudgetByImpressionValue** — new budget = current + `CollectiveChange` × cost per impression (`CollectiveChange` is a number of impressions).
- Values: `CollectiveChange`, `MinimumBudget`, `MaximumBudget`, `ResetAfterHours`.

**BudgetByClicksPercentage** / **BudgetByImpressionPercentage** — new budget = current + (`CollectiveChange` % of today's clicks or impressions) × their cost.
- Values: same as above. Use a negative `CollectiveChange` to cut.

### Cost cap (only adsets that already have a cap)

**ChangeCapValuePercentage** — new cap = cap ± `PercentageChange` %.
- Values:
  - `PercentageChange` (0 does nothing)
  - `MaximumDecrease` and `MaximumIncrease` (cents per change, default 100)
  - `MinimumBid` (3), `MaximumBid` (250)
  - `ResetAfterHours` (0)

**ChangeCapValue** — new cap = cap + `CollectiveChange` cents, clamped to `MinimumCap` and `MaximumCap`.
- Values: `CollectiveChange`, `MinimumCap` (3), `MaximumCap` (**55**), `ResetAfterHours` (0).
- **Caution:** even with a change of 0, every cap outside the min–max range is forced into it. For example, an 80c cap is cut to 55c. Prefer ChangeCapValuePercentage.

### Clone and scale (each creates new adsets that spend their own budget)

**TrafficAdsetClone** — clones each adset in the same account, with no cap.
- Values: `NewBudgetValue` (cents, default 200), `TagName`.

**TrafficAdsetCloneWithInitialBudget** — clones each adset at its current budget.
- Values: `TagName`.

**TrafficAdsetCloneWithCap** — clones each adset with a cost cap. The cap = floor(today's revenue per conversion) + `RpcDifference`, at least `MinimumBid`, and at most `MaximumBid` when that is > 0.
- Values: `Limit` (0), `CollectiveChange` (the clone's budget in cents, default 5000 = $50), `RpcDifference` (-5), `MinimumBid` (3), `MaximumBid` (0 = none).
- Skips adsets whose account has no room for adsets.
- With no conversions today the cap falls to `MinimumBid`, so add `ConversionsComparator ">=…"` to the filter.

**TransferToAccount** — creates the ads in another account of the same family where the offer doesn't run yet.
- Values: `InitialBudget` (cents, 200), `CapValue` (cents, 0 = no cap), `Limit` (0).
- From a preset it picks one free account automatically, for the first adset of each offer only. `AccountName` is ignored from a preset.

**ToTiktokWithCap** — copies the offer to a TikTok account of the same family, with a cap from the same revenue-per-conversion formula.
- Values: `Limit` (0), `InitialBudget` (cents, default 2000 = $20), `RpcDifference` (-5), `MinimumBid` (3), `MaximumBid` (0).
- Skips adsets when the family has no TikTok account.

**ToTiktokNoCap** — the same, without a cap.
- Values: `Limit`, `InitialBudget` (2000).

**CreateReplicate** — Facebook only: asks for new ads of the offer in the same account, one per offer.
- Values: `InitialBudget` (cents; values ≤ 150 use the default budget).

**ArticleSimilarTitle** — asks for `NumberOfTitles` similar article titles per offer.
- Values: `TitleReference` (default `stats-similar-title`), `NumberOfTitles` (2).

### Not available in presets

These need a value typed per adset in the UI, so a preset could never change anything with them. The tools reject them:

- `BudgetByValueIndividual`
- `BudgetNewValueIndividual`
- `BudgetByImpressionIndividual`
- `BudgetByClicksIndividual`
- `TrafficAdsetCloneToCountry`

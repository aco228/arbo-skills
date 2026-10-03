# Stats queries: API reference

Everything a query can use. Names are case-sensitive C#. `get_stat_response_adset_definition` returns the live member list when the MCP tools are available.

## Contents
1. What the query compiles into
2. Query API
3. `StatResponseAdset`: one adset
4. `AverageValue`: every metric
5. Enums
6. Namespaces available

---

## 1. What the query compiles into

The text in the Queries editor (or `code` in `run_stat_query`) becomes the body of this method:

```csharp
public class CompiledScriptQuery : ScriptQuery
{
    protected override async Task InternalRun()
    {
        // <your query>
    }
}
```

- It runs once, over the whole list of adsets you load. You can use `var`, `if`/`switch`, loops, LINQ, local functions, anonymous objects, `Math` and string methods. You cannot declare classes or fields.
- If it throws, the run stops: results added before that are returned together with the exception.
- A query that runs over 2 minutes is stopped the same way, wherever it is (inside a loop or a LINQ lambda too).
- Recursion that goes too deep (a local function or lambda calling itself without end) stops the query with "Recursion too deep" in `fatalException`.
- At most 4 queries run at once on the server (3 per division). When all slots stay taken for 30 seconds, the query doesn't run and `fatalException` says the server is busy; retry a minute later. A query that ran over its time limit keeps its slot until it really stops.
- When the server is nearly out of memory, a query doesn't start and `fatalException` says the server is low on memory; retry a few minutes later, loading fewer days if you can.
- When it adds no data at all, an error "The query produced no data" is added to the result.

## 2. Query API

### Loading stats

**Time zone:** all dates and day keys are UTC. "Today" is the current UTC day.

Each call returns a `List<StatResponseAdset>`: every adset of the division that has stats on any loaded day, including adsets killed since (see section 3). The newest loaded day is the "today" of every `AverageValue` (`.Value`).

| Call | Loads |
|---|---|
| `await LoadStatsToday()` | Today and the 5 days before (6 days). Today is partial. |
| `await LoadStatsTodayWithDays(int days)` | Today and the days before it, `days` in total. |
| `await LoadStatsYesterday()` | Yesterday and the 5 days before (6 full days). |
| `await LoadStatsYesterdayWithDays(int days)` | Yesterday and the days before it, `days` in total. |
| `await LoadStatsForDate(string date, int days)` | `date` in `dd-MM-yyyy` format, and the days before it, `days` in total. |

Loading is the slow part: **load once per query** and reuse the list. One load already holds every loaded day in each metric's `History` (read them with `GetDaysAgo`, `SumDaysAgo`, ...) and every adset that has stats on any loaded day, so never load today and yesterday separately. Responses are cached for a minute.

### Output

| Call | Effect |
|---|---|
| `AddData(string name, object value)` | Adds a named result. `value` is serialized to JSON: numbers, strings, lists, dictionaries and anonymous objects all work. Doubles are written with 2 decimals. |
| `AddError(string message)` | A message from the query to its reader about a problem in the data ("no adsets matched the country"). |
| `AddNote(string message)` | An informational message ("today's stats are partial"). |

Limits: at most 50 `AddData` entries, 20,000 characters per value, 100,000 characters in total. An entry over a limit is skipped and a system warning says so.

### Testing an arbo script

**Only for testing arbo scripts** before they are proposed or saved (the **arbo-scripts** skill, step 7). Never use it to answer questions about adsets: filter them with LINQ in the query itself.

`await RunTestScript(string scriptCode, List<StatResponseAdset> adsets)` dry-runs arbo script code (the Scripts editor text, see the **arbo-scripts** skill) on `adsets` and returns a `RunScriptResult`. Nothing is applied. Pass the code as a raw string literal (`"""..."""`). Last execution and stat collection times are null, as on a first run. The script runs for the query's division, so `GetSupportedAccounts(...)` in the script returns that division's live accounts.

| Member | Meaning |
|---|---|
| `Status` | `Success`, `CompileError` or `RuntimeError` (init threw). Check it first. |
| `Errors` / `Notes` | Compile errors with line and column, the runtime exception, "OnAdset threw for N adsets", init stopped or filtered adsets. |
| `Counts` | Adsets per action, e.g. `{ "Kill": 12, "None": 185 }`. |
| `Adsets` | Every input adset once: `Adset`, `AdsetId`, `Actions` (`Type`, `Value`, `Comment`), `ActionName`, `Error` (OnAdset threw, adset ignored). |
| `AdsetIdsWith(action)` | Ids of adsets that got `action`. |
| `Compare(action, expectedAdsetIds)` | `IsMatch`, `ExpectedCount`, `ActualCount`, `Missed` (expected, didn't get it: shows what it got instead), `Unexpected` (got it, not expected: the comment says why), `NotInInput`. |

Actions: `Kill`, `Activate`, `Pause`, `PercentageChange`, `BudgetChangeIndividual`, `CreateCostCap`, `ChangeCostCap`, `Clone`, `TransferToAccount`, `Include`, and `None` for untouched adsets. `Value` is the budget or cap in cents, pause hours, the account name, or the percentage / clone settings.

Return `Counts` and comparisons with `AddData`, not the whole result: every entry carries the full adset.

### Inputs

| Call | Returns |
|---|---|
| `Param(string name, string defaultValue, string? description = null)` | `string` |
| `Param(string name, int defaultValue, string? description = null)` | `int` |
| `Param(string name, double defaultValue, string? description = null)` | `double` |
| `Param(string name, bool defaultValue, string? description = null)` | `bool` |

### Dates

| Call | Returns |
|---|---|
| `ShiftDateKey(string dateKey, int days)` | The `yyyy-MM-dd` key `days` days after `dateKey` (negative = before); null if unreadable. |
| `DaysBetween(string fromKey, string toKey)` | Whole days from `fromKey` to `toKey`; null if either is unreadable. |

Both accept `yyyy-MM-dd` (`History` keys) and `yyyyMMdd` (`KillDateKey`). On a metric, `GetDaysFrom(dateKey, offset)` reads the value `offset` days from a date key.

The value passed by the caller for `name`, or `defaultValue`. Name, default and description must be literals (they are read from the code without running it) and names must be unique. `-5` and `-2.5` are fine as defaults.

## 3. `StatResponseAdset`: one adset

### Killed adsets

The list includes every adset that has stats on any loaded day, also adsets killed since. For days after the kill they have no stats (0). `Status` is the current status. For questions about the current state, filter with `Status == AdsetStatus.Active` or on spend; for patterns and history, keep them.

`Terminated` is a kill that cannot be undone: set only by a person in the UI (complications, compliance), paused on Facebook, and no tool, script or reset changes the adset again. Treat it as killed in every query (`Status is AdsetStatus.Killed or AdsetStatus.Terminated`, or the `IsKilledOrTerminated()` extension).

### Identity and state
| Member | Type | Meaning |
|---|---|---|
| `AdsetId` | string | Traffic-provider adset id. |
| `Status` | `AdsetStatus` | Current status. |
| `TrafficProvider` | `TrafficProvider` | Facebook / Taboola / Tiktok ... |
| `TrafficAccountName`, `TrafficAccountId`, `TrafficCampaignId` | string | Account and campaign. |
| `Origin` | `AdsetOrigin` | How the adset was created (regular publish, clone, cap clone, replicate to another account, transfer ...). |
| `OriginalAdsetId` | string? | Adset this one was created from (clone, cap clone, transfer or replicate to another account): the direct parent, so a chain A -> B -> C has C pointing to B. Empty when none. Transfers and replicates carry it only from 2026-09-27; older ones are empty. |
| `IsAdsetDeleted` | bool | Adset deleted on the provider. |
| `CreatedDays` | double | Fractional days since the adset was created. |
| `KillDateKey` | string? | UTC day of the kill as `yyyyMMdd` (no dashes, unlike `History` keys). |
| `LocalHour` | int | Current hour in the adset's country (0-23). Day keys are UTC, so near midnight UTC the country can be on another calendar day. |
| `Tags` | `List<AdsetTag>` | Tracking tags, each with `.Name`, `.Count`, `.Time` (UTC of the latest write). `t:...` = the launch tag from title submission, `s:...` = scripts and AI changes. Kept for 20 days. There is no `TagName` on the adset: find the launch tag with `x.Tags.Select(t => t.Name).FirstOrDefault(n => n.StartsWith("t:"))`. |

### Content and targeting
| Member | Type | Meaning |
|---|---|---|
| `Country` | string | ISO country code. |
| `Language` | string | Language code. |
| `HasMultiCountry` | bool | Targets more than one country. |
| `IsGeolocked` | bool | Geolocked. |
| `Name` | string | **Theme name of the article, else vertical name**, else `"DELETED"`. Not the adset name. |
| `CountryAndVertical` | string | `"<COUNTRY>-<Name>"`, e.g. `"US-Cars"`. |
| `Vertical`, `Theme` (nullable), `Division` | `IdDocument` | Use `.Name` (also `.SlugId`, `.Id`). |
| `ArticleName` | string | Internal article name: the search keyword on OH and Yahoo (`el-sparkesykler seniorer`), a URL slug on FLW. **Not the published title**, so not relevant for title work: use `Title` / `Anchor`. |
| `ArticleCategory` | `ArticleCategoryType` | Real category of the article (Auto, Finance, Health, ...), classified per title when the article was generated, independent of the division's vertical. Useful as a second vertical check, e.g. adsets whose `Vertical.Name` says one thing while the article is really about another. `Unknown` for OH and Yahoo articles and for articles created before 2026-10-03, so filter `!= ArticleCategoryType.Unknown` before grouping by it. |
| `ChannelId` | string? | Google AdSense channel of the RSOC article: the key the article's revenue is tracked by. Plumbing, rarely useful for analysis; mainly for matching an adset to AdSense revenue data. `null` when the adset has none. |
| `IsArticleDeleted` | bool | Article deleted. |
| `ImagePromptName` | string? | Name of the saved image prompt (see `list_image_prompts`) that generated the adset's creative. `null` = the default prompt, or no saved prompt (another image pipeline, or an adset created before prompt tracking started on 2026-09-26). Clones keep their source's value. |
| `Title` | string | The published title (ad text) in the original language. |
| `Anchor` | string | The published title (ad primary text) in English. |
| `Url` | string | Landing URL. |
| `OfferId` | ObjectId | The offer (article × country). |

### Affiliate
| Member | Type | Meaning |
|---|---|---|
| `Affiliate` | int | Affiliate id (a plain number, not an enum). |
| `AffiliateName` | string | Affiliate name. The easiest thing to compare. |
| `AffiliateModel.FeedType` | `AffiliateFeedType` | Feed (FLW, OH, Yahoo, ...). |
| `AffiliateModel.AccountType` | `TrafficAccountType` | Account family the affiliate is configured for (FLW, OH, Yahoo, ...). The adset can only be transferred or replicated to accounts of this `Type` **and** of the same `TrafficProvider`. Was `FacebookAccountType` before; that name no longer compiles. |
| `AffiliateModel.Domain`, `.Prefix` | string | Affiliate domain and prefix. |

### Siblings (other loaded adsets of the same offer and country)

Killed adsets in the list count as siblings too, so `AreOfferAdsetsPositives` is false when a killed sibling has no profit today.

| Member | Meaning |
|---|---|
| `OfferCount` | How many loaded adsets share this OfferId and Country. |
| `OfferCountWithCap` | ... of which have a cost cap. |
| `OfferCountWithCapAccount` | ... with a cap on the same account. |
| `OfferCountAccounts` | Distinct accounts among them. |
| `AreOfferAdsetsPositives` | All of them have today's profit > 0. |

### History of changes
| Member | Meaning |
|---|---|
| `Changes` | `List<ChangeModel>`, newest first, at most the last 100: `.Type` (`ChangeModelType`), `.Origin` (`AdsetChangeOrigin`), `.Created` (unix **milliseconds**), `.From`/`.To` (strings; status changes hold `AdsetStatus` names, but older records can have `From` as `ACTIVE`/`PAUSED`; `GetFromDouble()`/`GetToDouble()` give dollars), `.IsBudget()`, `.ResetTimeUtc` (unix milliseconds or null, when a timed change reverts), `.Comment`, `.Stats` (`StatSnapshot`, see "Intraday snapshots": the adset's cumulative stats of that day at the moment the change was applied, e.g. `.Stats.Profit`; null for changes before 2026-09-30 or when the day had no stats yet; resets and the early-morning activation carry it too). |
| `LastChangeType` | `ChangeModelType?`, the most recent change. |
| `LastChangeDays` | Days since the last change. |
| `GetLastBudgetIncreaseInHours()`, `GetLastBudgetDecreaseInHours()`, `GetLastCapIncreaseInHours()`, `GetLastCapDecreaseInHours()`, `GetLastStatusChangeInHours()` | Hours since that change; `double.MaxValue` if it never happened. Launch is not recorded as a status change, so a never-changed adset returns `double.MaxValue`. |
| `GetLastBudgetChangeInHours()` / `GetLastBudgetChangeInDays()` | `double?`, null if never. |
| `GetLastChangeInHours(ChangeModelType type, double? default = null)` / `GetLastChangeInDays(...)` | Generic versions. Return `default` when the change never happened (null if omitted). For cooldown checks pass `double.MaxValue`, never 0: with 0 every never-changed adset looks "just changed". |
| `LastCloneUtcHours`, `LastTransferUtcHours`, `LastCloneCapUtcHours` | **In days** despite the name. `double.MaxValue` if never. |
| `LastRevenueChangeUtcHours` | Hours since revenue last changed within the **newest loaded day**. `double.MaxValue` when revenue has not changed yet that day: it resets with every new day, even for adsets that had revenue yesterday. |

### Trend
| Member | Type | Meaning |
|---|---|---|
| `ProfitTrack` | `List<double>` | Recent profit snapshots in dollars, **newest first**, up to 10. `[0]` equals today's `Profit.Value`. Cumulative for today, added only when profit changes, no timestamps; 10 points usually cover a few hours, varying per adset. |
| `ProfitTrend` | `TrendDirection` | Slope of the last 4 `ProfitTrack` points. |
| `ProfitTrendSlope` | double | That slope. |
| `Trend` | `AdsetCollectionTrend` | Daily ROI sign pattern across the loaded days. |
| `RoiNumberOfDays` | int | Streak of the newest days whose ROI sign matches today's. |
| `GroupByValues.Age` | string | Bucket: `"<1"`, `"<2"`, `"<3.5"`, `"<6"`, `">6"` (days). |
| `GroupByValues.ROI` | string | Bucket: `"<-80"`, `"<-50"`, `"<-20"`, `"<0"`, `"<10"`, `"<30"`, `"<50"`, `"<80"`, `">80"`. |

### Intraday snapshots
| Member | Type | Meaning |
|---|---|---|
| `Snapshots` | `IReadOnlyList<StatSnapshot>` | The newest loaded day's stats at each moment they changed, **newest first**, up to 300. `[0]` is the latest state. Values are **cumulative for the day** (like `Profit.Value`), so the change between two snapshots is the difference of their values. A snapshot is added only when revenue, spend, clicks or conversions change. Tracked since 2026-09-29; empty for adsets without stats changes that day. |
| `SnapshotsByDay` | `IReadOnlyDictionary<string, List<StatSnapshot>>` | Snapshots of **every loaded day**, keyed like `History` (`"yyyy-MM-dd"`), each newest first and cumulative for its day. Compare the same hour across days, e.g. `ad.SnapshotsByDay.TryGetValue(key, out var list)`. Days before 2026-09-29 have no entry. |

`StatSnapshot` members (same type as `ChangeModel.Stats`): `TimeUtc` (`DateTime`, UTC), `HoursAgo` (hours since the snapshot), `Minute` (minutes since UTC midnight of the stats day), `Revenue`, `Spend`, `Profit` (dollars), `ROI` (percent, 0 without spend), `RevenueCents`, `SpendCents` (cents), `Clicks`, `Conversions`.

```csharp
// Profit made in roughly the last 2 hours (snapshot closest to 2h ago, or the oldest one)
var past = ad.Snapshots.FirstOrDefault(x => x.HoursAgo >= 2) ?? ad.Snapshots.LastOrDefault();
var profitLast2h = past == null ? 0 : ad.Snapshots[0].Profit - past.Profit;
```

When a query returns whole `ad` objects, `Snapshots` and `SnapshotsByDay` are left out of the output to keep it small. Return `ad.Snapshots` or a projection of it explicitly (e.g. `ad.Snapshots.Select(x => new { x.TimeUtc, x.Profit })`).

### Metrics (all `AverageValue`, see section 4)
| Member | Unit |
|---|---|
| `Spend`, `Revenue`, `Profit` | Dollars, from our tracking system. `Spend` is the actual spend. `Profit = Revenue - Spend`. |
| `SpendTraffic` | Dollars, as reported by the traffic provider (Facebook, ...). Only for comparing with our tracking in the UI; the numbers can differ. Don't use it for analysis: `Spend` is the actual spend. |
| `Budget` | Dollars. Today's value is the live budget. |
| `CostCap` | **Cents**. `0` = no cap. |
| `SpendPercentage` | Percent of budget spent. |
| `ROI` | Percent (`25` = +25%). `ROI.Overall` = ROI over all loaded days. |
| `ROAS`, `POAS` | Ratios. |
| `Clicks`, `Conversions`, `Impressions` | Counts from our tracking system, the source of truth. |
| `ClicksTraffic`, `ConversionTraffic`, `ImpressionsTraffic` | The traffic provider's own counts, only for comparing with our tracking in the UI. Don't use them for analysis. |
| `CTR` | Percent, clicks / impressions. |
| `CR` | Percent, conversions / clicks. |
| `CostPerVisit`, `RevenuePerVisit` | Cents per click. |
| `CostPerConversion`, `PricePerConversion`, `ProfitPerConversion` | Cents. `PricePerConversion` = revenue per conversion. |
| `CostPerImpression` | Cents. |
| `CPM` | Dollars per 1000 impressions. |
| `RPM` | Dollars per 1000 clicks. |
| `IRPM` | Dollars per 1000 impressions. |
| `CostToRevenueRatio`, `ClickToRevenueRatio`, `Margin`, `PTQS` | Ratios and quality score. |

Shortcuts: `CurrentBudgetInt` (today's budget in cents), `OverallRevenue`, `OverallProfit`, `OverallCost` (sums in dollars), `ROIOverall` (percent), `CTROverall`, `HistoryCount` (days with data).

## 4. `AverageValue`: every metric

One value per loaded day, **newest first**.

| Member | Meaning |
|---|---|
| (implicit `double`) | `x.ROI > 20` compares the newest day, the same as `.Value`. |
| `Value` | Newest day (today when today has data). |
| `Yesterday` | Second-newest day **that has data**. Not guaranteed to be the calendar day before. |
| `YesterdayDiff` | Ratio change `Value` vs `Yesterday`. |
| `Overall` | The value over all loaded days. Additive metrics (Spend, Revenue, Profit, Clicks, Impressions, Conversions): the sum. Ratio metrics (ROI, CTR, CR, CPM, RPM, IRPM, ROAS, POAS, cost / revenue per ...): recomputed from the period totals with the same formula as the daily value. `Budget`, `CostCap`, `PTQS`: a plain sum with no meaning, use `Value` or `Average`. |
| `Average` | Mean over loaded days. |
| `HistoryCount` | Number of days. |
| `History` | `Dictionary<string, double>` date key → value, newest first. `History.Values.Take(3)` = last 3 days. |
| `GetAverageForDays(int n)` | Mean of the newest `n` days. **Throws when there is no history.** |
| `GetForDate(string key)` | `"today"` or a date key; 0 if missing. |
| `GetDaysFrom(string dateKey, int offset)` | The day `offset` days after `dateKey` (negative = before). Accepts `yyyy-MM-dd` and `yyyyMMdd` (`KillDateKey`); 0 if missing. E.g. `Spend.GetDaysFrom(KillDateKey, -1)`. |
| `GetDaysAgo(int n)` | The calendar day `n` days before the newest loaded day (0 = newest); 0 if that day has no data. |
| `SumLastDays(int n)` | Sum over the newest `n` calendar days. Additive metrics only. |
| `SumDaysAgo(int from, int to)` | Sum over calendar days `from`..`to` days ago, both included. Additive metrics only. |
| `AverageLastDays(int n)` | Mean over the newest `n` calendar days that have data; 0 when none. Safe replacement for `GetAverageForDays`. |
| `TrendSlope(int n)` | Slope over the newest `n` calendar days with data, oldest to newest: positive = rising; 0 with fewer than 2 days. |
| `TodayTrend`, `AverageTrend` | `AverageTrendType`: `More` / `Less` / `Unknown`. |

## 5. Enums

Enums change during development: these lists are a snapshot and can be out of date. `get_stat_response_adset_definition` returns the current values (read from the code on every call); to see which values actually occur in the division, run a stats query that returns the distinct values. Affiliates are data, not an enum: compare `AffiliateName` or `AffiliateModel.FeedType`, and use `get_affiliate_providers` / `get_affiliate_feed_types` for what the division supports.

- `AdsetStatus`: `Unknown`, `Initialized`, `Active`, `Scheduled`, `Killed`, `Paused`, `Terminated` (permanent kill set by a person in the UI; treat as killed, never changeable)
- `TrafficProvider`: `Unknown`, `Undefined`, `Facebook`, `Taboola`, `Tiktok`
- `AdsetOrigin` (named `FacebookAdsetOrigin` before; that name no longer compiles): `Unknown`, `RegularPublish`, `LostAndFound`, `AiCloneAdset`, `AiCloneWithCap`, `AiReplicate`, `TrafficAdsetClone`, `TrafficAdsetCloneWithCap`, `TrafficAdsetCloneToCountry`, `TransferToAccount`, `TransferToTiktok`, `Ui_CountryPublish`
- `ChangeModelType`: `Status`, `BudgetDecrease`, `BudgetIncrease`, `CapDecrease`, `CapIncrease`
- `AdsetChangeOrigin`: `Default`, `Reset`, `UI`, `Script`, `AIChange`, `Preset` (the older preset automation), `HourRule`, `Yesterday`, `EndOfDay`
- `TrendDirection`: `Flat`, `Up`, `Down`
- `AdsetCollectionTrend`: `MinimumNotMet`, `Mixed`, `MoreNegative`, `MorePositive`, `AlwaysPositive`, `AlwaysNegative`
- `AffiliateFeedType`: `Unknown`, `FLW`, `OH`, `Yahoo`, `WordlineSearchRsoc`, `SearchRsoc2`, `SearchRsoc3`, `N2sJam`, `SearchRsocSt`, `FlwVoluum`
- `TrafficAccountType`: `Unknown`, `FLW`, `OH`, `Yahoo`, `MiraSearch`
- `ArticleCategoryType`: `Unknown`, `Auto`, `Beauty`, `Education`, `Employment`, `Finance`, `Health`, `HomeImprovement`, `Law`, `Lifestyle`, `Miscellaneous`, `RealEstate`, `Services`, `Shopping`, `Technology`, `Travel`
- `AverageTrendType`: `Unknown`, `More`, `Less`

## 6. Namespaces available

These are already imported, and nothing else is: `System`, `System.Linq`, `System.Collections.Generic`, `System.Threading.Tasks`, plus the project namespaces that hold every type above.

To use anything else, write its fully qualified name. For example, the affiliate-family helpers: `AdCompiler.Core.Extensions.AffiliateProviderExtensions.IsOceanHeroAffiliate(x.Affiliate)` (also `IsCoinisAffiliate`, `IsYahooAffiliate`).

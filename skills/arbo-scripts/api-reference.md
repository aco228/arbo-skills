# Arbo scripts: API reference

Everything a script can use. Names are case-sensitive C#.

## Contents
1. What the script compiles into
2. Actions (return values)
3. `ad`: the adset
4. `AverageValue`: every metric
5. Enums
6. Namespaces available

---

## 1. What the script compiles into

A script has up to three parts: two optional regions, and the rest.

```csharp
public class CompiledQuery : StatScriptBase
{
    // <#region members>: class-level code (fields, properties, helper methods, small records)

    protected override void Init()
    {
        // <#region init>: runs once, before any adset
    }

    protected override ScriptActionBase OnAdset(StatResponseAdset ad)
    {
        // <everything outside the two regions>
        return Include();          // reached when your script doesn't return
    }
}
```

- `#region members` ... `#endregion` and `#region init` ... `#endregion` are optional, each at most once, and can be anywhere in the script (put them at the top). The names are case-insensitive. Any other `#region` is an ordinary, cosmetic region. A missing `#endregion` is a compile error on the `#region` line.
- **Members** is class-level C#: typed fields or properties for state (`int Maximum = 0;`, `HashSet<string> ToKill = new();`) and helper methods. The script instance is new on every run, so fields start from their initial values each time. Don't reuse names of the base class (`Adsets`, `TagName`, `Kill`, ...).
- **Init** runs once, before the body. It sees every loaded adset, so cross-adset decisions go there (ranking, top N, totals). It can use the run context below and store results in members. There is no `ad` in init, and `return` there returns nothing. If init throws, the whole run fails with that error.
- **The body** (everything outside the two regions) runs once per adset in `Adsets`, **one at a time, in list order**, so it can safely read and update members (counters, sets). Prefer computing in init and only reading in the body.
- Only the variable `ad` is in scope in the body. The action helpers below are methods of the base class and are called directly (`Kill()`, `Pause(3)`).
- Before compiling, the literal texts `return true;` and `return false;` in the body are replaced with `return Include();` and `return Ignore();`. Only that exact spelling works. `return (true);`, `return true ;`, or `return true;` inside a lambda are not replaced. Members and init are never rewritten.
- If the body throws for an adset (null reference, empty sequence, bad cast), the adset silently becomes `Ignore()`.
- In the body you can use `var`, `if`/`switch`, LINQ, local functions, `Math`, and string methods. Classes, fields and methods go in members.

### Run context (properties of the script, usable in all three parts)

| Member | Type | Meaning |
|---|---|---|
| `Adsets` | `List<StatModel>` | The adsets the body runs for, in this order. Starts as every loaded adset (the Stats page's date range, default 6 days back from today). Reassign it in init to filter or reorder: `Adsets = Adsets.Where(x => x.Entry.ROI < 0).OrderBy(x => x.Entry.Profit.Value).ToList();`. Each item's adset is `.Entry`, the same type as `ad`. Adsets left out get no action and are not shown. It can hold adsets that did nothing today (killed recently, stopped by the provider) next to live ones: check `ad.IsActiveToday` before acting on today's numbers. Automated runs before 06:00 server time (CET/CEST) see yesterday as the newest day, so `IsActiveToday` is false for every adset then. |
| `CanRun` | bool | Default `true`. Set it to `false` in init to skip the run: no adset is processed and nothing is shown. The run is also skipped when `Adsets` is empty. |
| `TagName` | string | Tag written on every adset this run changes, with a timestamp and a counter (a later change with the same tag bumps both). Empty = no tag. Format `"s:<camelCaseName>"`, short and stable: it is how this script (and others) find the adsets it touched, so renaming it loses that history. Set it in init. Tags are written only for **status, budget and cost-cap changes**, once they are applied after Execute. Clones and transfers don't tag the source adset. |
| `LastExecutionUtc` | `DateTime?` | When this saved script's automation last created action groups (or failed to compile or threw). Automated runs that found nothing don't move it, so a gate like `CanRun = LastExecutionUtc == null \|\| ... >= 6` means "at most one acting run per 6 hours", not one run. `null` when run from the editor, or when the automation never acted. |
| `LastStatisticUpdateUtc` | `DateTime?` | When the loaded stats were last collected. |

`BreakExecution()` (body only) stops the run: this adset and the ones after it get no action and are not shown. Actions already returned stay.

### Comments on actions

Any action can carry a comment, stored with the change on the adset so you can later see why it happened: `return Kill().WithComment("ROI < -40% over 3 days");`. Call `WithComment` last.

The comment is for later analysis of changes: a short reason and, when useful, the expected outcome ("ROI 45% on 20$ spend, scale to test headroom"). Leave out what the change or adset already holds or can be filtered on: adset id, country, vertical, old and new value, date.

## 2. Actions (return values)

Every path of the body has to return one of these. Budgets and caps passed to actions are in **cents** unless the name says `Usd`.

| Call | Effect |
|---|---|
| `Include()` / `return true;` | Keep the adset visible in the grid. No action. |
| `Ignore()` / `return false;` | Hide the adset. No action. |
| `Kill()` | Kill group: sets status Killed. Already-killed and terminated adsets are skipped. |
| `Activate()` | Activate group: sets Active. Only applies to Killed, Paused, Scheduled or Initialized adsets. Terminated adsets never come back. |
| `Pause(int hours)` | Pause group: sets Paused and automatically re-activates after `hours`. `0` = skipped. Already Paused, Killed or Terminated = skipped. One group per distinct `hours`. |
| `ChangeBudgetByPercentage(new ActionChangeBudgetByPercentageRequest { ... })` | Percentage budget change (details below). One group per distinct request. |
| `NewBudgetInUsd(double usd)` | Set an exact new budget in dollars (rounded up to cents). |
| `NewBudgetInCents(double cents)` | Set an exact new budget in cents. The group clamps it (min 150 cents). |
| `ChangeCostCap(double cents)` | Set a new cost cap in cents on an adset that **already has** a cap. Adsets with `CostCap == 0` are skipped. |

### Timed budget and cap changes: `.WithResetAfterHours(int hours)`

`NewBudgetInUsd(...)`, `NewBudgetInCents(...)`, `ChangeCostCap(...)` and `ChangeBudgetByPercentage(...)` return an action you can chain `.WithResetAfterHours(hours)` on. The change is then temporary: `hours` after it is applied, the budget (or cap, for `ChangeCostCap`) goes back to the value the adset had before the change. Without it the new value stays.

- `hours` is corrected into **1 to 24**: `0` or a negative number becomes 1, anything above 24 becomes 24.
- Actions with different reset hours (or none) land in different groups, so one script can mix temporary and permanent changes.
- A later change to the same field cancels that part of the pending reset; killing the adset clears all resets. `ad.Changes[i].ResetTimeUtc` shows when a timed change reverts.
- Chain it before `WithComment`, which stays last.

```csharp
if (ad.ROI.Value > 50 && ad.Spend.Value > 10)
    return NewBudgetInUsd(ad.Budget.Value * 1.3).WithResetAfterHours(6).WithComment("evening push on strong ROI");
return Include();
```
| `CreateCostCap()` | **Clones** the adset as a cost-cap adset (it does not convert the existing one). Cap auto = `floor(PricePerConversion) - 5` cents, limited to at least 3. New budget $50. |
| `CreateCostCapWith(double capCents)` | Same clone, with an explicit cap in cents. |
| `Clone()` | Clone the adset with the source adset's current budget. |
| `CloneWithBudget(int cents)` | Clone with that budget. Used only if > 150 cents, otherwise the source budget. |
| `CloneAsCap(int newBudgetCents)` | Clone as a cost-cap adset with an auto cap (as `CreateCostCap`) and this budget. |
| `CloneWithCap(int capCents, int newBudgetCents)` | Clone as a cost-cap adset with an explicit cap (used if > 3) and budget. |
| `ToAnotherAccount()` | Transfer (rebuild) the offer on another account with new creatives: a new adset, the source stays as it is. Initial budget 200 cents. The target is picked at random from **valid accounts** (see "Which accounts can take an adset" below) where no loaded adset of the same offer runs. If there is none, or the adset's own account is disabled, the adset is dropped. |
| `ToAnotherSpecificAccount(string name)` | Same, to the named account. Pass only a name read from `GetSupportedAccounts(...)` at run time, never a literal. A name that is not a valid account for this adset (unknown, disabled, full, another traffic provider, another account type, or the adset's own account) **silently falls back to a random valid account** other than the adset's own. If there is no valid account at all, nothing is created. Not checked: whether the offer already runs in the named account, so filter that yourself. |
| `ToAnotherAccountWithBudget(int newBudgetInCents, int? capValueInCents = null)` | Same as `ToAnotherAccount()`, but the new adset starts with this budget and, if given, this cost cap (both in cents). The budget must be at least 150 and the cap at least 2, otherwise the script throws (the whole run fails, so clamp computed values yourself). Without a cap the new adset is uncapped. |
| `ToAnotherSpecificAccountWithBudget(string name, int newBudgetInCents, int? capValueInCents = null)` | Same as `ToAnotherSpecificAccount(name)`, with the budget and cap rules of `ToAnotherAccountWithBudget`. |

### Which accounts can take an adset

Accounts are **not interchangeable**. An adset can only go to an account that matches it on **both**:

1. **Traffic provider**: `account.TrafficProvider == ad.TrafficProvider`. A Facebook adset goes only to Facebook accounts, a TikTok adset only to TikTok accounts. Transfers never switch provider.
2. **Account type**: `account.Type == ad.AffiliateModel.AccountType`. Every affiliate is configured for one account family (`FLW`, `OH`, `Yahoo`, `MiraSearch`), and its offers can only run on accounts of that family. An OH adset can't go to an FLW account, even on the same provider.

On top of that the account must be enabled (every account `GetSupportedAccounts` returns is) and have room (`HasValidAdsetsCount()`). So "the division has 12 accounts" usually means only a few are valid targets for a given adset. Always filter per adset, never pick from the full list.

### Accounts the division can use: `GetSupportedAccounts(...)`

`GetSupportedAccounts(Func<TrafficAccount, bool>? predicate = null)` returns the division's **currently enabled** traffic accounts (Facebook and TikTok), optionally filtered. It is the same list publishing picks accounts from, refreshed every few minutes, so use it instead of **hardcoding account names**: accounts get added, disabled and filled up, and a hardcoded list goes stale (a stale name silently falls back to a random account).

Each account has: `Name` (what `ToAnotherSpecificAccount` takes), `ActId`, `TrafficProvider` (must match `ad.TrafficProvider`), `Type` (`TrafficAccountType`, the account family; must match `ad.AffiliateModel.AccountType`), `IsScaleEnabled`, `AdsetCount` (all adsets in CK on that account, any status) and `HasValidAdsetsCount()` (true when the account can still take adsets: empty, or scaling enabled and under 900 adsets).

- The type name `TrafficAccount` is not imported: use `var` (or the full name `CK.TrafficProvidersCore.Models.TrafficAccount` for a typed member).
- Call it in init (once) and keep the result in a member; calling it per adset works but repeats the work.
- Filter **per adset** on its traffic provider and account family (see "Which accounts can take an adset"). A name that fails either check is not an error: the transfer silently goes to a random account instead.

```csharp
#region members
// Valid targets per (traffic provider, account family); an adset may only use its own key.
Dictionary<(TrafficProvider, TrafficAccountType), List<string>> Targets = new();
#endregion

#region init
TagName = "s:replicate";
Targets = GetSupportedAccounts(x => x.HasValidAdsetsCount())
    .GroupBy(x => (x.TrafficProvider, x.Type))
    .ToDictionary(g => g.Key, g => g.Select(x => x.Name).ToList());
#endregion

if (ad.Status != AdsetStatus.Active || ad.Profit.Value < 30 || ad.LastTransferUtcHours < 2) return Ignore();
if (!Targets.TryGetValue((ad.TrafficProvider, ad.AffiliateModel.AccountType), out var names)) return Ignore();
// Accounts where this offer already runs (the adset's own account included)
var offerAccounts = Adsets.Where(x => x.Entry.OfferId == ad.OfferId).Select(x => x.Entry.TrafficAccountName).ToHashSet();
var target = names.FirstOrDefault(x => !offerAccounts.Contains(x));
return target == null ? Ignore() : ToAnotherSpecificAccount(target).WithComment("profit > 30$, replicate to an account without this offer");
```

### `ActionChangeBudgetByPercentageRequest` (all money in cents)

| Property | Default | Meaning |
|---|---|---|
| `Percentage` | `5.0` | `+` increases, `-` decreases. `0` = adset skipped. Step = `ceil(abs(pct)/100 * currentBudgetCents)`. |
| `MinimumChange` | `150` | A step smaller than this becomes exactly this. `0` = no minimum. |
| `MaximumChange` | `10_00` | A step larger than this becomes exactly this. `0` = no maximum. |
| `MinimumBudget` | `150` | The result is never below this. |
| `MaximumBudget` | `300_00` | The result is never above this. **An adset already above it is set down to it, even on an increase.** |
| `ResetAfterHours` | `null` | Hours until the budget goes back, the same as `.WithResetAfterHours` and corrected into 1 to 24 the same way. `null` = no reset. |

If the resulting budget equals the current one, the adset is dropped from the group.

```csharp
return ChangeBudgetByPercentage(new ActionChangeBudgetByPercentageRequest
{
    Percentage = -20, MinimumChange = 2_00, MaximumChange = 20_00, MinimumBudget = 5_00, MaximumBudget = 500_00,
});
```

### Nothing is applied by running the script

Running the script only creates **groups**, one per action type and configuration, named after the run. Nothing changes on Facebook until someone opens the save screen, reviews the groups, and clicks **Execute N actions**. Even then the changes are queued as requests and applied by background workers.

## 3. `ad`: the adset (`StatResponseAdset`)

### Identity and state
| Member | Type | Meaning |
|---|---|---|
| `AdsetId` | string | Traffic-provider adset id. |
| `Status` | `AdsetStatus` | Current status. |
| `TrafficProvider` | `TrafficProvider` | Facebook / Taboola / Tiktok ... |
| `TrafficAccountName`, `TrafficAccountId`, `TrafficCampaignId` | string | Account and campaign. Read and group by them, compare adsets with each other on them, but never compare them to a literal: accounts change. |
| `Origin` | `AdsetOrigin` | How the adset was created (regular publish, clone, cap clone, transfer ...). |
| `OriginalAdsetId` | string? | Adset this one was created from (clone, cap clone, transfer or replicate to another account): the direct parent, so a chain A -> B -> C has C pointing to B. Empty when none. Transfers and replicates carry it only from 2026-09-27; older ones are empty. |
| `IsActiveToday` | bool | **The adset delivered on the current UTC day**: today's stats have spend, impressions, clicks, conversions or revenue. Use it for anything about today (live adsets, clone or replicate sources, today's economics). The list also holds adsets that stopped days ago (their today row is all zeros), and `Status == Active` doesn't prove delivery. False for every adset while no stats of the current UTC day are loaded. |
| `HasStatsForDay(string day)` | bool | The adset delivered on that day (same activity test as `IsActiveToday`). `day`: `"today"` (current UTC day), `yyyy-MM-dd` or `yyyyMMdd` (`KillDateKey`). A day outside the loaded range is false; any other format throws. |
| `IsAdsetDeleted` | bool | **Legacy, always false**: nothing sets it. Don't use it; use `IsActiveToday` / `HasStatsForDay` for delivery and `Status` for the CK status. |
| `CreatedDays` | double | Fractional days since the adset was created. |
| `KillDateKey` | string? | UTC day of the kill as `yyyyMMdd` (no dashes, unlike `History` keys). |
| `LocalHour` | int | Current hour in the adset's country (0-23). Day keys are UTC, so near midnight UTC the country can be on another calendar day. |
| `Tags` | `List<AdsetTag>` | Tags written by scripts (see `TagName` in section 1), newest first, kept for 20 days. Each has `.Name`, `.Count` (how many times it was written) and `.Time` (UTC of the latest write). `.PreviousTimes`: UTC times of the earlier writes, newest first, at most one per hour and at most 50 (writes within an hour of the newest kept one are not kept again), tracked from 2026-10-03, so older writes and `.Count` don't match it. E.g. the write before the latest: `.PreviousTimes.FirstOrDefault()` (`DateTime.MinValue` when there is none); how often a script hit the adset in the last 24h: `.PreviousTimes.Count(t => t > DateTime.UtcNow.AddHours(-24))`. For a cooldown use `GetLastTagInHours`. |

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
| `Affiliate` | int | Affiliate id (a plain number, not an enum). Never compare it to a literal. |
| `AffiliateName` | string | Affiliate name. For reading and grouping only; never compare it to a literal in a script: affiliates are added and removed. Select by `FeedType` / `AccountType` instead. |
| `AffiliateModel.FeedType` | `AffiliateFeedType` | Feed (FLW, OH, Yahoo, ...). |
| `AffiliateModel.AccountType` | `TrafficAccountType` | Account family the affiliate is configured for (FLW, OH, Yahoo, ...). The adset can only be transferred or replicated to accounts of this `Type` **and** of the same `TrafficProvider`. Was `FacebookAccountType` before; that name no longer compiles. |
| `AffiliateModel.Domain`, `.Prefix` | string | Affiliate domain and prefix. |

### Siblings (other loaded adsets of the same offer and country)
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
| `GetLastTagInHours(string tagName)` | Hours since a change with that tag was last applied, `double.MaxValue` if never (tags older than 20 days are dropped). Per-adset cooldown for this script: `if (ad.GetLastTagInHours(TagName) < 6) return Ignore();`. Pass another script's tag to see what it did. |
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

**Time zone:** all dates and day keys are UTC. "Today" is the current UTC day.

One value per loaded day, **newest first**.

| Member | Meaning |
|---|---|
| (implicit `double`) | `ad.ROI > 20` compares the newest day, the same as `.Value`. |
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

Enums change during development: these lists are a snapshot and can be out of date. `get_stat_response_adset_definition` returns the current values (read from the code on every call); to see which values actually occur in the division, run a stats query that returns the distinct values. Affiliates are data, not an enum, and a script never names one: select by `AffiliateModel.FeedType` / `AffiliateModel.AccountType`, and use `get_affiliate_providers` / `get_affiliate_feed_types` for what the division supports.

- `AdsetStatus`: `Unknown`, `Initialized`, `Active`, `Scheduled`, `Killed`, `Paused`, `Terminated` (permanent kill set by a person in the UI; same as Killed for scripts, but no group, budget or cap change is ever applied to it, so filter it out like Killed: `ad.Status is AdsetStatus.Killed or AdsetStatus.Terminated`)
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

To use anything else, write its fully qualified name (e.g. `System.Text.RegularExpressions.Regex`). Don't use affiliate-family helpers that test specific affiliates (`AffiliateProviderExtensions.IsOceanHeroAffiliate(...)` and similar): they depend on a fixed affiliate list. Use `ad.AffiliateModel.FeedType` / `ad.AffiliateModel.AccountType`.

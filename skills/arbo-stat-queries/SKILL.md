---
name: arbo-stat-queries
description: Answer any question about CK adset performance by writing and running "stats queries", C# + LINQ snippets that load the division's adset stats and return named results (run_stat_query, list_stat_queries, get_stat_query, get_stat_response_adset_definition, save_agentic_query, update_agentic_query, delete_agentic_query MCP tools). Use for totals, breakdowns, winners and losers, trends, period comparisons, patterns in killed adsets, or any data question about adsets, and when the user wants help writing, fixing or explaining a query for the Queries editor on the Stats page. Not for scripts that create action groups (kill, pause, budget): that is the arbo-scripts skill.
---

# Stats queries

A stats query is a C# method body that loads the division's adsets, analyses them with LINQ, and returns named results. It is read-only: it never changes an adset. It is how you answer data questions about adsets, and how the user builds their own reusable queries in **Stats → Queries**.

**Call `get_stat_response_adset_definition` once before writing queries** (once per conversation is enough). It is generated from the code, so it is always current: the query API, every `StatResponseAdset` and `AverageValue` member with its type, and a `hint` with the meaning and unit of each member. Hints are authoritative; when they differ from this skill, follow the hints. [reference.md](reference.md) has the same information as a fallback when the tool isn't available.

Read it as an analyst, not as a spell-checker: before the first query, go through the members and pick the ones that carry the answer to the question at hand (which metric over which days, which counts make a ratio trustworthy, which fields describe the adset's size and context, which history members say what was already done to it). Members are added and renamed while CK is developed, so the live definition often holds a better field for the question than the one you remember or the one the examples use (for example `ArticleCategory` next to `Vertical`, `ImagePromptName`, `Snapshots`, `Changes[].Stats`). Reuse that reading for the rest of the session.

## Shape of a query

```csharp
var days = Param("days", 7, "Days of stats to load");
var adsets = await LoadStatsYesterdayWithDays(days);

var active = adsets.Where(x => x.Spend.Overall > 0).ToList();
AddData("adsets", active.Count);
AddData("profit", Math.Round(active.Sum(x => x.Profit.Overall), 2));
AddNote($"Full days only, the {days} days before today.");
```

- The code is the body of an `async` method: use `await` for `LoadStats...()`. No class, no method signature, no `using` lines.
- There is no `ad` variable (that is scripts). You get a `List<StatResponseAdset>` and work with the whole list.
- `AddData(name, value)` returns a result. `value` can be a number, a string, a list or an anonymous object: it is serialized to JSON.
- `AddError(message)` and `AddNote(message)` are messages from the query to its reader, for example "no adsets matched" or "today's data is partial". They are not system errors.
- `Param(name, defaultValue, description)` declares an input (details below).

## Load once, read days from `AverageValue`

One load is enough for any window. Each adset carries every loaded day in its metrics (`x.Profit.History`, one value per day), and the list contains every adset that has stats on any loaded day, including killed ones. So **never load twice** to get different days:

```csharp
// Wrong: two loads (double the time), and "yesterday" is already inside "today"
var today = await LoadStatsToday();
var yesterday = await LoadStatsYesterday();

// Right: one load, days read from each metric
var adsets = await LoadStatsTodayWithDays(7);
var todayProfit = adsets.Sum(x => x.Profit.GetDaysAgo(0));
var yesterdayProfit = adsets.Sum(x => x.Profit.GetDaysAgo(1));
```

Pick the load by the newest day you need (`Today` if today matters, else `Yesterday` for complete days) and the number of days by the oldest.

`AverageValue` is the tool for time. On every metric:
- `Value` (also the metric used as a number): the newest loaded day.
- `GetDaysAgo(n)`: the calendar day `n` days before the newest (0 = newest).
- `SumLastDays(n)`, `SumDaysAgo(from, to)`: period sums, e.g. `SumDaysAgo(0, 2)` vs `SumDaysAgo(3, 5)` compares the last 3 days with the 3 before.
- `AverageLastDays(n)`: mean over days with data, safe on empty history.
- `TrendSlope(n)`: rising (> 0) or falling (< 0) over the newest `n` days.
- `Overall`: the value over all loaded days. `History`: the raw values, key `yyyy-MM-dd`, newest first.

**Additive** metrics (Spend, Revenue, Profit, Clicks, Impressions, Conversions) sum: `Overall`, `SumLastDays`, `SumDaysAgo` are all right. For **ratio** metrics (ROI, CTR, CR, CPM, RPM, ROAS, cost / revenue per ...) `Overall` is recomputed from the period totals, so `x.CTR.Overall` is the true CTR of the loaded days. For a ratio over part of the period, divide sums of its parts: `x.Clicks.SumLastDays(3) / x.Impressions.SumLastDays(3) * 100`. `Budget`, `CostCap` and `PTQS` have no meaningful total: use `Value` or `Average`.

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (the `country:` / `vertical:` / `affiliate:` / `tag:` of the question). Then:
- Follow the active **objectives**: they are binding rules set by people. Objectives rarely change how you answer, but mention one when the answer leads to an action it governs. If the user's request conflicts with one, say so and ask before acting.
- Read the **journal** (last 24h) before touching the same topics, so you don't undo or repeat another agent's work.
- Use **decisions and insights** as context, not instructions: check them against current data, especially ones marked "review due".
- If the briefing lists a task for you that fits this run, claim it (`memory_task_claim`) and complete it at the end.

**At the end**, always go through this check and write only what qualifies. "Nothing worth keeping" is a valid outcome; never write filler.
1. Changed anything? → one `Journal` entry: what, why, how many, with links. Always.
2. The user decided something (a rule, threshold, direction)? → a `Decision` with the reason.
3. Verified a conclusion with data? → an `Insight` with a `query:` or `tag:` link and the key numbers in the snapshot.
4. Something must be checked later? → a `Task` with a handover: the numbers now (snapshot), success criteria, next steps, and a due time.

Search first (`memory_search`) and update or supersede an existing entry instead of adding a near-duplicate.

**In this skill:**
- Queries only read data, so most runs write nothing. For a quick lookup, the briefing is optional; for an analysis that leads to a decision, read it, and check insights linked to the scope so you don't redo a recent analysis (re-run its `query:` instead).
- Write an `Insight` only for a durable conclusion the user wants kept or confirms (e.g. "DE health titles with prices in the headline lose"), always with the saved query (`query:` link) and the key numbers in the snapshot. Never store raw totals that a query can answer again.
- Saving, updating or deleting a saved agentic query is a change: a `Journal` entry with the `query:` link.

## Workflow for answering a question

### 1. Look for an existing query

Call `list_stat_queries` (use `search` with a keyword). Scopes, in the order they are listed:
- **agentic**: the shared library written by agents, usable in every division. Prefer these.
- **division**: written by people of this division. Useful, but can depend on the division's specifics, so read the code (`get_stat_query`) before trusting it for a different question.
- **public**: shared by other divisions.

If one fits, run it with `run_stat_query` (`queryId` or `queryName`) and pass `parameters` for its inputs instead of writing new code.

### 2. Otherwise write the query

- Decide the window first and load **once** (see above). All dates are **UTC**: "today" is the current UTC day and is **incomplete** until it ends (near midnight UTC most adsets' `LocalHour` can already be late evening or the next day): use `LoadStatsToday...()` when today matters, `LoadStatsYesterday...()` when only full days count. Say which you used.
- Aggregate in the query, not in your head. Return totals, breakdowns and a short list of example adsets, not every adset.
- Return only the fields you need, rounded: `Math.Round(x, 2)`. Values are serialized with 2 decimals, so return percentages (`12.34`) rather than tiny fractions (`0.001234`).
- Limit lists with `OrderBy...().Take(n)`.
- Guard against empty data: `DefaultIfEmpty()`, `?.`, `Where(x => x.Spend.Overall > 0)` before dividing. One exception stops the **whole** query (unlike scripts, where only that adset is skipped); the results added before it are still returned, together with the exception.

### 3. Run and fix

`run_stat_query` with `code` (or `queryId` / `queryName`) and `parameters`, all as top-level arguments: `code` is a plain string, `parameters` a JSON object such as `{"days": 7}`. The response has one of:
- `compileErrors`: line and column count from the start of your code. Fix and run again.
- `parameterErrors`: an unknown parameter name or a value of the wrong type.
- `results`, plus `errors` / `notes` from your code, `warnings` from the system (data skipped for being over the limits) and `fatalException` when the query threw, ran over 2 minutes, or recursed too deep ("Recursion too deep").
- `fatalException` starting with "The server is busy": no query slot freed up within 45 seconds, so the query did not run. Wait a minute and retry. It is not a problem with your code.
- `fatalException` starting with "The server is low on memory": the query did not run. Retry in a few minutes and, if you can, load fewer days. It is not a problem with your code.

If a result was skipped for size, narrow it (fewer items, fewer fields) and run again.

### 4. Answer

Base the answer on the returned numbers, state the window and units, and mention caveats (partial day, killed adsets included, thin data). If the user wants to act (kill, change budgets), don't do it from query results alone: the kill and budget tools require `get_adset_details` with `includeChanges=true` first, and only when the user explicitly asks.

### 5. Save it when it is worth reusing

Save to the agentic library with `save_agentic_query` when the query answers a question that will come back (a standard breakdown, a recurring health check), not for one-off questions.
- **Generalise with `Param`** instead of hard-coding countries, days or thresholds, so one query serves many questions. Account, affiliate, vertical, theme and feed names are data that changes: never write them from memory, take them from a distinct-values query or from the user, and prefer a property (`AffiliateModel.FeedType`, `ArticleCategory`, `TrafficProvider`) when one expresses the same thing.
- **Name and describe it for someone searching later.** Name: what it answers ("Losers by country over N days"). Description (40+ characters): which adsets it looks at, what it returns, what each parameter means.
- **Check first** with `list_stat_queries` that a similar agentic query doesn't exist; if it does, improve it with `update_agentic_query` (read it with `get_stat_query` first, code replaces the whole code).
- The library holds **50** agentic queries (`agenticCount` / `agenticLimit` in `list_stat_queries`). When it is full, delete ones that are unused or superseded with `delete_agentic_query`.
- Agents can only change or delete **agentic** queries. Division queries belong to people.
- Dashboards and widgets (the **arbo-dashboards** skill) load agentic queries by id and depend on their result names and row keys. Before `update_agentic_query` or `delete_agentic_query`, check `list_widgets` for views whose `queryIds` contain the query, and keep it compatible or update those views too.

## Parameters

```csharp
var country = Param("country", "", "ISO country code, empty for all countries");
var days = Param("days", 7, "Days of stats to load");
var minSpend = Param("minSpend", 5.0, "Minimum spend in dollars over the period");
var activeOnly = Param("activeOnly", true, "Only adsets that are active now");
```

- Types: string, int, double, bool, inferred from the default (`5.0` is a double, `5` an int).
- Name, default and description must be **literals**, because they are read from the code without running it. `Param(someVariable, 3)` is an error, and so is a name used twice.
- A value that isn't passed uses the default. When running, pass `parameters: { "country": "DE", "days": 14 }`.

## Queries and scripts work together

Queries gather intelligence; arbo scripts (the **arbo-scripts** skill) act on it in the Scripts editor. Both work on the same `StatResponseAdset` and `AverageValue`, so everything here about metrics, units, `Overall`, days and enums holds for scripts too. A typical flow:
1. Explore with queries: find where the losses or wins are, which thresholds separate good from bad adsets, how many adsets a rule would catch. Look for thresholds that scale with the adset (spend as a multiple of its budget or cap, loss as a fraction of its daily budget, ROI against the vertical or country median, a minimum number of conversions) rather than one flat dollar figure for adsets of very different sizes, and report the distribution (quartiles, medians per group), not just a cutoff that happens to fit today's list.
2. Check the rule as a query before it becomes a script: the same conditions in a `Where`, returning the count, the spend at stake and a few examples.
3. Write the script with the arbo-scripts skill using the thresholds the data supports, and tell the user what the query showed (how many adsets, how much spend).
4. Test the script before proposing it (this is the only use of `RunTestScript`; never use it to answer questions about adsets): in a query, select the adsets that should get each action independently of the script (adsets the user named, or the goal written as a plain filter, not the script's conditions copied), run `RunTestScript` and `Compare` each action, plus `"None"` for adsets that must stay untouched. Fix until every comparison `IsMatch`, and show the user the kills and budget changes with their comments.

```csharp
var adsets = (await LoadStatsToday()).Where(x => x.Status == AdsetStatus.Active && x.IsActiveToday).ToList();
var test = await RunTestScript("""
    if (ad.Spend.Overall > 50 && ad.ROI.Overall < -30) return Kill().WithComment("ROI < -30% after $50");
    return Ignore();
    """, adsets);
if (!test.IsSuccess) { AddData("errors", test.Errors); return; }

var shouldKill = adsets.Where(x => x.Spend.Overall > 50 && x.Profit.Overall < -20).Select(x => x.AdsetId);
var kill = test.Compare("Kill", shouldKill);
AddData("counts", test.Counts);
AddData("kill", new { kill.IsMatch, kill.ExpectedCount, kill.ActualCount,
    missed = kill.Missed.Select(x => new { x.AdsetId, x.ActionName, spend = x.Adset.Spend.Overall, profit = x.Adset.Profit.Overall }),
    unexpected = kill.Unexpected.Select(x => new { x.AdsetId, comment = x.Actions[0].Comment, spend = x.Adset.Spend.Overall, profit = x.Adset.Profit.Overall }) });
```

**Tags and comments are the memory of past decisions.** `Tags` on an adset (`.Name`, `.Count`, `.Time`; there is no `TagName` member) group adsets by the idea behind them: the tag they were launched with (`t:...` from title creation) and the tags of scripts and AI changes that touched them (`s:...`). `Changes[].Comment` holds the short reason, and often the expected outcome, written with each change. To judge whether an optimization or a launch worked, group by tag and compare what happened after the changes with what their comments expected.

**`ImagePromptName` says which image prompt made the creative.** Group by it (`x.ImagePromptName ?? "default"`) to compare prompts on ROI, CTR and profit. Only compare adsets created after tracking started (2026-09-26); older ones are `null` too and would inflate the `default` group. Compare within the same division, affiliate or vertical, because prompts can be filtered to specific affiliates or feeds.

Scripts see the days loaded on the Stats page (6 by default) and run per adset, so a condition written for a query (`x.Profit.SumDaysAgo(0, 2) < 0`) becomes `ad.Profit.SumDaysAgo(0, 2) < 0` in the script.

## Helping the user write a division query

When the user wants their own query for the **Queries** editor (Stats page → Queries):
- Output only the method body in one fenced `csharp` block, ready to paste, with short `//` comments on non-obvious lines.
- Use `Param` for the values they will want to change, so the editor shows inputs for them.
- Explain in a few bullets what it returns, the window and the units.
- Tell them how to use it: paste it into Stats → Queries, click **Run** (parameters show as inputs above the editor, empty = default), give it a name and **Save**. Results show as cards under the editor.
- You can run it with `run_stat_query` first to check it compiles and returns sensible data. You don't save division queries: the user saves them in the editor.

## Things that are easy to get wrong

- **The list holds every adset with stats on any loaded day, grouped together**, also ones killed or stopped days ago; for the days after they stopped, their values are 0 (query loads even give them an all-zero row for the newest day). `Status == AdsetStatus.Active` is CK's status and doesn't prove the adset is delivering. **For "today" / "currently running" questions filter with `x.IsActiveToday`** (delivered on the current UTC day); for another day use `x.HasStatsForDay(day)`; for the period, `x.Spend.Overall > 0`. Clone and replicate candidates need `x.Status == AdsetStatus.Active && !x.IsArticleDeleted && x.IsActiveToday`.
- **`IsAdsetDeleted` is always false** (legacy). Don't filter on it.
- **`x.Spend` as a number is the newest loaded day**, which is today for `LoadStatsToday...()`. Use `.Overall` or `SumLastDays(n)` for periods.
- **Ratios over part of the period**: `SumLastDays` / `SumDaysAgo` on a ratio sums daily ratios; divide sums of the underlying metrics instead. `.Overall` of a ratio is fine.
- **`Yesterday` is the second-newest day that has data**, not always the calendar day before. `GetDaysAgo(1)` is the calendar day before.
- **`GetAverageForDays` throws on empty history**; use `AverageLastDays`.
- **Use our tracking metrics** (`Spend`, `Revenue`, `Clicks`, `Impressions`, `Conversions`). The `...Traffic` copies (`SpendTraffic`, `ClicksTraffic`, ...) are the traffic provider's own numbers, kept for comparing in the UI; they can differ and shouldn't be used for analysis.
- **Date keys come in two formats**: `History` keys are `yyyy-MM-dd`, `KillDateKey` is `yyyyMMdd`. Don't parse them by hand: `x.Spend.GetDaysFrom(x.KillDateKey, -1)` (the day before the kill), `ShiftDateKey(key, days)`, `DaysBetween(from, to)` accept both.
- **Units**: stats money (`Spend`, `Revenue`, `Profit`, `Budget`) is dollars; `CostCap`, `CostPerVisit`, `CostPerConversion`, `PricePerConversion` are cents; ROI, CTR, CR are percent. Details in the reference.
- **`Name` is the theme or vertical name**, not the adset name. Use `Vertical.Name` for the vertical.
- **Enums change during development.** Don't trust enum values from memory or from this skill: `get_stat_response_adset_definition` lists the current ones. To know which values actually occur, query them first (example below). Affiliates are data, not an enum: filter on `AffiliateName` or `AffiliateModel.FeedType`.
- **Loading is the slow part.** Load once and reuse the list. Stats are cached for a minute, so repeating a query soon after is fast. A query that runs over 2 minutes is stopped.
- **Run queries one after another, not in parallel.** At most 8 queries run at once on the server (6 per division), shared with everyone else; the rest wait up to 45 seconds. A note "Waited N seconds for a free query slot" means the server was busy. Combine questions into one query instead of firing many at once.
- **Output limits**: at most 50 `AddData` entries, 20,000 characters per value, 100,000 in total. Over that, the entry is skipped with a warning.

## Examples

Totals and a country breakdown for the last 7 full days, best and worst 5:

```csharp
var days = Param("days", 7, "Full days to load, ending yesterday");
var adsets = (await LoadStatsYesterdayWithDays(days)).Where(x => x.Spend.Overall > 0).ToList();

var spend = adsets.Sum(x => x.Spend.Overall);
var profit = adsets.Sum(x => x.Profit.Overall);
AddData("totals", new
{
    adsets = adsets.Count,
    spend = Math.Round(spend, 2),
    profit = Math.Round(profit, 2),
    roi = spend > 0 ? Math.Round(profit / spend * 100, 2) : 0,
});

var countries = adsets
    .GroupBy(x => x.Country)
    .Select(g => new
    {
        country = g.Key,
        adsets = g.Count(),
        spend = Math.Round(g.Sum(x => x.Spend.Overall), 2),
        profit = Math.Round(g.Sum(x => x.Profit.Overall), 2),
    })
    .OrderByDescending(x => x.profit)
    .ToList();
AddData("bestCountries", countries.Take(5));
AddData("worstCountries", countries.AsEnumerable().Reverse().Take(5));
```

Compare the last N full days with the N days before, per vertical, from one load:

```csharp
var days = Param("days", 3, "Days in each period");
var adsets = await LoadStatsYesterdayWithDays(days * 2);

var verticals = adsets
    .GroupBy(x => x.Vertical.Name)
    .Select(g => new
    {
        vertical = g.Key,
        profitRecent = Math.Round(g.Sum(x => x.Profit.SumDaysAgo(0, days - 1)), 2),
        profitBefore = Math.Round(g.Sum(x => x.Profit.SumDaysAgo(days, days * 2 - 1)), 2),
    })
    .Where(x => x.profitRecent != 0 || x.profitBefore != 0)
    .OrderBy(x => x.profitRecent - x.profitBefore)
    .ToList();
AddData("biggestDrops", verticals.Take(10));
AddNote($"Recent = the {days} days before today, before = the {days} days before that.");
```

Today so far against yesterday's full day, from one load (stats are per day, so "yesterday at this hour" isn't available):

```csharp
var adsets = await LoadStatsTodayWithDays(2);
var active = adsets.Where(x => x.Spend.GetDaysAgo(0) > 0 || x.Spend.GetDaysAgo(1) > 0).ToList();
AddData("profitToday", Math.Round(active.Sum(x => x.Profit.GetDaysAgo(0)), 2));
AddData("profitYesterday", Math.Round(active.Sum(x => x.Profit.GetDaysAgo(1)), 2));
AddData("ctrToday", Math.Round(active.Sum(x => x.Clicks.GetDaysAgo(0)) / Math.Max(1, active.Sum(x => x.Impressions.GetDaysAgo(0))) * 100, 2));
AddNote("Today is partial, yesterday is a full day.");
```

Top N per group, with exactly the fields needed. This is the typical shape: a `Param` for the threshold, a filter, a grouping, a small projection, and one `AddData` per group:

```csharp
var adsets = await LoadStatsToday();
var minimumRoi = Param("minimumRoi", 20, "Minimum ROI in percent today");
var top = Param("top", 5, "Adsets per feed type");

foreach (var feedGroup in adsets.GroupBy(x => x.AffiliateModel.FeedType))
{
    var best = feedGroup
        .Where(x => x.ROI >= minimumRoi && x.Spend > 0.5)   // ROI and Spend as numbers = today
        .OrderByDescending(x => x.Profit.Value)
        .Take(top)
        .Select(x => new
        {
            adsetId = x.AdsetId,
            title = x.Anchor,                                // long text: only for content analysis
            profit = Math.Round(x.Profit.Value, 2),
        })
        .ToList();                                           // a new list per group

    if (best.Count > 0)
        AddData($"{feedGroup.Key}-adsets", best);
}
```

Build the list inside the loop. A list declared once outside it keeps growing, so every group's entry would also contain the adsets of the groups before it.

Which enum values actually occur (run this before filtering on an enum you aren't sure about):

```csharp
var adsets = await LoadStatsToday();
AddData("feedTypes", adsets.GroupBy(x => x.AffiliateModel.FeedType.ToString()).ToDictionary(g => g.Key, g => g.Count()));
AddData("affiliates", adsets.GroupBy(x => x.AffiliateName).ToDictionary(g => g.Key, g => g.Count()));
AddData("statuses", adsets.GroupBy(x => x.Status.ToString()).ToDictionary(g => g.Key, g => g.Count()));
AddData("origins", adsets.GroupBy(x => x.Origin.ToString()).ToDictionary(g => g.Key, g => g.Count()));
```

Active adsets with a falling CTR, enough data to judge, top 10 by spend today:

```csharp
var adsets = await LoadStatsToday();
var falling = adsets
    .Where(x => x.Status == AdsetStatus.Active && x.Spend > 5 && x.CTR.HistoryCount >= 3)
    .Where(x => x.CTR < x.CTR.AverageLastDays(7) * 0.8)
    .OrderByDescending(x => x.Spend.Value)
    .Take(10)
    .Select(x => new
    {
        x.AdsetId,
        x.Country,
        vertical = x.Vertical.Name,
        ctrToday = Math.Round(x.CTR.Value, 2),
        ctrAverage = Math.Round(x.CTR.AverageLastDays(7), 2),
        spendToday = Math.Round(x.Spend.Value, 2),
    })
    .ToList();

if (falling.Count == 0)
    AddNote("No active adset has today's CTR 20% below its average.");
AddData("fallingCtr", falling);
AddNote("Today's stats are partial.");
```

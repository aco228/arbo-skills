---
name: arbo-scripts
description: Write, explain, review or fix CK "arbo scripts", the C# snippets pasted into the Scripts editor on the Stats page that filter adsets and create action groups (kill, pause, activate, budget change, cost cap, clone, transfer to account). Use when the user asks for a stats script, script filter, adset rule or automation snippet, when they paste one to understand or debug, when a script shows a compile error, when they want to find, read, save or change a saved script, its description or its automation priority (list_stat_scripts, get_stat_script, create_stat_script, update_stat_script_code MCP tools). Not for querying or analysing adsets: that is done with stats queries (run_stat_query).
---

# Arbo scripts

You help the user write scripts for the **Scripts** editor on the CK Stats page. A script is mostly a C# method body. It runs once per loaded adset and returns what to do with that adset: show it, hide it, or put it into an action group (kill, pause, budget change, clone, ...). Optional `#region members` (fields and helpers) and `#region init` (runs once before the adsets) handle decisions that need all adsets at once.

The complete API is in [api-reference.md](api-reference.md). Read it before writing any script, and only use members listed there. Don't guess member names, and don't look for project source files. When the CK MCP tools are available, `get_stat_response_adset_definition` returns the current members of `ad` (`StatResponseAdset`) and `AverageValue` with a `hint` giving each one's meaning and unit, and the current enum values. It is generated from the code, so follow it when it differs from the reference.

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (`script:<name>` of the script, plus its `country:` / `vertical:` if it is scoped). Then:
- Follow the active **objectives**: they are binding rules set by people. A script that scales, activates or clones falls under a `scaling` objective; one that kills or pauses under `kill-policy`. If a script (new or existing) would act against an active objective, point it out. If the user's request conflicts with one, say so and ask before acting.
- Read the **journal** (last 24h) before touching the same scripts, so you don't undo or repeat another agent's work.
- Use **decisions and insights** as context, not instructions: check them against current data, especially ones marked "review due".
- If the briefing lists a task for you that fits this run, claim it (`memory_task_claim`) and complete it at the end.

**At the end**, always go through this check and write only what qualifies. "Nothing worth keeping" is a valid outcome; never write filler.
1. Changed anything? → one `Journal` entry: what, why, how many, with links. Always.
2. The user decided something (a rule, threshold, direction)? → a `Decision` with the reason.
3. Verified a conclusion with data? → an `Insight` with a `query:` or `tag:` link and the key numbers in the snapshot.
4. Something must be checked later? → a `Task` with a handover: the numbers now (snapshot), success criteria, next steps, and a due time.

Search first (`memory_search`) and update or supersede an existing entry instead of adding a near-duplicate.

**In this skill:**
- At the start, check the journal and decisions linked to the script (`script:<name>`): why it has its thresholds, what was changed recently and by whom.
- After saving or changing a saved script: a `Journal` entry with the `script:` link, what changed and why (thresholds, scope, priority, schedule).
- Thresholds or rules chosen with the user ("kill only after $15 spend") are a `Decision` linked to the script.
- When a script is (or will be) automated: a `Task` to check its effect after a few days (how many adsets it acted on, outcome of its tag), with the expected effect in the success criteria.
- Writing or explaining a script in chat without saving it changes nothing: no journal.

## Workflow

### 1. Understand the rule

Establish, asking only for what is missing:
- **Which adsets.** Conditions on status, country, vertical or theme, affiliate, account, age, cost cap, origin, and so on.
- **Which signal.** Which metric, over which window (today, `Yesterday`, the last N days, `Overall`), and the thresholds.
- **What to do** with the matches, and what to do with the rest: show them (`Include()`) or hide them (`Ignore()`).
- **Guards.** A minimum spend before judging ROI, time since the last budget change, whether the adset is currently active, and so on.

If the user is vague ("kill the bad ones"), propose concrete thresholds and state them so they can adjust.

### 2. Write the script

Rules that must hold:
- Output **only the script**: the body, plus the optional `#region members` / `#region init` blocks at the top. No class, no method signature, no `using` lines.
- Use the regions only when the rule needs more than one adset at a time (top N, ranking, totals, a cap on how many adsets to touch) or needs to skip the whole run (`CanRun`). A per-adset rule stays a plain body.
- Compute in init, read in the body: e.g. build a `HashSet<string>` of adset ids in init, then `return ToKill.Contains(ad.AdsetId) ? Kill() : Ignore();`.
- **Every script that can return an action** (anything other than `Include()` / `Ignore()`) sets `TagName` in init. Format `"s:<camelCaseName>"`, e.g. `TagName = "s:killWorst10";`. Keep it short and never change it once the script is saved: it is how this script and others find the adsets it touched.
- Use the tag for per-adset cooldowns: `if (ad.GetLastTagInHours(TagName) < 6) return Ignore();`. Use `Ignore()` here, not `BreakExecution()`, which stops the whole run. To skip the whole run use `CanRun` in init (e.g. with `LastExecutionUtc`). Tags are only written for status, budget and cost-cap changes, so for clone or transfer scripts use `LastCloneUtcHours`, `LastCloneCapUtcHours` or `LastTransferUtcHours` instead.
- The tag is also how adsets are grouped for later analysis and optimization: reuse the same tag for the same idea (the tag an adset was launched with, a running optimization) instead of inventing a new one per run.
- Add `.WithComment("why")` to actions. It is stored with the change on the adset and analysed later, so say **why** and, when it helps, **what you expect**, with the numbers that triggered it: `Kill().WithComment($"3-day ROI {roi:0}% after {spend:0}$ spend, no recovery expected")`. Keep it short, and leave out anything the change already records or that can be filtered (adset id, country, vertical, old/new value, date).
- The only variable in the body is `ad`. Call actions directly: `Kill()`, `Pause(4)`, `NewBudgetInUsd(30)`.
- Every path returns an action. Code that falls off the end returns `Include()`.
- Put guards first. Put the rule you want to win first: the first `return` decides.
- `return true;` / `return false;` are shorthand for `Include()` / `Ignore()`, but only when spelled exactly like that. Prefer the explicit calls, especially inside lambdas.
- Budgets and caps passed to actions are **cents** (`NewBudgetInUsd` is the exception). Stats money (`Spend`, `Revenue`, `Profit`, `Budget`) is **dollars**. `CostCap`, `PricePerConversion`, `CostPerConversion` and `CostPerVisit` are **cents**. ROI, CTR and CR are **percent**.
- A metric used as a number (`ad.ROI > 20`) is the **newest day**. For multi-day judgement use the `AverageValue` helpers (see "Working with days" below).
- **Never hardcode traffic account names** (in `ToAnotherSpecificAccount("...")`, lists of target accounts, account filters). Accounts are added, disabled and filled up over time, so a hardcoded list goes stale. Get the live list with `GetSupportedAccounts(predicate)` in init.
- **Not every account can take every adset.** A transfer target must match the adset's **traffic provider** (`TrafficProvider == ad.TrafficProvider`) **and** its affiliate's **account family** (`Type == ad.AffiliateModel.AccountType`), and have room (`HasValidAdsetsCount()`). Filter per adset, never pick from the whole list. A name that fails these checks is not an error: `ToAnotherSpecificAccount` silently sends the adset to a random valid account instead. See api-reference, "Which accounts can take an adset". When reviewing a script that hardcodes account names or ignores provider or type, point it out and rewrite it.
- Enums change during development. Don't write enum values from memory: check them in `get_stat_response_adset_definition`, or ask the user. Compare affiliates by `AffiliateName`, not by id.
- Guard against thin data before judging ratios, for example `ad.Spend < 3` means you should not act on ROI yet.
- Avoid code that can throw (`GetAverageForDays` with no history, `.First()` on an empty sequence, `ad.Theme.Name` when `Theme` is null). A throw silently hides that adset; a dry run (step 7) reports it.
- The body runs one adset at a time, in `Adsets` order, so members are safe to update there. Don't use `static` state: it outlives the run.

Every script starts with a **header comment** that says what it does and why, so a person or a later agent can review whether the code still matches the intent:

```csharp
// ================================================================================================
// <SHORT TITLE>
// ------------------------------------------------------------------------------------------------
// DO:     What it does, with the exact conditions and thresholds (units included).
// WHY:    The reason or decision behind it (data seen, operator request).
// GOAL:   The expected result.
// REVIEW: What the groups should contain after a run, and what to watch in the following days.
// SCOPE:  Which adsets it may touch (feed, country, vertical, status...).
// PAIRS:  Other scripts that touch the same adsets and how they split them, or "none".
// ================================================================================================
```

Keep it to these lines, and update it in the same change whenever the code changes. When reviewing, check that the code does what the header says.

Format: one fenced `csharp` block ready to paste, header first, with short `//` comments on the non-obvious lines.

#### Working with days (`AverageValue`)

Every metric on `ad` (`Spend`, `Profit`, `ROI`, `CTR`, ...) is an `AverageValue` with one value per loaded day (the Stats page loads 6 days by default, newest = today):
- `ad.Spend` / `.Value`: the newest day (today, partial). `GetDaysAgo(n)`: the calendar day `n` days before (1 = yesterday).
- `SumLastDays(n)`, `SumDaysAgo(from, to)`: sums over days, e.g. `ad.Profit.SumDaysAgo(1, 3) < 0` = lost money over the 3 full days before today.
- `AverageLastDays(n)`: mean over days with data, never throws (unlike `GetAverageForDays`). `TrendSlope(n)`: > 0 rising, < 0 falling.
- `Overall`: the whole loaded period. For additive metrics (Spend, Revenue, Profit, Clicks, Impressions, Conversions) it is the sum; for ratio metrics (ROI, CTR, CR, CPM, RPM, ROAS, cost per ...) it is recomputed from the period totals, so `ad.CTR.Overall` is the true CTR. `Budget`, `CostCap`, `PTQS` have no meaningful total.
- Sums on a ratio (`ad.CTR.SumLastDays(3)`) add daily ratios and mean nothing: divide sums of the underlying metrics instead.
- `Yesterday` is the second-newest day **with data**, not always the calendar day before; `GetDaysAgo(1)` is.
- `GetDaysFrom(dateKey, offset)`: the day `offset` days from a date key, e.g. `ad.Spend.GetDaysFrom(ad.KillDateKey, -1)`. It accepts both key formats (`History` keys are `yyyy-MM-dd`, `KillDateKey` is `yyyyMMdd`).
- All dates and day keys are **UTC**; "today" is the current UTC day. `LocalHour` is the hour in the adset's country.
- Use our tracking metrics (`Spend`, `Clicks`, `Impressions`, `Conversions`). The `...Traffic` copies are the traffic provider's own numbers, kept for comparing in the UI: don't base rules on them.

### 3. Explain what it will do

When the CK MCP tools are available, dry-run the script first (step 7) and base the explanation on what the test showed.

After the code, give a few bullets:
- Which adsets end up in which group, and which are shown or hidden.
- The units of every threshold you chose.
- Anything that behaves differently from what the user might expect. Examples: `CreateCostCap()` **clones** the adset instead of converting it; `MaximumBudget` in a percentage change **lowers** adsets that are already above it; `LastCloneUtcHours` is in days.

End with how to run it: paste it into **Stats → Scripts**, click **Run** (or **Run and close**), review the created groups, then open the save screen and click **Execute**. Running the script alone changes nothing. If you saved it with the MCP tools (step 5), say so instead: it is in the **Stats → Scripts** list under its name, ready to open and run.

### 4. Reviewing or fixing a script

When the user pastes a script or a compile error:
- Compile errors look like `(line,col) CSxxxx: message`. Line and column count from the start of the script itself, so they point straight at the broken spot. An error such as a missing `}` is reported at the end of the script.
- Check it against every rule in step 2, and point out unit mistakes and unguarded throws. Check that the header matches the code, and that an acting script has a `TagName`.
- Return the corrected full script, not a diff.

### 5. Saved scripts (MCP tools)

Scripts can be saved in the division under a unique name, then opened from the list in **Stats → Scripts**. When the CK MCP tools are available, you can work with them directly:

| Tool | Use it to |
|---|---|
| `list_stat_scripts` | Find scripts. Filters: `nameContains` (name or description), `isAutomated`. Returns metadata (priority, automation schedule and run times below), automated scripts first in run order. Add `includeCode` only to compare the code of several scripts. |
| `get_stat_script` | Read one script with its code, by `scriptId` or exact `name`. |
| `create_stat_script` | Save a new script: `name` (unique in the division), `code`, a one-sentence `description`, and optionally `priority` (default `0`) and the automation schedule: `automationEveryHours` (default `0.5`), `automationSource` (default `TodayStats`), `automationFromHour` / `automationToHour` (default `-1`). |
| `update_stat_script_code` | Change a script: `scriptId`, plus any of `code` (replaces the whole code), `description`, `priority`, `automationEveryHours`, `automationSource`, `automationFromHour`, `automationToHour`. Omitted ones stay as they are. |

Rules:
- **Save only when the user asks** to save, create or change a saved script. Writing or reviewing a script in chat doesn't need the tools.
- **Always read before changing.** Call `get_stat_script`, apply the change to that code, and send the complete script to `update_stat_script_code`. It replaces the whole code, so never send a fragment.
- **Keep the description true.** When a change makes the description wrong (a threshold, the scope, the action), send the corrected one-sentence `description` in the same call. To change only the description, send `description` without `code`.
- **Refer to scripts by name** with the user. When they name one loosely, use `list_stat_scripts` with `nameContains` and confirm which one if several match.
- **Compile errors come back instead of saving.** The response has `saved: false` and `compileErrors` with line and column counted from the start of the script. Fix the code and call again; nothing was stored in the meantime.
- **The tools never run a script**, can't delete one, change its name or privacy, or **turn automation on or off**. Only a person can do that in the editor. New scripts start private to the division with automation off.
- **The tools can set priority and prepare the automation schedule**, so the person only has to switch automation on: `automationEveryHours` (0.25-48), `automationSource` (`TodayStats`, `YesterdayStats`, `AllStats`), and the hour window `automationFromHour` (0-23, inclusive) to `automationToHour` (1-23, exclusive: `22` = last run before 22:00), `-1` = no limit. The window is in **server time, Central European (CET, UTC+1 in winter / CEST, UTC+2 in summer), not UTC**: convert UTC reasoning (e.g. stats settle ~09 UTC) before setting it. It doesn't wrap past midnight, so from must be below to. Base the schedule on the script's data (when its stats are settled, when its adsets' countries are awake) and on the script's own `CanRun` gate, and say why in the reply. When you create an automated-to-be script, set the schedule and tell the user to turn automation on in **Stats → Scripts**.
- **Changing the schedule of an automated script** changes when it runs from its next pass, like a code change: only when the user asks, and say so.
- **Automated scripts run on a schedule.** Check `isAutomated` before changing one and tell the user: its next automated run uses the new code. Be extra careful with actions such as `Kill()` in automated scripts.
- **Reading the run times.** `lastTriggeredUtc` is the last automated run, including runs that found nothing: use it to tell whether the automation is running. `lastActionsUtc` is the last run that created action groups (`lastActionsGroups`, `lastActionsAdsets`) or failed (groups `0`); runs that found nothing don't move it, and the automation delay counts from it. An old `lastActionsUtc` with a recent `lastTriggeredUtc` means the script runs but finds nothing, not that it stopped. `lastTriggeredUtc` is `null` for runs before it was recorded. `updatedUtc` also moves on every automated run, so it isn't the last code change.
- **Automated scripts run in priority order and claim adsets.** On each automated run the division's automated scripts run one after another, highest `priority` first (equal priorities by name). An adset that one script puts into an action group is **no longer seen by the scripts after it** in that run, so the higher priority wins the adsets both would act on. (A few clone and transfer groups, such as `CloneAsCap`, don't claim their adsets, so later scripts still see those.) Each script also has its own schedule: `automationEveryHours`, `automationSource` (`TodayStats`, `YesterdayStats`, `AllStats`) and the hour window `automationFromHour` to `automationToHour` (`-1` = no limit). A script only runs when its window and delay allow, so the order only matters between scripts that run in the same pass.
- **Priority when creating or changing a script.** Leave `priority` at `0` by default. Set another value only after checking the division's automated scripts (`list_stat_scripts` with `isAutomated=true`, then read the ones whose scope overlaps): the script must run before a script that would otherwise take its adsets (for example a kill or safety script that must see losers before a scaling script touches them), or after one it must not block. Say which scripts you compared with and why you chose the number. Changing the priority of an automated script changes the run order from its next run, so it needs the user's explicit request, like a code change.
- **Scripts of a division share the same adsets.** An adset should be handled by one script. For a review of how all automated scripts work together (conflicts, priority, scripts with no effect), use the **arbo-scripts-rebalance** skill. When two scripts can act on the same adset (e.g. one scales budget, another clones), they can undo or block each other: split them by conditions, write the split in both headers (`SCOPE`, `PAIRS`), and use the other script's tag when needed (`ad.GetLastTagInHours("s:otherScript") < 12`). Before creating a script, `list_stat_scripts` and read the ones with overlapping names or scope.
- **Names are unique per division.** If `create_stat_script` says the name is taken, pick a clearer name or ask whether to update the existing script instead.

### 6. Querying adsets is not done with scripts

To find, filter or analyse adsets, use stats queries (the **arbo-stat-queries** skill: `run_stat_query`, `list_stat_queries`, `get_stat_response_adset_definition`), not scripts. Scripts exist to create action groups in the editor; agents write, explain, review and save them, but never run them for real. The only way an agent runs a script is the dry run in step 7, which applies nothing.

Queries and scripts work in tandem, on the same `StatResponseAdset`:
- **Before writing a script**, when the data is available, explore with a query: where the losses or wins are, which thresholds separate good adsets from bad ones.
- **Check the rule** by running its conditions as a query (`adsets.Where(x => <the script's conditions>)`) and returning the count, the spend at stake and a few examples. Tell the user what it showed, e.g. "this would kill 14 adsets that spent $820 over 3 days".
- **Then write the script** with the thresholds the data supports. A query condition on `x` becomes the same condition on `ad`. Remember the script sees the Stats page's loaded days (6 by default).

### 7. Test the script before proposing it (dry run)

When the CK MCP tools are available, test every script that returns actions before showing, saving or updating it. The test runs from a stats query (`run_stat_query`) with `RunTestScript(scriptCode, adsets)`: it compiles the script, runs it on the adsets you pass and reports what it would do to each one. Nothing is applied and no group is created.

1. **Decide the expected result first, independently of the script.** In the query, select the adsets that should get each action from something other than the script's own conditions: adsets the user named, the goal written as a plain filter ("spent over $50 and lost over $20 in the period"), or a ranking. Copying the script's conditions into the expected filter proves nothing, because both would be wrong together.
2. **Run and check `Status`.** `CompileError` and `RuntimeError` (init threw) come with `Errors`; fix and run again. `Errors` also reports adsets whose body threw (they were silently ignored); fix those too.
3. **Compare every action the script returns**, plus `"None"` for adsets that must stay untouched (the good ones): `test.Compare("Kill", expectedIds)`. `Missed` = should have got it but didn't (shows what it got instead), `Unexpected` = got it without being expected (its comment says why). Return the comparisons and `test.Counts` with `AddData`, never the whole result: every entry carries the full adset.
4. **Iterate until every comparison `IsMatch`.** When a mismatch is the expectation's fault, not the script's, say so and fix the expectation. Don't bend it to match the script.
5. **Show the user** the counts and the adsets that get a destructive action (kill, pause, budget cut) with their key metrics and comments. The user decides what counts as a good adset: the test only proves the script does what was meant.

The test sees the adsets you load in the query, which may be more days than the Stats page's 6; load the same window the script will run on (`LoadStatsToday()` = 6 days). Last execution and stat collection times are null, as on a first run, so `CanRun` gates on `LastExecutionUtc` pass.

```csharp
var adsets = (await LoadStatsToday()).Where(x => x.Status == AdsetStatus.Active).ToList();
var test = await RunTestScript("""
    // ... the full script, header included ...
    if (ad.Spend.Overall > 50 && ad.ROI.Overall < -30) return Kill().WithComment("ROI < -30% after $50");
    return Ignore();
    """, adsets);
if (!test.IsSuccess) { AddData("errors", test.Errors); return; }
AddData("errors", test.Errors);
AddData("counts", test.Counts);

// Expected: the goal in plain terms, not the script's conditions.
var shouldKill = adsets.Where(x => x.Spend.Overall > 50 && x.Profit.Overall < -20).Select(x => x.AdsetId).ToList();
var kill = test.Compare("Kill", shouldKill);
var keep = test.Compare("None", adsets.Select(x => x.AdsetId).Except(shouldKill));
AddData("kill", new { kill.IsMatch, kill.ExpectedCount, kill.ActualCount,
    missed = kill.Missed.Select(x => new { x.AdsetId, x.ActionName, x.Error, spend = x.Adset.Spend.Overall, profit = x.Adset.Profit.Overall }),
    unexpected = kill.Unexpected.Select(x => new { x.AdsetId, comment = x.Actions[0].Comment, spend = x.Adset.Spend.Overall, profit = x.Adset.Profit.Overall }) });
AddData("keep", new { keep.IsMatch, touched = keep.Missed.Select(x => new { x.AdsetId, x.ActionName }) });
```

The full `RunTestScript` API is in the **arbo-stat-queries** skill (reference, "Testing an arbo script").

## Examples

Kill losing, mature adsets and pause borderline ones. Show only those two groups:

```csharp
if (ad.Status != AdsetStatus.Active) return Ignore();
if (ad.CreatedDays < 2 || ad.Spend.Overall < 20) return Ignore();   // not enough data yet

if (ad.ROI.Overall < -40 && ad.ROI < -30) return Kill();            // multi-day and today both bad
if (ad.ROI < -15 && ad.ProfitTrend == TrendDirection.Down) return Pause(6);

return Ignore();
```

Scale winners by 15% at most once every 12 hours, with steps between $2 and $25 and a $400 ceiling:

```csharp
if (ad.Status != AdsetStatus.Active) return Ignore();
if (ad.Spend < 10 || ad.ROI < 25 || ad.ROI.Overall < 15) return Ignore();
if (ad.GetLastBudgetIncreaseInHours() < 12) return Include();       // winner, but changed recently: just show

return ChangeBudgetByPercentage(new ActionChangeBudgetByPercentageRequest
{
    Percentage = 15, MinimumChange = 2_00, MaximumChange = 25_00, MaximumBudget = 400_00,
});
```

Clone strong adsets that have no cost cap as cap adsets with a $40 budget, unless the offer already has a cap sibling:

```csharp
if (ad.CostCap > 0 || ad.OfferCountWithCap > 0) return Ignore();
if (ad.LastCloneCapUtcHours < 2) return Ignore();                   // in days: cap-cloned in the last 2 days
if (ad.RoiNumberOfDays >= 3 && ad.ROI > 30 && ad.Spend > 15) return CloneAsCap(40_00);
return Ignore();
```

Kill the 10 worst mature losers by 3-day profit, at most once every 6 hours when automated, with the reason on each change:

```csharp
// ================================================================================================
// KILL WORST 10 BY 3-DAY PROFIT
// ------------------------------------------------------------------------------------------------
// DO:     Kill up to 10 active adsets, 3+ days old with > $20 spend over the last 3 days, that have the
//         lowest 3-day profit, if that profit is negative. Runs at most every 6 hours when automated.
// WHY:    Example: cut the biggest losers first instead of every loser at once.
// GOAL:   Stop the largest losses while keeping the number of kills per run small.
// REVIEW: One Kill group, at most 10 adsets, all with negative 3-day profit.
// SCOPE:  All feeds, active adsets only.
// PAIRS:  none
// ================================================================================================
#region members
HashSet<string> ToKill = new();
#endregion

#region init
TagName = "s:killWorst10";
CanRun = LastExecutionUtc == null || (DateTime.UtcNow - LastExecutionUtc.Value).TotalHours >= 6;
ToKill = Adsets
    .Select(x => x.Entry)
    .Where(x => x.Status == AdsetStatus.Active && x.CreatedDays >= 3 && x.Spend.SumLastDays(3) > 20)
    .OrderBy(x => x.Profit.SumLastDays(3))
    .Take(10)
    .Where(x => x.Profit.SumLastDays(3) < 0)                          // only real losers
    .Select(x => x.AdsetId)
    .ToHashSet();
#endregion

if (ToKill.Contains(ad.AdsetId))
    return Kill().WithComment($"Bottom 10 by 3-day profit: {ad.Profit.SumLastDays(3):0.00}$");
return Ignore();
```

Show only one vertical in one country with no action (a pure filter):

```csharp
return ad.Vertical.Name == "Cars" && ad.Country == "US" ? Include() : Ignore();
```

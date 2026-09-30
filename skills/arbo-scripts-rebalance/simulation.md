# Queries for the rebalance review

Both run with `run_stat_query`. Nothing is applied: `RunTestScript` is a dry run.

## 1. Pass simulation

Paste every automated script of the pass you simulate. Use its **name, priority and exact code** from `list_stat_scripts(isAutomated: true, includeCode: true)`.

How to paste the code:
- Put each script in its own `var sN = """" ... """";` block, with the code unchanged between the delimiters.
- Keep both `""""` lines at the very start of their line, so no indentation is stripped.
- If a script itself contains `""""`, use five quotes (`"""""`) for that block.

Change nothing else in the template, except the loader for the yesterday pass. Remove any unused `sN` blocks.

```csharp
// ---- scripts of this pass: name, priority, exact code ----
var s1 = """"
// code of script 1, unchanged
return Ignore();
"""";

var s2 = """"
// code of script 2, unchanged
return Ignore();
"""";

var scripts = new List<(string Name, int Priority, string Code)>
{
    ("Script one name", 100, s1),
    ("Script two name", 0, s2),
};

// Today pass: TodayStats + AllStats scripts. Yesterday pass: LoadStatsYesterday() with YesterdayStats + AllStats scripts.
var adsets = await LoadStatsToday();
var maxExamples = Param("maxExamples", 5, "Example adsets per finding");

// Copies don't claim their adsets, and Include creates no group.
var notClaiming = new HashSet<string> { "Include", "Clone", "CreateCostCap", "TransferToAccount" };

double Num(object? v) => v == null ? 0 : Convert.ToDouble(v);

// stop, start, budget+, budget-, cap+, cap-, copy, or none when the group would drop the action.
string Direction(string type, object? value, StatResponseAdset ad)
{
    switch (type)
    {
        case "Kill":
            return ad.Status is AdsetStatus.Killed or AdsetStatus.Terminated ? "none" : "stop";
        case "Pause":
            return Num(value) <= 0 ? "none" : "stop";
        case "Activate":
            return ad.Status == AdsetStatus.Active ? "none" : "start";
        case "PercentageChange":
            var pct = Num(value?.GetType().GetProperty("Percentage")?.GetValue(value));
            return pct > 0 ? "budget+" : pct < 0 ? "budget-" : "none";
        case "BudgetChangeIndividual":
            var budgetCents = ad.Budget.Value * 100;
            var newBudget = Num(value);
            return Math.Abs(newBudget - budgetCents) < 1 ? "none" : newBudget > budgetCents ? "budget+" : "budget-";
        case "ChangeCostCap":
            if (ad.CostCap.Value <= 0) return "none";
            var newCap = Num(value);
            return Math.Abs(newCap - ad.CostCap.Value) < 1 ? "none" : newCap > ad.CostCap.Value ? "cap+" : "cap-";
        case "Clone":
        case "CreateCostCap":
        case "TransferToAccount":
            return "copy";
        default:
            return "none";
    }
}

var opposite = new HashSet<string> { "stop|start", "budget+|budget-", "cap+|cap-", "copy|stop", "budget+|stop", "cap+|stop", "start|budget-" };
bool Opposes(string a, string b) => opposite.Contains($"{a}|{b}") || opposite.Contains($"{b}|{a}");

var ordered = scripts.OrderByDescending(x => x.Priority).ThenBy(x => x.Name).ToList();
var remaining = adsets;
var claimedBy = new Dictionary<string, string>();                          // adset id -> script that claimed it
var standalone = new Dictionary<string, Dictionary<string, string>>();     // script -> adset id -> direction
var pipeline = new List<object>();

foreach (var s in ordered)
{
    var alone = await RunTestScript(s.Code, adsets);
    if (!alone.IsSuccess)
    {
        pipeline.Add(new { s.Name, s.Priority, status = alone.Status.ToString(), errors = alone.Errors.Take(3) });
        continue;
    }
    var chained = await RunTestScript(s.Code, remaining);

    var aloneActing = alone.Adsets.Where(a => a.Actions.Any(x => x.Type != "Include")).ToList();
    var chainedActing = chained.Adsets.Where(a => a.Actions.Any(x => x.Type != "Include")).ToList();
    var chainedIds = chainedActing.Select(a => a.AdsetId).ToHashSet();

    standalone[s.Name] = aloneActing.ToDictionary(
        a => a.AdsetId,
        a => string.Join("+", a.Actions.Where(x => x.Type != "Include").Select(x => Direction(x.Type, x.Value, a.Adset))));

    var lost = aloneActing.Where(a => !chainedIds.Contains(a.AdsetId)).ToList();
    var noOps = chainedActing.Where(a => a.Actions.Any(x => x.Type != "Include" && Direction(x.Type, x.Value, a.Adset) == "none")).ToList();

    pipeline.Add(new
    {
        s.Name,
        s.Priority,
        tag = chained.TagName,
        standaloneCounts = alone.Counts,
        chainedCounts = chained.Counts,
        chainedSpend = chainedActing.Sum(a => a.Adset.Spend.Overall),
        lost = lost.Count,
        lostTo = lost
            .GroupBy(a => claimedBy.TryGetValue(a.AdsetId, out var by) ? by : "(changed decision on fewer adsets, e.g. top-N in init)")
            .Select(g => new { script = g.Key, adsets = g.Count(), examples = g.Take(maxExamples).Select(a => new { a.AdsetId, wanted = a.ActionName }) }),
        noOpActions = noOps.Count,
        noOpExamples = noOps.Take(maxExamples).Select(a => new { a.AdsetId, action = a.ActionName }),
        errors = chained.Errors.Take(3),
        notes = chained.Notes.Take(3),
    });

    foreach (var a in chainedActing.Where(a => a.Actions.Any(x => !notClaiming.Contains(x.Type))))
        claimedBy.TryAdd(a.AdsetId, s.Name);
    remaining = remaining.Where(a => !claimedBy.ContainsKey(a.AdsetId)).ToList();
}

var byId = adsets.GroupBy(x => x.AdsetId).ToDictionary(g => g.Key, g => g.First());
var overlaps = new List<(int Opposing, object Data)>();
var names = standalone.Keys.ToList();
for (var i = 0; i < names.Count; i++)
for (var j = i + 1; j < names.Count; j++)
{
    var a = standalone[names[i]];
    var b = standalone[names[j]];
    var common = a.Keys.Intersect(b.Keys).ToList();
    if (common.Count == 0) continue;
    var opposing = common.Where(id => a[id].Split('+').Any(x => b[id].Split('+').Any(y => Opposes(x, y)))).ToList();
    overlaps.Add((opposing.Count, new
    {
        first = names[i],
        second = names[j],
        sharedAdsets = common.Count,
        opposing = opposing.Count,
        opposingSpend = opposing.Sum(id => byId[id].Spend.Overall),
        examples = opposing.Concat(common.Except(opposing)).Take(maxExamples).Select(id => new
        {
            adsetId = id,
            first = a[id],
            second = b[id],
            status = byId[id].Status.ToString(),
            spend = byId[id].Spend.Overall,
            roi = byId[id].ROI.Overall,
        }),
    }));
}

AddData("adsets", adsets.Count);
AddData("pipeline", pipeline);          // in run order
AddData("overlaps", overlaps.OrderByDescending(x => x.Opposing).Select(x => x.Data).ToList());
AddData("claimedAdsets", claimedBy.Count);
AddData("unclaimedAdsets", remaining.Count);
```

Reading it:
- `pipeline` is in run order. `standaloneCounts` shows what the script would do alone, and `chainedCounts` what it gets after the scripts above it.
- `lost` / `lostTo`: adsets it wanted but a higher script had already claimed. A large share lost points to a priority problem or a duplicate script.
- `noOpActions`: actions the groups would drop (kill on a killed adset, a cap change on an adset without a cap, a budget equal to the current one).
- `overlaps`: pairs of scripts that would act on the same adsets if each ran alone. `opposing` counts the ones where they pull in opposite directions. Priority decides who wins inside a pass, but across passes both still act.
- An `(changed decision on fewer adsets...)` entry in `lostTo` means the script's init logic picked different adsets on the smaller list. This happens with top-N rankings or totals. It usually means the script depends on adsets the higher scripts claim.

When the query is too slow or too large, run it in two parts:
1. Run the first scripts in order and add `AddData("claimedIds", claimedBy.Keys.ToList())`.
2. Run the second part with `remaining = adsets.Where(x => !claimedIdsFromPart1.Contains(x.AdsetId)).ToList()`, with the ids pasted in as a `HashSet<string>`.

In the second part the overlaps only cover pairs within that part. Compare cross-part pairs from each part's standalone counts.

## 2. Tag history

Shows which automated scripts really changed the same adsets over the last days. Put in the `TagName` of each automated script: it's in the code's init (`TagName = "s:..."`) and in the simulation's `pipeline[].tag`. Scripts without a tag leave no history.

Each tag on an adset holds only its **latest** write time and how many times it was written. So you see which scripts met on an adset and which one wrote last, not the full sequence.

```csharp
var adsets = await LoadStatsToday();
var days = Param("days", 7, "Look back this many days");
var maxExamples = Param("maxExamples", 5, "Example adsets per pair");

// TagName of each automated script -> script name
var tags = new Dictionary<string, string>
{
    ["s:scriptOne"] = "Script one name",
    ["s:scriptTwo"] = "Script two name",
};

var since = DateTime.UtcNow.AddDays(-days);
var touched = adsets
    .Select(x => new { ad = x, tags = x.Tags.Where(t => tags.ContainsKey(t.Name) && t.Time >= since).OrderBy(t => t.Time).ToList() })
    .Where(x => x.tags.Count > 0)
    .ToList();

AddData("perScript", tags.Select(t => new
{
    script = t.Value,
    tag = t.Key,
    adsets = touched.Count(x => x.tags.Any(y => y.Name == t.Key)),
    writes = touched.Sum(x => x.tags.Where(y => y.Name == t.Key).Sum(y => (int)y.Count)),
}));

var pairs = touched
    .Where(x => x.tags.Count >= 2)
    .SelectMany(x => x.tags.SelectMany((a, i) => x.tags.Skip(i + 1).Select(b => new { x.ad, a, b })))
    .GroupBy(p => $"{tags[p.a.Name]} | {tags[p.b.Name]}")
    .Select(g => new
    {
        pair = g.Key,
        adsets = g.Count(),
        spend = g.Sum(p => p.ad.Spend.Overall),
        profit = g.Sum(p => p.ad.Profit.Overall),
        examples = g.OrderByDescending(p => p.ad.Spend.Overall).Take(maxExamples).Select(p => new
        {
            p.ad.AdsetId,
            status = p.ad.Status.ToString(),
            budget = p.ad.Budget.Value,
            spend = p.ad.Spend.Overall,
            roi = p.ad.ROI.Overall,
            // earlier write first; the later one is the script that had the last word
            first = new { script = tags[p.a.Name], lastWriteUtc = p.a.Time.ToString("MM-dd HH:mm"), writes = (int)p.a.Count },
            then = new { script = tags[p.b.Name], lastWriteUtc = p.b.Time.ToString("MM-dd HH:mm"), writes = (int)p.b.Count },
        }),
    })
    .OrderByDescending(x => x.adsets)
    .ToList();

AddData("pairs", pairs);
AddData("adsetsWithSeveralScripts", touched.Count(x => x.tags.Count >= 2));
```

Reading it:
- A pair with many adsets means the two scripts manage the same adsets across passes. Check the directions in the code. Budget up and budget down on the same adsets, with high write counts on both, is a ping-pong.
- High `writes` on one tag for a few adsets means the script keeps hitting the same adsets. Check its own cooldown (`GetLastTagInHours(TagName)`).
- Clones and transfers write no tags. For those, compare with the clone fields on the adset (`LastCloneUtcHours`, `LastCloneCapUtcHours`, `LastTransferUtcHours`).

# Title scout query

Fallback for when the saved agentic query **"Title scout: test economics, batch size and title DNA"** is missing (`run_stat_query` with `queryName` returns an error). Run this code with `run_stat_query` (`code` = the block below, `parameters` as in SKILL.md). If it is missing and you can save queries, save it again with `save_agentic_query` under the same name.

```csharp
var days = Param("days", 10, "Full days to analyse, ending yesterday");
var country = Param("country", "", "ISO country code, empty = all");
var vertical = Param("vertical", "", "Exact vertical name, empty = all");
var feed = Param("feed", "", "Feed type (FLW, OH, Yahoo, ...), empty = all");
var affiliate = Param("affiliate", "", "Exact affiliate name, empty = all");
var matureDays = Param("matureDays", 3.0, "A title test counts as judged once its first adset is this many days old");
var minSpend = Param("minSpend", 5.0, "Minimum test spend in dollars for a title to count as a winner");
var roiFloor = Param("roiFloor", -1000.0, "ROI floor in percent the scope must keep; -1000 = default (current ROI minus a third of it, at least 0)");
var top = Param("top", 20, "Items per winners / losers list");
var recentDays = Param("recentDays", 2.0, "Adsets younger than this many days count as just launched (for de-duplication, not judged yet)");

bool InScope(StatResponseAdset x) =>
        (country == "" || x.Country.Equals(country, StringComparison.OrdinalIgnoreCase)) &&
        (vertical == "" || (x.Vertical?.Name ?? "").Equals(vertical, StringComparison.OrdinalIgnoreCase)) &&
        (feed == "" || x.AffiliateModel.FeedType.ToString().Equals(feed, StringComparison.OrdinalIgnoreCase)) &&
        (affiliate == "" || (x.AffiliateName ?? "").Equals(affiliate, StringComparison.OrdinalIgnoreCase));

// Metrics: full days only, ending yesterday
var adsets = (await LoadStatsYesterdayWithDays(days)).Where(InScope).ToList();
if (adsets.Count == 0) { AddError("No adsets match the scope."); return; }

// Scope totals, per day
var spend = adsets.Sum(x => x.Spend.Overall);
var profit = adsets.Sum(x => x.Profit.Overall);
var roi = spend > 0 ? profit / spend * 100 : 0;
AddData("scope", new
{
    days, country, vertical, feed, affiliate,
    adsets = adsets.Count,
    spendPerDay = Math.Round(spend / days, 2),
    profitPerDay = Math.Round(profit / days, 2),
    roi = Math.Round(roi, 2),
});

// One title test = one article (offer) in one country, all its adsets together (clones included)
var tests = adsets
    .GroupBy(x => new { x.OfferId, x.Country })
    .Select(g =>
    {
        // The published title (Title = original language, Anchor = English) comes from the test's best adset
        var best = g.OrderByDescending(x => x.Profit.Overall).First();
        return new
        {
            title = best.Title ?? "",
            titleEn = best.Anchor ?? "",
            adsetId = best.AdsetId,
            country = g.Key.Country,
            language = g.First().Language,
            vertical = g.First().Vertical?.Name ?? "",
            feed = g.First().AffiliateModel.FeedType.ToString(),
            affiliate = g.First().AffiliateName,
            ageDays = Math.Round(g.Max(x => x.CreatedDays), 1),
            adsets = g.Count(),
            active = g.Count(x => x.Status == AdsetStatus.Active),
            tag = g.SelectMany(x => x.Tags ?? new List<AdsetTag>()).Select(t => t.Name).FirstOrDefault(n => n != null && n.StartsWith("t:")),
            spend = Math.Round(g.Sum(x => x.Spend.Overall), 2),
            profit = Math.Round(g.Sum(x => x.Profit.Overall), 2),
            roi = g.Sum(x => x.Spend.Overall) > 0 ? Math.Round(g.Sum(x => x.Profit.Overall) / g.Sum(x => x.Spend.Overall) * 100, 1) : 0,
            revenue = g.Sum(x => x.Revenue.Overall),
            clicks = g.Sum(x => x.Clicks.Overall),
            rpcCents = g.Sum(x => x.Clicks.Overall) > 0 ? Math.Round(g.Sum(x => x.Revenue.Overall) / g.Sum(x => x.Clicks.Overall) * 100, 1) : 0,
            cpcCents = g.Sum(x => x.Clicks.Overall) > 0 ? Math.Round(g.Sum(x => x.Spend.Overall) / g.Sum(x => x.Clicks.Overall) * 100, 1) : 0,
            profitLast3 = Math.Round(g.Sum(x => x.Profit.SumDaysAgo(0, 2)), 2),
        };
    })
    .ToList();

// Just launched (today and yesterday, often no full-day stats yet): already being tested, so never propose them again
var fresh = (await LoadStatsToday()).Where(InScope).Where(x => x.CreatedDays <= recentDays)
    .GroupBy(x => new { x.OfferId, x.Country })
    .Select(g => new { country = g.Key.Country, ageHours = Math.Round(g.Max(x => x.CreatedDays) * 24), vertical = g.First().Vertical?.Name ?? "", feed = g.First().AffiliateModel.FeedType.ToString(),
        title = g.Select(x => x.Title).FirstOrDefault(n => !string.IsNullOrEmpty(n)) ?? "" })
    .ToList();

// Test economics: titles first launched inside the window and old enough to judge
var launched = tests.Where(t => t.ageDays <= days + 1).ToList();
var judged = launched.Where(t => t.ageDays >= matureDays).ToList();
var winners = judged.Where(t => t.profit > 0 && t.spend >= minSpend).ToList();
var losers = judged.Where(t => t.profit <= 0).ToList();
var hitRate = judged.Count > 0 ? (double)winners.Count / judged.Count : 0;
var winProfit = winners.Count > 0 ? winners.Average(t => t.profit) : 0;
var lossPerTest = losers.Count > 0 ? -losers.Average(t => t.profit) : 0;
var testSpend = judged.Count > 0 ? judged.Average(t => t.spend) : 0;
var ev = hitRate * winProfit - (1 - hitRate) * lossPerTest;
var pace = launched.Count / (double)days;

// Sizing: how many extra new titles per day the scope can absorb while keeping ROI at or above the floor
var floor = roiFloor > -1000 ? roiFloor : Math.Max(0, roi - Math.Abs(roi) / 3);
var cushionPerDay = Math.Max(0, (profit - floor / 100 * spend) / days);
// Worst case: every new title loses the average loss. Each test burns over about matureDays days.
var maxByRisk = lossPerTest > 0 ? cushionPerDay / lossPerTest : pace * 2;

AddData("testEconomics", new
{
    launchedInWindow = launched.Count,
    launchedPerDay = Math.Round(pace, 2),
    recentLaunches = fresh.Count,
    rpcCents = adsets.Sum(x => x.Clicks.Overall) > 0 ? Math.Round(adsets.Sum(x => x.Revenue.Overall) / adsets.Sum(x => x.Clicks.Overall) * 100, 1) : 0,
    judged = judged.Count,
    winners = winners.Count,
    losers = losers.Count,
    hitRatePct = Math.Round(hitRate * 100, 1),
    avgWinnerProfit = Math.Round(winProfit, 2),
    avgLoserLoss = Math.Round(lossPerTest, 2),
    avgTestSpend = Math.Round(testSpend, 2),
    expectedProfitPerTest = Math.Round(ev, 2),
    testSpendSharePct = spend > 0 ? Math.Round(launched.Sum(t => t.spend) / spend * 100, 1) : 0,
});
AddData("sizing", new
{
    roiNow = Math.Round(roi, 2),
    roiFloor = Math.Round(floor, 2),
    cushionPerDay = Math.Round(cushionPerDay, 2),
    maxExtraTitlesPerDayByRisk = Math.Round(maxByRisk, 1),
});

// Where to put them: country x vertical x feed, paying segments first
var segments = tests
    .GroupBy(t => new { t.country, t.vertical, t.feed })
    .Select(g =>
    {
        var j = g.Where(t => t.ageDays <= days + 1 && t.ageDays >= matureDays).ToList();
        var wl = j.Where(t => t.profit > 0 && t.spend >= minSpend).ToList();
        var ll = j.Where(t => t.profit <= 0).ToList();
        var w = wl.Count;
        var hr = j.Count > 0 ? (double)w / j.Count : 0;
        var segLoss = ll.Count > 0 ? -ll.Average(t => t.profit) : lossPerTest;
        var segEv = hr * (wl.Count > 0 ? wl.Average(t => t.profit) : 0) - (1 - hr) * segLoss;
        var s = g.Sum(t => t.spend);
        var p = g.Sum(t => t.profit);
        return new
        {
            g.Key.country, g.Key.vertical, g.Key.feed,
            language = g.First().language,
            titles = g.Count(),
            judged = j.Count,
            winners = w,
            hitRatePct = j.Count > 0 ? Math.Round(100.0 * w / j.Count, 1) : 0,
            spendPerDay = Math.Round(s / days, 2),
            profitPerDay = Math.Round(p / days, 2),
            roi = s > 0 ? Math.Round(p / s * 100, 1) : 0,
            rpcCents = g.Sum(t => t.clicks) > 0 ? Math.Round(g.Sum(t => t.revenue) / g.Sum(t => t.clicks) * 100, 1) : 0,
            cpcCents = g.Sum(t => t.clicks) > 0 ? Math.Round(s / g.Sum(t => t.clicks) * 100, 1) : 0,
            recentLaunches = fresh.Count(f => f.country == g.Key.country && f.vertical == g.Key.vertical && f.feed == g.Key.feed),
            profitLast3 = Math.Round(g.Sum(t => t.profitLast3), 2),
            launchedPerDay = Math.Round(g.Count(t => t.ageDays <= days + 1) / (double)days, 1),
            avgLoss = Math.Round(segLoss, 2),
            expectedProfitPerTest = Math.Round(segEv, 2),
            // Extra titles per day on top of the current pace: only where tests have paid, half the current pace, at least 1
            extraTitles = j.Count >= 5 && segEv > 0 ? Math.Max(1, (int)Math.Round(g.Count(t => t.ageDays <= days + 1) / (double)days * 0.5)) : 0,
            // Exploration: a strong segment whose new tests don't pay on average yet still earns, gets 1 title to try a new angle
            exploreTitles = !(j.Count >= 5 && segEv > 0) && s > 0 && p / s * 100 >= 15 && p / days >= 10 && g.Sum(t => t.profitLast3) > 0 ? 1 : 0,
        };
    })
    .Where(x => x.spendPerDay >= 1)
    .OrderByDescending(x => x.extraTitles + x.exploreTitles > 0)
    .ThenByDescending(x => x.profitPerDay)
    .ToList();

// The batch: extra titles where tests pay, capped so that if every one of them loses, ROI stays above the floor
var exploit = segments.Sum(x => x.extraTitles);
var explore = segments.Sum(x => x.exploreTitles);
var batchCap = (int)Math.Floor(maxByRisk);
AddData("batch", new
{
    exploitTitles = exploit,
    exploreTitles = explore,
    capByRoiFloor = batchCap,
    recommendedBatch = Math.Max(1, Math.Min(exploit + explore, batchCap)),
    segmentsWithPayingTests = segments.Count(x => x.extraTitles > 0),
    worstCaseCostPerDay = Math.Round(Math.Min(exploit + explore, batchCap) * lossPerTest, 2),
});
AddData("segments", segments.Take(30).ToList());

object Row(string title, string titleEn, string adsetId, string country, string language, string vertical, string feed, string affiliate, string tag,
    double ageDays, int adsets, double spend, double profit, double roi, double rpcCents, double cpcCents, double profitLast3)
    => new { title, titleEn, adsetId, country, language, vertical, feed, affiliate, tag, ageDays, adsets, spend, profit, roi, rpcCents, cpcCents, profitLast3 };

AddData("winners", tests.Where(t => t.profit > 0 && t.spend >= minSpend)
    .OrderByDescending(t => t.profit).Take(top)
    .Select(t => Row(t.title, t.titleEn, t.adsetId, t.country, t.language, t.vertical, t.feed, t.affiliate, t.tag, t.ageDays, t.adsets, t.spend, t.profit, t.roi, t.rpcCents, t.cpcCents, t.profitLast3)).ToList());
AddData("newWinners", winners.OrderByDescending(t => t.profit).Take(top)
    .Select(t => Row(t.title, t.titleEn, t.adsetId, t.country, t.language, t.vertical, t.feed, t.affiliate, t.tag, t.ageDays, t.adsets, t.spend, t.profit, t.roi, t.rpcCents, t.cpcCents, t.profitLast3)).ToList());
AddData("losers", tests.Where(t => t.profit < 0 && t.spend >= minSpend)
    .OrderBy(t => t.profit).Take(top)
    .Select(t => Row(t.title, t.titleEn, t.adsetId, t.country, t.language, t.vertical, t.feed, t.affiliate, t.tag, t.ageDays, t.adsets, t.spend, t.profit, t.roi, t.rpcCents, t.cpcCents, t.profitLast3)).ToList());
AddData("fizzled", judged.Where(t => t.spend < minSpend)
    .OrderBy(t => t.spend).Take(top).Select(t => new { t.title, t.country, t.vertical, spend = Math.Round(t.spend, 2) }).ToList());
AddData("recentLaunches", fresh.OrderBy(t => t.ageHours).Select(t => $"{t.country}|{t.vertical}|{t.feed}|{t.ageHours}h|{t.title}").Distinct().Take(200).ToList());
AddData("testedTitles", tests.OrderByDescending(t => t.spend).Select(t => $"{t.country}|{t.title}").Distinct().Take(250).ToList());

AddNote($"Metrics use full days only: the {days} days ending yesterday; recentLaunches lists titles launched in the last {recentDays} days for de-duplication. RPC / CPC in cents. A title test = one article in one country, clones included. Judged = first launched in the window and at least {matureDays} days old. Winner = profit > 0 with at least ${minSpend} spend.");
if (judged.Count < 10) AddNote("Fewer than 10 judged tests: the hit rate is thin, treat the sizing as a rough guide.");
```

# Cap scout queries

Fallbacks for when the saved agentic queries are missing (`run_stat_query` with `queryName` returns an error). Run the code with `run_stat_query` (`code` = the block, `parameters` as in SKILL.md). If a query is missing and you can save queries, save it again with `save_agentic_query` under the same name, with a description saying what it returns and what its parameters mean.

## Study: "Cap scout: study of past cap clones"

```csharp
var days = Param("days", 30, "Days of history: cap clones created in this window are judged");
var minCloneAge = Param("minCloneAge", 3.0, "Only judge clones at least this many days old");
var excludeBursts = Param("excludeBursts", false, "Leave out days with mass cloning (more than 2x the median clones per day)");
var feed = Param("feed", "", "Feed type (FLW, OH, ...), empty = all");
var strongProfit = Param("strongProfit", 10.0, "Source profit on the clone day that defines a 'strong' source for the strong... tables");
var strongRoi = Param("strongRoi", 50.0, "Source ROI in percent on the clone day that defines a 'strong' source");

var adsets = await LoadStatsTodayWithDays(days);
var byId = adsets.GroupBy(x => x.AdsetId).ToDictionary(g => g.Key, g => g.First());
var now = DateTime.UtcNow;
var clonesAll = adsets.Where(x => (x.Origin == AdsetOrigin.TrafficAdsetCloneWithCap || x.Origin == AdsetOrigin.AiCloneWithCap) && byId.ContainsKey(x.OriginalAdsetId ?? "")
  && (feed == "" || x.AffiliateModel.FeedType.ToString().Equals(feed, StringComparison.OrdinalIgnoreCase))).ToList();
var perDay = clonesAll.GroupBy(x => now.AddDays(-x.CreatedDays).ToString("yyyy-MM-dd")).ToDictionary(g => g.Key, g => g.Count());
var sorted = perDay.Values.OrderBy(v => v).ToList();
double median = sorted.Count > 0 ? sorted[sorted.Count / 2] : 0;
var burst = new HashSet<string>(perDay.Where(p => p.Value > 2 * median).Select(p => p.Key));
AddData("clonesPerDay", perDay.OrderBy(p => p.Key).Select(p => $"{p.Key}:{p.Value}{(burst.Contains(p.Key) ? " burst" : "")}").ToList());
AddNote("A clone is judged on its whole life: spend, profit, delivered = spent at least 5$. Source numbers are the source adset's UTC day the clone was created (that day includes hours after the clone). Clones that never had a stats row (rejected, never delivered) are missing, so delivery rates are optimistic.");

var rows = new List<(double conv, double profit, double roi, double sp, double rpc, double rpc3, double cap, double srcAge, double cSpend, double cProfit, double cDays, string feed, bool burst)>();
foreach (var c in clonesAll.Where(x => x.CreatedDays >= minCloneAge)) {
  var day = now.AddDays(-c.CreatedDays).ToString("yyyy-MM-dd");
  if (excludeBursts && burst.Contains(day)) continue;
  var s = byId[c.OriginalAdsetId];
  double conv = s.Conversions.GetForDate(day), rev = s.Revenue.GetForDate(day), sp = s.Spend.GetForDate(day);
  double c3 = conv + s.Conversions.GetDaysFrom(day, -1) + s.Conversions.GetDaysFrom(day, -2), r3 = rev + s.Revenue.GetDaysFrom(day, -1) + s.Revenue.GetDaysFrom(day, -2);
  rows.Add((conv, rev - sp, sp > 0 ? (rev - sp) / sp * 100 : 0, sp, conv > 0 ? rev / conv * 100 : 0, c3 > 0 ? r3 / c3 * 100 : 0, c.CostCap.History.Values.FirstOrDefault(v => v > 0),
    s.CreatedDays - c.CreatedDays, c.Spend.Overall, c.Profit.Overall, Math.Max(1, c.CreatedDays), c.AffiliateModel.FeedType.ToString(), burst.Contains(day)));
}
if (rows.Count == 0) { AddError("No judged cap clones in the window."); return; }
object Agg(IEnumerable<(double conv, double profit, double roi, double sp, double rpc, double rpc3, double cap, double srcAge, double cSpend, double cProfit, double cDays, string feed, bool burst)> g) {
  var l = g.ToList(); if (l.Count == 0) return null; double sp = l.Sum(r => r.cSpend), pr = l.Sum(r => r.cProfit);
  return new { n = l.Count, winPct = Math.Round(100.0 * l.Count(r => r.cProfit > 0) / l.Count), deliverPct = Math.Round(100.0 * l.Count(r => r.cSpend >= 5) / l.Count),
    roi = sp > 0 ? Math.Round(pr / sp * 100, 1) : 0, profitPerClone = Math.Round(pr / l.Count, 1), profitPerCloneDay = Math.Round(l.Sum(r => r.cProfit / r.cDays) / l.Count, 2),
    bigWinPct = Math.Round(100.0 * l.Count(r => r.cProfit >= 50) / l.Count) }; }
string B(double v, double[] e) { for (int i = 0; i < e.Length; i++) if (v < e[i]) return i + ":<" + e[i]; return e.Length + ":>=" + e.Last(); }

AddData("all", Agg(rows));
AddData("burstVsNormal", rows.GroupBy(r => r.burst ? "burst days" : "normal days").Select(g => new { b = g.Key, a = Agg(g) }).ToList());
AddData("byFeed", rows.GroupBy(r => r.feed).Select(g => new { b = g.Key, a = Agg(g) }).ToList());
AddData("bySourceDayProfit", rows.GroupBy(r => B(r.profit, new double[]{0,5,10,25,50})).OrderBy(g => g.Key).Select(g => new { b = "$ " + g.Key, a = Agg(g) }).ToList());
AddData("bySourceDayRoi", rows.GroupBy(r => B(r.roi, new double[]{0,30,50,100,200})).OrderBy(g => g.Key).Select(g => new { b = "% " + g.Key, a = Agg(g) }).ToList());
AddData("byRpc", rows.Where(r => r.rpc > 0).GroupBy(r => B(r.rpc, new double[]{10,15,20,30,50})).OrderBy(g => g.Key).Select(g => new { b = "cents " + g.Key, a = Agg(g) }).ToList());
AddData("byCapToRpc3d", rows.Where(r => r.rpc3 > 0).GroupBy(r => B(r.cap / r.rpc3, new double[]{0.6,0.7,0.8,0.9,1.0,1.1})).OrderBy(g => g.Key).Select(g => new { b = "ratio " + g.Key, a = Agg(g) }).ToList());

var strong = rows.Where(r => r.profit >= strongProfit && r.roi >= strongRoi).ToList();
AddData("strong", new { rule = $"source profit >= {strongProfit}$ and ROI >= {strongRoi}% on the clone day", a = Agg(strong) });
AddData("strongByConversions", strong.GroupBy(r => B(r.conv, new double[]{5,10,20,40,80})).OrderBy(g => g.Key).Select(g => new { b = "conv " + g.Key, a = Agg(g) }).ToList());
AddData("strongByRpc", strong.GroupBy(r => B(r.rpc, new double[]{10,15,20,30,50})).OrderBy(g => g.Key).Select(g => new { b = "cents " + g.Key, a = Agg(g) }).ToList());
AddData("strongByRpcStability", strong.Where(r => r.rpc3 > 0).GroupBy(r => B(r.rpc / r.rpc3, new double[]{0.8,0.95,1.05,1.25,1.5})).OrderBy(g => g.Key).Select(g => new { b = "rpcDay/rpc3d " + g.Key, a = Agg(g) }).ToList());
AddData("strongByCapMinusRpc", strong.Where(r => r.rpc > 0).GroupBy(r => B(r.cap - r.rpc, new double[]{-15,-10,-5,-2,0,3})).OrderBy(g => g.Key).Select(g => new { b = "cents " + g.Key, a = Agg(g) }).ToList());
AddData("strongByCapToRpc3d", strong.Where(r => r.rpc3 > 0).GroupBy(r => B(r.cap / r.rpc3, new double[]{0.7,0.8,0.9,1.0,1.1})).OrderBy(g => g.Key).Select(g => new { b = "ratio " + g.Key, a = Agg(g) }).ToList());
AddData("strongBySourceAge", strong.GroupBy(r => B(r.srcAge, new double[]{1,2,4,8})).OrderBy(g => g.Key).Select(g => new { b = "days " + g.Key, a = Agg(g) }).ToList());
AddData("strongBySourceDaySpend", strong.GroupBy(r => B(r.sp, new double[]{3,5,10,20,40})).OrderBy(g => g.Key).Select(g => new { b = "$ " + g.Key, a = Agg(g) }).ToList());
```

## Candidates: "Cap scout: winners ready for a cost cap clone"

```csharp
var minProfit = Param("minProfit", 10.0, "Minimum profit in dollars on the signal day (today so far, or yesterday's full day)");
var minRoi = Param("minRoi", 50.0, "Minimum ROI in percent on the signal day");
var minConv = Param("minConv", 10, "Minimum conversions on the signal day");
var minRpc = Param("minRpc", 15.0, "Minimum RPC (revenue per conversion, cents) a cap clone needs; below it caps rarely deliver");
var capMarginCents = Param("capMarginCents", 5.0, "Cap = RPC basis minus this many cents");
var minCapRatio = Param("minCapRatio", 0.8, "The cap is never set below this share of the RPC basis (lower caps rarely deliver)");
var cloneCooldownDays = Param("cloneCooldownDays", 7.0, "Block adsets whose last cap clone (even an unfinished one) is younger than this many days");
var maxCapOffer = Param("maxCapOffer", 3, "Block when the offer already has more than this many cap adsets in the country (all accounts)");
var maxCapAccount = Param("maxCapAccount", 0, "Block when the offer already has more than this many cap adsets in the same account");
var historyDays = Param("historyDays", 21, "Days loaded to find earlier cap clones of each candidate");
var country = Param("country", "", "ISO country code, empty = all");
var feed = Param("feed", "", "Feed type (FLW, OH, ...), empty = all");
var top = Param("top", 25, "Rows per list");

var adsets = await LoadStatsToday();
var utcDayShare = Math.Max(0.1, (DateTime.UtcNow.Hour + DateTime.UtcNow.Minute / 60.0) / 24);
AddNote($"Today is UTC {adsets.FirstOrDefault()?.Spend.DateKey}, {Math.Round(utcDayShare * 100)}% of the UTC day has passed. capOffer / capAccount count cap adsets of the same offer and country (killed ones included) seen in the last 6 days.");

// Sources must be eligible now (Active, article present) AND delivering today: Status alone doesn't prove delivery.
var pool = adsets.Where(x => x.Status == AdsetStatus.Active && !x.IsArticleDeleted && x.IsActiveToday && x.CostCap.Value == 0 && x.TrafficProvider == TrafficProvider.Facebook
    && (country == "" || x.Country.Equals(country, StringComparison.OrdinalIgnoreCase))
    && (feed == "" || x.AffiliateModel.FeedType.ToString().Equals(feed, StringComparison.OrdinalIgnoreCase))).ToList();

var rows = pool.Select(x => {
  double tConv = x.Conversions.Value, tRev = x.Revenue.Value, tSp = x.Spend.Value;
  double yConv = x.Conversions.GetDaysAgo(1), yRev = x.Revenue.GetDaysAgo(1), ySp = x.Spend.GetDaysAgo(1);
  double c3 = x.Conversions.SumDaysAgo(0, 2), r3 = x.Revenue.SumDaysAgo(0, 2);
  double tRoi = tSp > 0 ? (tRev - tSp) / tSp * 100 : (tRev > 0 ? 999 : 0), yRoi = ySp > 0 ? (yRev - ySp) / ySp * 100 : (yRev > 0 ? 999 : 0);
  bool todayOk = tRev - tSp >= minProfit && tConv >= minConv && tRoi >= minRoi;
  bool yestOk = yRev - ySp >= minProfit && yConv >= minConv && yRoi >= minRoi && tRev - tSp > 0;
  double rpcToday = tConv > 0 ? tRev / tConv * 100 : 0, rpcY = yConv > 0 ? yRev / yConv * 100 : 0, rpc3 = c3 > 0 ? r3 / c3 * 100 : 0;
  // Basis: the 3-day conversion-weighted RPC when it has enough volume (stable), else the signal day's RPC; never above the signal day's RPC
  double signalRpc = todayOk ? rpcToday : rpcY;
  double rpcBasis = c3 >= 2 * minConv && rpc3 > 0 ? Math.Min(rpc3, signalRpc > 0 ? signalRpc : rpc3) : signalRpc;
  int cap = (int)Math.Max(2, Math.Min(350, Math.Round(Math.Max(rpcBasis - capMarginCents, rpcBasis * minCapRatio))));
  var lastCap = x.LastCloneCapUtcHours > 1e6 ? (double?)null : Math.Round(x.LastCloneCapUtcHours, 2);
  var blocks = new List<string>();
  if (lastCap != null && lastCap < cloneCooldownDays) blocks.Add(x.OfferCountWithCapAccount == 0 ? $"cap clone started {lastCap}d ago, no cap adset of the offer visible in the account (pending, rejected or never delivered)" : $"cap clone {lastCap}d ago");
  if (x.OfferCountWithCapAccount > maxCapAccount) blocks.Add($"offer already has {x.OfferCountWithCapAccount} cap adset(s) in this account");
  if (x.OfferCountWithCap > maxCapOffer) blocks.Add($"offer already has {x.OfferCountWithCap} cap adsets in the country");
  if (rpcBasis < minRpc) blocks.Add($"RPC {Math.Round(rpcBasis, 1)}c below {minRpc}c");
  return new { x, signal = todayOk ? "today" : yestOk ? "yesterday" : "", blocks, cap,
    row = new { adsetId = x.AdsetId, x.Country, vertical = x.Vertical?.Name, feed = x.AffiliateModel.FeedType.ToString(), affiliate = x.AffiliateName, account = x.TrafficAccountName,
      ageDays = Math.Round(x.CreatedDays, 1), x.LocalHour, budget = Math.Round(x.Budget.Value, 2), spendPct = Math.Round(x.SpendPercentage.Value),
      tSpend = Math.Round(tSp, 2), tProfit = Math.Round(tRev - tSp, 2), tProfitPace = Math.Round((tRev - tSp) / utcDayShare, 1), tRoi = Math.Round(tRoi), tConv,
      ySpend = Math.Round(ySp, 2), yProfit = Math.Round(yRev - ySp, 2), yRoi = Math.Round(yRoi), yConv,
      rpcToday = Math.Round(rpcToday, 1), rpcYesterday = Math.Round(rpcY, 1), rpc3d = Math.Round(rpc3, 1), conv3d = c3, rpcBasis = Math.Round(rpcBasis, 1),
      cpaToday = Math.Round(x.CostPerConversion.Value, 1), cpcToday = Math.Round(x.CostPerVisit.Value, 1), trend = x.ProfitTrend.ToString(),
      suggestedCapCents = cap, capToRpc = rpcBasis > 0 ? Math.Round(cap / rpcBasis, 2) : 0,
      lastCapCloneDays = lastCap, capOffer = x.OfferCountWithCap, capAccount = x.OfferCountWithCapAccount,
      tag = (x.Tags ?? new List<AdsetTag>()).Select(t => t.Name).FirstOrDefault(n => n != null && n.StartsWith("t:")),
      article = x.ArticleName } };
}).ToList();

var sig = rows.Where(r => r.signal != "").ToList();

// Earlier cap clones of the candidates (clones that never had a stats row are invisible here)
var hist = (await LoadStatsTodayWithDays(historyDays))
  .Where(x => (x.Origin == AdsetOrigin.TrafficAdsetCloneWithCap || x.Origin == AdsetOrigin.AiCloneWithCap) && !string.IsNullOrEmpty(x.OriginalAdsetId))
  .GroupBy(x => x.OriginalAdsetId).ToDictionary(g => g.Key, g => g.OrderBy(c => c.CreatedDays)
     .Select(c => $"{Math.Round(c.CreatedDays, 1)}d ago cap {c.CostCap.History.Values.FirstOrDefault(v => v > 0)}c {c.Status}: spend {Math.Round(c.Spend.Overall)}$ profit {Math.Round(c.Profit.Overall)}$").ToList());
List<string> H(string id) => hist.TryGetValue(id, out var l) ? l : new List<string>();

AddData("summary", new { activeUncapped = pool.Count, withSignal = sig.Count, ready = sig.Count(r => r.blocks.Count == 0), blocked = sig.Count(r => r.blocks.Count > 0) });
AddData("ready", sig.Where(r => r.blocks.Count == 0).OrderByDescending(r => Math.Max(r.row.tProfit, r.row.yProfit)).Take(top)
  .Select(r => new { r.signal, r.row, earlierCapClones = H(r.row.adsetId) }).ToList());
AddData("blocked", sig.Where(r => r.blocks.Count > 0).OrderByDescending(r => Math.Max(r.row.tProfit, r.row.yProfit)).Take(top)
  .Select(r => new { r.signal, why = string.Join("; ", r.blocks), r.row.adsetId, r.row.Country, r.row.vertical, r.row.feed, r.row.account, r.row.tProfit, r.row.yProfit, r.row.tConv, r.row.yConv, r.row.rpcBasis, r.row.suggestedCapCents, earlierCapClones = H(r.row.adsetId) }).ToList());
AddData("watch", rows.Where(r => r.signal == "" && r.blocks.Count == 0 && r.row.tProfit > 0 && r.row.tProfitPace >= minProfit && r.row.tRoi >= minRoi)
  .OrderByDescending(r => r.row.tProfitPace).Take(top)
  .Select(r => new { r.row.adsetId, r.row.Country, r.row.vertical, r.row.feed, r.row.ageDays, r.row.budget, r.row.spendPct, r.row.tProfit, r.row.tProfitPace, r.row.tRoi, r.row.tConv, r.row.rpcBasis, r.row.suggestedCapCents }).ToList());
```

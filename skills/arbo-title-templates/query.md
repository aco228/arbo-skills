# Template evidence query

Run this code with `run_stat_query` (`code` = the block below). Nothing is saved or changed.

Parameters:
- `vertical` (required): exact vertical or theme name.
- `days` (default 7): full days ending yesterday.
- `templates`: the templates to score, one per line, exactly as `list_title_templates` returns them. Leave empty to get only the winners and losers.
- `language`: the templates' language code when they are language templates; empty for generic English templates (matched against the English title).
- `minSpend` (3), `loserRoi` (-30), `matchShare` (0.8), `top` (25).

Results:
- `vertical`: totals for the vertical (titles, winners, losers, spend and profit per day, ROI).
- `winners` / `losers`: English title, a native title, countries, where it won, spend, profit, ROI, age in days.
- `templates`: per template, the live titles that look made from it (`matchedTitles`), how many of them win and lose, their spend, profit and ROI, and up to 5 examples.

Matching is approximate. A title counts as made from a template when it contains most of the template's literal words (placeholders removed, words of 3+ letters). Titles that were translated away from the template's wording are missed, so 0 matches means "no evidence", not "failed". A template with few literal words over-matches; check the examples before trusting its numbers.

```csharp
var vertical = Param("vertical", "", "Exact vertical or theme name (required)");
var days = Param("days", 7, "Full days to analyse, ending yesterday");
var minSpend = Param("minSpend", 3.0, "Minimum spend in dollars for a title to count as a winner or loser");
var loserRoi = Param("loserRoi", -30.0, "ROI in percent below which a title with enough spend is a loser");
var templates = Param("templates", "", "Templates to score, one per line (from list_title_templates). Empty = only the evidence");
var language = Param("language", "", "Language code of the templates; empty = generic English templates, matched against the English title");
var matchShare = Param("matchShare", 0.8, "Share of a template's literal words a title must contain to count as made from it");
var top = Param("top", 25, "Items per winners / losers list");

if (vertical == "") { AddError("Pass the vertical parameter."); return; }

var adsets = (await LoadStatsYesterdayWithDays(days))
    .Where(x => (x.Vertical?.Name ?? "").Equals(vertical, StringComparison.OrdinalIgnoreCase))
    .ToList();
if (adsets.Count == 0) { AddError($"No adsets for `{vertical}` in the last {days} days."); return; }

// One title = one English title (Anchor) across all countries, the same unit the template generator learns from
var titles = adsets
    .Where(x => !string.IsNullOrEmpty(x.Anchor))
    .GroupBy(x => x.Anchor.Trim())
    .Select(g =>
    {
        var spend = g.Sum(x => x.Spend.Overall);
        var profit = g.Sum(x => x.Profit.Overall);
        return new
        {
            titleEn = g.Key,
            titles = g.Select(x => x.Title ?? "").Where(t => t != "").Distinct().ToList(),
            languages = g.Select(x => (x.Language ?? "").ToLowerInvariant()).Distinct().ToList(),
            countries = g.Select(x => x.Country).Distinct().ToList(),
            wonIn = g.Where(x => x.Profit.Overall > 0).Select(x => x.Country).Distinct().ToList(),
            ageDays = Math.Round(g.Min(x => x.CreatedDays), 1),
            spend = Math.Round(spend, 2),
            profit = Math.Round(profit, 2),
            roi = spend > 0 ? Math.Round(profit / spend * 100, 1) : 0,
        };
    })
    .ToList();

bool IsWinner(double spend, double profit) => spend >= minSpend && profit > 0;
bool IsLoser(double spend, double roi) => spend >= minSpend && roi < loserRoi;

var spendAll = titles.Sum(t => t.spend);
var profitAll = titles.Sum(t => t.profit);
AddData("vertical", new
{
    vertical, days,
    titles = titles.Count,
    winners = titles.Count(t => IsWinner(t.spend, t.profit)),
    losers = titles.Count(t => IsLoser(t.spend, t.roi)),
    spendPerDay = Math.Round(spendAll / days, 2),
    profitPerDay = Math.Round(profitAll / days, 2),
    roi = spendAll > 0 ? Math.Round(profitAll / spendAll * 100, 1) : 0,
});

AddData("winners", titles.Where(t => IsWinner(t.spend, t.profit)).OrderByDescending(t => t.profit).Take(top)
    .Select(t => new { t.titleEn, title = t.titles.FirstOrDefault(), t.countries, t.wonIn, t.spend, t.profit, t.roi, t.ageDays }).ToList());
AddData("losers", titles.Where(t => IsLoser(t.spend, t.roi)).OrderByDescending(t => t.spend).Take(top)
    .Select(t => new { t.titleEn, title = t.titles.FirstOrDefault(), t.countries, t.spend, t.profit, t.roi, t.ageDays }).ToList());

// Score templates: a title counts as made from a template when it holds most of the template's literal words.
// Approximate: titles are translated when resolved, so a template only matches titles that kept its wording.
var templateList = templates.Split('\n').Select(t => t.Trim()).Where(t => t != "").ToList();
if (templateList.Count == 0) { AddNote("No templates passed: evidence only."); return; }

List<string> Words(string text) => System.Text.RegularExpressions.Regex
    .Split(System.Text.RegularExpressions.Regex.Replace(text.ToLowerInvariant(), @"\{[a-z0-9_]+\}", " "), @"[^\p{L}\p{N}]+")
    .Where(w => w.Length >= 3).Distinct().ToList();

var lang = language.Trim().ToLowerInvariant();
var useNative = lang != "" && lang != "en";

AddData("templates", templateList.Select(template =>
{
    var words = Words(template);
    var matched = words.Count == 0 ? new() : titles.Where(t =>
    {
        if (useNative && !t.languages.Contains(lang)) return false;
        var candidates = useNative ? t.titles : new List<string> { t.titleEn };
        return candidates.Any(c =>
        {
            var titleWords = Words(c).ToHashSet();
            return words.Count(w => titleWords.Contains(w)) >= Math.Ceiling(words.Count * matchShare);
        });
    }).ToList();
    var spend = matched.Sum(t => t.spend);
    var profit = matched.Sum(t => t.profit);
    return new
    {
        template,
        literalWords = words.Count,
        matchedTitles = matched.Count,
        winners = matched.Count(t => IsWinner(t.spend, t.profit)),
        losers = matched.Count(t => IsLoser(t.spend, t.roi)),
        spend = Math.Round(spend, 2),
        profit = Math.Round(profit, 2),
        roi = spend > 0 ? Math.Round(profit / spend * 100, 1) : 0,
        examples = matched.OrderByDescending(t => t.spend).Take(5).Select(t => $"{t.titleEn} | ${t.spend} | ROI {t.roi}%").ToList(),
    };
}).ToList());

AddNote($"Full days only: the {days} days ending yesterday. Title = one English title across countries. Winner = profit > 0 with at least ${minSpend} spend; loser = ROI below {loserRoi}% with at least ${minSpend} spend. Template matching is approximate (share {matchShare} of the template's literal words); titles that were translated away from the template's wording are missed, and short templates over-match.");
```

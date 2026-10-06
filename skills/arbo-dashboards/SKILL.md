---
name: arbo-dashboards
description: Build CK dashboards and widgets, data-driven HTML pages (KPI cards, charts, tables) that load live adset data from saved stats queries and are shown in CK on the Dashboards page or as small cards on the home page. Writes the reusable stats queries, tests them, writes the HTML against the CK query API, and saves both (save_agentic_query, save_widget, list_widgets, get_widget, delete_widget MCP tools). Use when the user asks for a dashboard, widget, report page, KPI board, chart or table view of adset data in CK, or wants to change, resize, fix or delete one.
---

# Dashboards and widgets

A **dashboard** is a full page, opened from **Dashboards** in CK. A **widget** is a small card on an 8-column grid, opened from the Widgets section of the same page and optionally shown on the home page. Both are one self-contained HTML page that CK shows in a sandboxed iframe. The page loads its data in the browser from **saved stats queries** through the CK query API, so it is always live.

You build two things: the queries (the data) and the HTML (the view). Queries are written as in the **arbo-stat-queries** skill; follow it for everything about query code.

## Workflow

1. **Understand the need.** Ask what decisions the view should support, which metrics, which period, which breakdowns (country, vertical, account, feed...), and whether it is a dashboard or a widget. For a widget, agree the size (below) first, because it decides what fits.
2. **Look for what exists.** `list_widgets` (avoid a duplicate name, maybe extend an existing one) and `list_stat_queries` (reuse an agentic query whose results already fit).
3. **Write and test the queries** with `run_stat_query` until the results are right and shaped for the view (see Queries for views). Show the user the key numbers so they can confirm the data before you build the view.
4. **Save the queries** with `save_agentic_query` (agents can only save agentic queries). You need their ids for the HTML.
5. **Write the HTML** (see The page contract and Design).
6. **Save** with `save_widget` only after the user agreed. If validation errors come back, fix them and save again.
7. **To change one later:** `get_widget` first, edit the current HTML, then `save_widget` with `widgetId` and the whole new HTML. Size and home-page placement are usually set by people in CK; change them only when asked.

You can't see the page as CK renders it. If your environment can render HTML (an artifact or preview), render the page there with the real results from `run_stat_query` pasted in place of the fetch, to check the layout, then switch back to the fetch before saving.

## Queries for views

- **Few queries, many results.** One query can return several named results (`AddData("kpis", ...)`, `AddData("byCountry", ...)`, `AddData("daily", ...)`). Every query call takes a slot on a server that runs only a few queries at once per division, so prefer one query per dashboard (two or three for a big one) and one per widget, and load the adsets once inside it.
- **Return view-ready data.** Rounded numbers, sorted, rows limited (top 20, not 2,000), one object per row with short camelCase keys, dates as `yyyy-MM-dd`. The browser should only draw, not compute.
- **Daily series** for charts: a list of `{ date, spend, revenue, profit }` per day, oldest first, read from the `AverageValue` history of one load.
- **Parameters**: use `Param` for what the viewer may change (`days`, `country`), and send them from filter controls in the page. Defaults must give a sensible view with no body sent.
- **Name and describe** each query so the agentic library stays readable: what it returns and that it feeds a dashboard, e.g. description "... Feeds the 'Country overview' dashboard: results kpis, byCountry, daily."
- **Don't break views.** A view depends on its query's result names and row keys. Before `update_agentic_query` or `delete_agentic_query` on any query, check `list_widgets` for views whose `queryIds` contain it; keep names and keys compatible, or update those views in the same task.
- The agentic library has a limit (see `list_stat_queries`); reuse queries across views when the data is the same.

## The page contract

CK injects this into the page's `<head>` before it runs:

```js
window.ARBO = { divisionId: "<division id>", apiBase: "https://<ck api host>/api/query/<division id>/" };
```

Load a query with:

```js
const res = await fetch(ARBO.apiBase + queryId, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ days: 7 }),   // values for the query's Param(...) inputs; {} for defaults
});
```

The response is JSON (camelCase):

| Field | Meaning |
|---|---|
| `results` | `[{ name, value }]`, one entry per `AddData`; `value` is the JSON you added |
| `notes`, `errors`, `warnings` | the query's `AddNote` / `AddError` messages, and system warnings (e.g. output trimmed), or null |
| `fatalException` | the query crashed, timed out, or the server was busy; no usable results |
| `compileErrors`, `parameterErrors` | the code doesn't compile / a body parameter is unknown or has the wrong type |
| `durationSeconds` | run time |
| `fromCache`, `ranUtc` | results are cached for 5 minutes per query and parameters; `ranUtc` is when they were computed |

Status codes: `200` ok, `400` bad body or parameters, `404` unknown division or query (or a query the division can't see), `500` compile error or failed run (the JSON body still says why).

Rules that follow from the sandbox and the API:

- Write a **complete document**: `<!doctype html><html><head>...</head><body>...</body></html>`. Put your scripts at the end of `<body>` (or run them on `DOMContentLoaded`) so `ARBO` exists.
- **Never hardcode** the division id, the host, or test data. Query ids are hardcoded in the HTML, and every one must be listed in `queryIds` when saving.
- The iframe allows scripts only: no `localStorage`, `sessionStorage` or cookies (accessing them throws), no `alert`/`confirm`, no forms that submit, no popups or links that navigate away. Keep state in variables.
- Libraries only from a CDN, with a pinned version, e.g. `https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`. No inlined libraries (the HTML is limited to 400,000 characters).
- Call each query **once per load** and read all its results from that one response. Don't poll more often than every 5 minutes (results are cached for 5 minutes anyway); a manual refresh button is fine.
- Queries can take from one to tens of seconds. Show a loading state per section, and an error state per section (with the message) when a call fails, so one broken query doesn't blank the page.
- Show freshness, e.g. "Updated 3 min ago" from `ranUtc`, and the query's `notes` in small muted text when present.

## Sizes

**Dashboard**: the iframe fills the window height under the CK header and scrolls inside. Lay out for 1,000 to 1,800px width and stay usable down to 700px (CSS grid with `minmax`, tables that scroll horizontally).

**Widget**: a cell of an 8-column grid with a 16px gap. The iframe has a fixed height, and the content must fit it **without scrolling**:

| Width | Typical pixels | Fits |
|---|---|---|
| `1/8` | 120–220 | one KPI number with a label and a delta |
| `1/4` | 260–450 | a KPI with a sparkline, or 2–3 small KPIs, or a 5-row list |
| `1/2` | 550–900 | a small chart, or a table of 5–8 rows |
| `1` | full row | a wide chart or a table of up to 8 rows |

Heights: `1` = 220px, `2` = 456px. Widths change with the screen, so size with percentages and flex/grid, and use `body { margin: 0; height: 100vh; overflow: hidden; }`. Pass `width` and `height` to `save_widget` on creation.

## Design

Match CK's light look so the page doesn't feel embedded:

- Background `#ffffff` for cards on a `#f9fafb` page (widgets: the card is the whole page, `#ffffff` with a `1px solid #f1f2f4` border and `8px` radius).
- Font `system-ui, -apple-system, "Segoe UI", sans-serif`; text `#111827`, secondary `#6b7280`, muted `#9ca3af`; sizes 11–13px for body and labels, 20–28px for KPI values.
- Accent `#4f46e5`; positive `#059669`, negative `#dc2626`. Color profit, ROI and deltas by sign, nothing else.
- Numbers: `font-variant-numeric: tabular-nums`, right-aligned in tables; money `$1,234.56`, large values `$12.3k`; percents with one decimal; never raw floats.
- Tables: sticky header, light row borders, sortable columns when more than a few rows, totals row when it helps.
- Charts: one question per chart, at most 4–5 series, consistent colors for the same metric across the page, no 3D, no pie charts with more than 5 slices; turn off chart animation and legends that repeat the title.
- Hierarchy: KPIs at the top (with the change vs the previous period), then trends, then breakdown tables.

## Skeleton

```html
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  body { margin: 0; padding: 16px; background: #f9fafb; color: #111827; font: 13px system-ui, -apple-system, "Segoe UI", sans-serif; }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
  .card { background: #fff; border: 1px solid #f1f2f4; border-radius: 8px; padding: 12px 14px; }
  .label { color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  .value { font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .pos { color: #059669; } .neg { color: #dc2626; } .muted { color: #9ca3af; font-size: 11px; }
</style>
</head>
<body>
  <div id="kpis" class="grid"><div class="card muted">Loading…</div></div>
  <div class="card" style="margin-top:16px"><canvas id="daily" height="90"></canvas></div>
  <div id="updated" class="muted" style="margin-top:8px"></div>
<script>
const QUERY_ID = "<saved query id>";

async function runQuery(queryId, params = {}) {
  const res = await fetch(ARBO.apiBase + queryId, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
  });
  const body = await res.json().catch(() => ({}));
  const problem = body.error || body.fatalException
    || body.compileErrors?.map(e => e.message).join("; ") || body.parameterErrors?.join("; ");
  if (!res.ok || problem) throw new Error(problem || `HTTP ${res.status}`);
  return { ...body, data: Object.fromEntries(body.results.map(r => [r.name, r.value])) };
}

const money = v => (v < 0 ? "-$" : "$") + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

async function load() {
  try {
    const run = await runQuery(QUERY_ID, { days: 7 });
    const k = run.data.kpis;
    document.getElementById("kpis").innerHTML = [
      ["Spend", money(k.spend), ""], ["Profit", money(k.profit), k.profit >= 0 ? "pos" : "neg"],
    ].map(([l, v, c]) => `<div class="card"><div class="label">${l}</div><div class="value ${c}">${v}</div></div>`).join("");
    new Chart(document.getElementById("daily"), {
      type: "line",
      data: { labels: run.data.daily.map(d => d.date),
              datasets: [{ label: "Profit", data: run.data.daily.map(d => d.profit), borderColor: "#4f46e5", tension: .3 }] },
      options: { animation: false, plugins: { legend: { display: false } } },
    });
    const minutes = Math.round((Date.now() - new Date(run.ranUtc)) / 60000);
    document.getElementById("updated").textContent = `Updated ${minutes < 1 ? "just now" : minutes + " min ago"}`;
  } catch (e) {
    document.getElementById("kpis").innerHTML = `<div class="card neg">Could not load: ${e.message}</div>`;
  }
}
load();
</script>
</body>
</html>
```

## Saving

`save_widget(type, name, description, html, queryIds, width?, height?, showOnHome?, widgetId?)`:
- `type`: `dashboard` or `widget`. It can't be changed later.
- `name` unique per type in the division; `description` says what it shows and which questions it answers.
- `queryIds`: every query id the HTML calls; each must appear in the HTML and be visible to the division.
- `width` (`1/8`, `1/4`, `1/2`, `1`), `height` (`1`, `2`), `showOnHome`: widgets only. Omit them on updates to keep what people set in CK; set `showOnHome` only when the user asks.
- `delete_widget` only when the user explicitly asks to delete that one. Its queries stay.

## Shared memory

If the `memory_*` tools are available (see the **arbo-memory** skill): saving, changing or deleting a dashboard, widget or agentic query is a change, so write one `Journal` entry with what was built and the ids. Building a view is not an insight; write an `Insight` only for a conclusion the user confirmed from the data.

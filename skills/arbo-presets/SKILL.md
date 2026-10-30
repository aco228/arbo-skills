---
name: arbo-presets
description: Read, create and change CK Stats presets, the saved filters on the Stats page (Stats → Presets) that keep adsets by conditions (ROI, spend, days started, country, status, ...), order and limit them, and optionally build an action group for them (kill, pause, activate, budget change, cost cap change, clone, clone with cap, transfer, TikTok clone, replicate). Automated presets build and execute that action on their own. Use when the user asks about their presets, which presets are automated, what a preset does, or asks to create, save, fix, retune or reschedule a preset (list_stat_presets, create_stat_preset, update_stat_preset MCP tools). Not for C# scripts (arbo-scripts) or one-off adset changes (arbo-adset-actions).
---

# Arbo presets

A **preset** is a saved row on the Stats page (Stats → Presets). It has:

1. **A filter.** It decides which of the division's loaded adsets are kept: conditions on metrics, plus lists of countries, statuses, affiliates, accounts, tags and so on.
2. **An order and a limit.** The kept adsets are sorted (`orderBy`, `orderByDirection`), and at most `limit` of them go into the action. `0` means all of them.
3. **An optional action.** This is the action group built for the kept adsets: `actionType` plus its `actionValues`.
   - With no action, the preset is filter-only. A person uses it with the **Filter** button to look at adsets.
   - With an action, the **Group** button builds the action group for a person to review and execute.
4. **Automation (optional).** When the preset is automated and preset automation is on for the division, the stats automation applies the preset by itself. It builds the action and executes it, with real money and real adsets, within the hour window and delay you set.

Every field, every comparator, the condition syntax and every action type are in [reference.md](reference.md). Read it before you create or change a preset. Don't guess field names: the tools reject unknown ones, and the error lists the valid names.

## Tools

| Tool | What it does |
|---|---|
| `list_stat_presets(isAutomated?, textContains?)` | Every preset with its full definition. Only the filter fields that are set are returned. `presetAutomationEnabled` tells whether preset automation runs for the division at all. |
| `create_stat_preset(title, category, description, filter?, actionType?, actionValues?, orderBy?, orderByDirection?, limit?, areKilledIncluded?, automation...)` | Saves a new preset. It is never automated. |
| `update_stat_preset(presetId, ...)` | Changes an existing preset. Omitted arguments keep their saved value, and the filter is merged (see below). |

Things agents can't do:

- **Delete a preset.** Only a person can, in the UI.
- **Turn automation on or off.** Only a person can, in the preset editor. You may prepare the schedule (`automationSource`, `automationFromHour`, `automationToHour`, `automationDelayHours`) so the person only has to flip the switch. Say so in your answer.
- **Run a preset.** Saving never executes anything. To see which adsets a preset would catch right now, write a stats query with the same conditions (**arbo-stat-queries**).

## How a preset runs

**Picking the adsets**

1. Adsets are ordered by `orderBy` / `orderByDirection`.
2. Killed and terminated adsets are dropped unless `areKilledIncluded` is true.
3. The filter is applied. An adset must pass every set condition.
4. The first `limit` adsets that pass go into the action (`0` means all).

The action itself can still skip adsets (for example Pause skips already paused ones, and the budget actions skip adsets whose budget would not change). See reference.md for each action.

**Automation** runs inside each stats refresh of the division, both the today-stats run and the yesterday-stats run. An automated preset acts only when all of these hold:

- Preset automation is on for the division (`presetAutomationEnabled`).
- `automationSource` matches the run (TodayStats, YesterdayStats, or AllStats for both).
- The current server hour is inside `automationFromHour`–`automationToHour`. The server runs on **Central European time (CET/CEST), not UTC**. The from hour is inclusive, the to hour exclusive, and `-1` means no limit.
- On today runs, at least `automationDelayHours` have passed since the preset last built an action group (`automationLastExecutionUtc`). Runs that found no adsets don't count.
- At least one adset passes.

**Presets go first.** Automated presets run before the automated scripts in the same pass. An adset put into an action group by a preset is no longer seen by the later presets or by any script. So an automated preset with a broad filter takes adsets away from your scripts. Check that before you widen one (**arbo-scripts-rebalance** reviews scripts as one system, so mention any automated presets to it).

The preset's `description` is written as the comment on every adset the automation changes. Keep it a clear sentence.

## Working rules

- **Look first.** Call `list_stat_presets` before creating one, so you don't duplicate an existing preset (titles must be unique). Also call it before updating one, so your change starts from what is saved.
- **Explain before saving.** Tell the user, in plain words:
  - which adsets the preset will catch;
  - what the action does to them, with units: budgets are in **cents**, so 5000 is $50;
  - whether it is or will be automated.
- **Only save when the user asked.** Create or update a preset only when the user asked for that change.
- **When the preset is already automated**, the next automated run uses your change. Say so, and be conservative with thresholds and limits.
- **Thresholds come from data, not from memory.** When the user asks for "losers" or "winners", run a stats query first to see the division's actual ROI, spend and conversion distribution. Pick thresholds that are relative to that, and show them to the user.
- **Never filter on one specific affiliate or account** in a preset meant to be automated unless the user asks for exactly that. The division adds and renames them all the time. Prefer `accountTypes` or `trafficProviders`.
- **Always put a condition that proves the signal is real** next to a "bad" condition. For example, `SpendComparator ">10"` or `DaysStartedComparator ">=2"` next to `RoiComparator "<-30"`. Otherwise a new adset with one bad hour gets killed.
- **Updating the filter:**
  - Fields you send replace those fields.
  - Comparators you send replace those comparators. `""` clears one.
  - Everything else stays as saved.
  - `replaceFilter: true` replaces the whole filter.
  - Show the user the full resulting filter returned in `preset`.
- **Updating the action:**
  - Sending only `actionValues` merges them into the saved values.
  - A new `actionType` starts from that action's defaults plus your `actionValues`.
  - `actionType: "None"` removes the action.
- **Errors:** if a call returns `saved: false`, fix every listed error and call again. Never report a preset as saved without `saved: true`.

## Examples

**Kill clear losers** (filter-only shown for review; the user turns automation on themselves):

```json
{
  "title": "Kill losers 3d",
  "category": "Kill",
  "description": "Kills adsets with ROI under -40% today and yesterday after 3 days and $15 spend.",
  "filter": {
    "statuses": ["Active"],
    "comparators": {
      "DaysStartedComparator": ">=3",
      "SpendComparator": ">15",
      "RoiComparator": "<-40&y<-40"
    }
  },
  "actionType": "Kill",
  "orderBy": "ByROI",
  "orderByDirection": "ASC",
  "automationSource": "TodayStats",
  "automationFromHour": 10,
  "automationToHour": 22,
  "automationDelayHours": 2
}
```

**Scale winners by 20%, max $300:**

- `actionType: "BudgetByPercentage"`
- `actionValues: {"PercentageUpgrade": 20, "MaximumBudget": 30000, "MaximumIncrease": 5000}`
- filter comparators `{"RoiComparator": ">30&y>20", "ConversionsComparator": ">=5"}`

**Retune an existing preset's threshold only:** `update_stat_preset(presetId, filter: {"comparators": {"RoiComparator": "<-50"}})`.

## Shared memory

If the `memory_*` tools are available (**arbo-memory** skill):

- **At the start**, call `memory_briefing`, with `scopeLinks` for the preset's country or vertical when it is scoped. Follow the active objectives. A kill or pause preset falls under `kill-policy`; a scale, activate or clone preset falls under `scaling`.
- **After saving**, `memory_save` one journal line: what changed and why.

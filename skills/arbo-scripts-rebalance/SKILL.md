---
name: arbo-scripts-rebalance
description: Review and rebalance a division's automated CK arbo scripts as one system. Finds scripts that work against each other (one scales or activates what another cuts, pauses or kills), checks whether the priority order lets the important scripts act first, spots scripts that break another script's intent and need a rewrite, and finds scripts that currently have no effect (never run, never match, or lose all their adsets to higher-priority scripts). Simulates a full automation pass with dry runs, reads the tag history for real conflicts, then proposes a new priority order and rewrites, and applies them only when the user approves (update_stat_script_code). Use when the user asks to review, audit, check, rebalance or reorder their automated scripts or automation, asks whether scripts conflict or overlap, which script should run first, or why a script never does anything.
---

# Review and rebalance automated scripts

You review the division's **automated** arbo scripts together, not one by one. The user wants four answers:

1. **Opposing scripts.** Do any scripts push the same adsets in opposite directions?
2. **Priority.** Is the run order right, so the script that should decide an adset gets it first?
3. **Violations.** Does a script break another script's intent in any way (takes adsets another one is built for, undoes its work across runs, ignores its cooldown), so one of them needs a rewrite?
4. **No effect.** Does any script currently do nothing?

Then you propose a fix: a new priority order and, where needed, rewrites. You change nothing until the user approves.

## How the automation runs

Know this before judging anything:

- **One pass after each stats collection.** In a pass, the division's automated scripts run **one after another, once each**, from the highest `priority` down. Scripts with equal priority run in name order. Priority is a plain integer and the default is `0`.
- **Adsets are claimed.** When a script puts an adset into an action group, that adset is **removed from what every later script in the same pass sees**: its body is never called for it and its init `Adsets` doesn't contain it. So the higher-priority script wins every adset both would act on, and the lower one never knows.
- **Exception: copies.** Clone, cost-cap clone and transfer actions (`Clone`, `CloneWithBudget`, `CreateCostCap`, `CreateCostCapWith`, `CloneAsCap`, `CloneWithCap`, `ToAnotherAccount`, `ToAnotherSpecificAccount`) don't claim their adsets. Later scripts still see and can act on them. `Include()` and `Ignore()` create nothing and claim nothing.
- **Each script has its own schedule**, and a pass only runs the scripts that are due:
  - `automationSource`: `TodayStats` runs in the today pass, `YesterdayStats` in the yesterday pass, `AllStats` in both.
  - `automationFromHour` to `automationToHour`: the hour window, `-1` means no limit.
  - `automationEveryHours`: the minimum time since the script last **acted** (`lastActionsUtc`). A run that finds nothing doesn't reset it, so a quiet script is checked on every pass.
  
  Two scripts only compete for adsets inside a pass when both are due. Across passes they still see each other's results in the adsets themselves: a new budget, a status, a tag.
- **Scripts first, then presets.** After the scripts, the division's automated presets run on the adsets that are left. You can't read presets with the tools. Mention them when a finding depends on them.
- **Tags are the memory between passes.** A script that sets `TagName = "s:..."` writes the tag on every adset it changes with a status, budget or cost cap action (not clones or transfers). Other scripts can read it (`ad.GetLastTagInHours("s:other") < 12`). Tags are kept 20 days, so they are also your evidence of what really happened.

## Tools

| Tool | Use |
|---|---|
| `list_stat_scripts` with `isAutomated=true`, `includeCode=true` | Every automated script with its code, `priority`, schedule (`automationEveryHours`, `automationSource`, `automationFromHour`, `automationToHour`) and run times (`lastTriggeredUtc`, `lastActionsUtc`, `lastActionsGroups`, `lastActionsAdsets`). They come back in run order. |
| `run_stat_query` | Dry-run the scripts on real adsets and read the tag history (templates in [simulation.md](simulation.md)). Nothing is applied. |
| `get_stat_response_adset_definition` | Current members and enum values when a script's code uses something you need to check. |
| `get_stat_script`, `update_stat_script_code` | Read one script, then change its `priority`, `code` and/or `description`. **Only after the user approves.** |

The tools can change a script's schedule (`automationEveryHours`, `automationSource`, `automationFromHour`, `automationToHour` on `update_stat_script_code`), but can't turn automation on or off. When a fix needs a script switched on or off, tell the user what to change in **Stats → Scripts**.

When the script writing rules matter (a rewrite, a header, a dry-run comparison), follow the **arbo-scripts** skill. Refer to scripts by name with the user.

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (`script:` of the scripts in the review). Then:
- Follow the active **objectives**: they are binding rules set by people. Objectives (`scaling`, `kill-policy`, ...) decide which scripts should win a conflict; a script that works against an active objective is a finding. If the user's request conflicts with one, say so and ask before acting.
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
- At the start, look for the last rebalance: `memory_search` with `types=Decision` and `text="script priority"` (topic `script-priority`). Don't re-argue an agreed order unless the data or the scripts changed since; say what changed.
- After the user agrees: a `Decision` "script priority" (topic `script-priority`, superseding the previous one) with the order and the reason for each move, linked to the scripts.
- After applying changes: a `Journal` entry per run (scripts rewritten, priorities changed).
- A `Task` to re-run the pass simulation and tag-history check after about a week, with the conflicts found now in the snapshot.

## Workflow

### 1. Inventory

Call `list_stat_scripts(isAutomated: true, includeCode: true)`. If nothing is automated, say so and stop. For each script, read the code and header comment and write down:

- **Priority and schedule**: source, window, delay, and whether it's due at the same time as the others.
- **Scope**: which adsets it can touch (status, feed, country, vertical, cap or no cap, age, spend guards).
- **Actions and direction**: stop (`Kill`, `Pause`), start (`Activate`), budget up or down, cap up or down, copy (clones, transfers). Note which of them claim adsets.
- **Its tag** (`TagName`) and the cooldowns it reads, both its own tag and other scripts' tags.
- **Run gates**: `CanRun`, `LastExecutionUtc` or time gates, hour checks, top-N limits in init.
- **Health** from the run times (see step 4).

Show this as one compact table in run order before going further: priority, name, source/window/every, actions, tag, last run, last actions.

### 2. Simulate a pass

Run the **pass simulation** query from [simulation.md](simulation.md). Paste in every automated script that runs in the pass you simulate, with its exact code and priority. It runs each script twice:

- **Standalone**, on all adsets: what the script would do if it were alone.
- **Chained**, in priority order, on the adsets the higher scripts left unclaimed: what it really gets.

It returns, per script, both action counts, how many adsets it **lost** to each higher-priority script, and, for every pair of scripts, the adsets both would act on and how many of them in **opposite directions**.

- Simulate the today pass (`TodayStats` + `AllStats` scripts on `LoadStatsToday()`). Simulate the yesterday pass (`YesterdayStats` + `AllStats` on `LoadStatsYesterday()`) only when yesterday scripts exist.
- The dry run treats every script as due and every `CanRun` gate on `LastExecutionUtc` as open, as on a first run. Correct for it using the schedules: two scripts that are never due together don't compete within a pass, but they still meet across passes (step 3).
- If the query runs too long (2 minutes) or is too large, split the scripts into two runs. Carry the adsets claimed by the first run over to the second, as the template explains.

### 3. Read the history

Run the **tag history** query from [simulation.md](simulation.md) with the tags of the automated scripts. It lists adsets that two or more automated scripts changed in the last N days, which pairs of scripts meet on the same adsets, and in what order. This shows conflicts **across passes** that the simulation can't: one script raises a budget on one pass, another cuts it on a later one, and the first raises it again.

A script without a tag leaves no history. Say so, since that's a finding of its own: it can't be reviewed, and no other script can respect its cooldown.

### 4. Answer the four questions

Base every finding on the code plus evidence (simulation numbers, history, run times), and give the numbers.

**1. Opposing scripts.** A pair works against each other when:
- they act on the same adsets in opposite directions (stop vs start, budget up vs down, cap up vs down, scale or clone vs kill), in the simulation's `opposing` counts or in the history's pairs; or
- they ping-pong across passes: each pass is fine on its own, but together they oscillate. A classic case is a budget raise every 2 h on ROI > X and a trim every 4 h on a fading ROI slightly above X.

Explain the mechanism in one line and which adsets are affected (count, spend, examples).

**2. Priority.** The script whose decision should win an overlap must run first. Common orderings:
- Protective scripts before aggressive ones. Kills, pauses and budget cuts on losers go before scaling, so a loser isn't scaled first and then left alone.
- Specific before general. A script for one feed, country or offer goes before a catch-all that would claim the same adsets.
- A script that must not act on adsets another script is handling goes after it. Claiming then keeps them apart.
- Copies (clones, transfers) don't claim. To stop a clone script from copying an adset that a kill script kills in the same pass, the kill must run **first** (it claims, so the clone never sees the adset). Kill-after-clone clones a dying adset.

Flag a script that loses most of its standalone adsets to a higher one: either the order is wrong, or the two scripts are duplicates.

**3. Violations, needs a rewrite.** Priority can't fix everything. Flag when:
- two scripts overlap because their scopes aren't split, and the right fix is a condition (for example one takes cap adsets and the other takes the rest), not the order;
- a script changes adsets that another script manages across passes without reading its tag (no `GetLastTagInHours("s:other")` guard), so it undoes the other's work;
- the header's `SCOPE`/`PAIRS` don't match the code, or claim a split the code doesn't make;
- a script depends on seeing adsets a higher script claims (a top-N or a total in init that silently shrinks);
- a script has no `TagName` but returns actions.

Propose the concrete change: which condition or guard to add, in which script.

**4. No effect.** Classify each quiet script:
- **Not running**: `lastTriggeredUtc` is null or far older than its delay while it is automated. Check the source, the window (`from` ≥ `to`, a window that never matches) and whether other scripts of the division run. If none of them run, script automation is probably off for the division. The user checks that; you can't.
- **Runs but never acts**: `lastTriggeredUtc` is recent while `lastActionsUtc` is old or null, and the standalone simulation returns 0 actions. The conditions never match the current data (thresholds too strict, a wrong name or enum, a `CanRun` that never opens).
- **Shadowed**: it acts standalone but 0 chained. Higher-priority scripts take all its adsets.
- **Failing**: `lastActionsGroups` is 0 with a `lastActionsUtc` set (compile error or exception), or the simulation returns `CompileError`/`RuntimeError`, or it reports adsets whose body threw.
- **No-op actions**: the script returns actions that the groups drop (`ChangeCostCap` on adsets with no cap, `Activate` on active ones, a budget equal to the current one, `Pause(0)`). The simulation's direction `none` on its actions shows this.

### 5. Report

Keep it short and in this order:

1. **Verdict**: one or two lines. Is the setup healthy, and what is the biggest problem?
2. **Findings** under the four questions, most costly first. Each has what happens, the evidence (numbers, example adsets) and the fix. Skip a question with "none found" when it's clean.
3. **Proposed order** as a table: script, current priority, proposed priority, why. Use spaced numbers (100, 90, 80 ...) so a later script can go in between. Keep scripts that don't interact at their current value rather than renumbering everything.
4. **Proposed rewrites**: per script, the change in one or two lines. Write the full code only when the user asks to apply it.
5. **Schedule changes** (delay, source, hours) you can apply with the tools after approval, and **on/off changes** for the user to make in the editor.

### 6. Apply, only when the user approves

Apply exactly what the user approved, nothing more:

- **Priority**: `update_stat_script_code(scriptId, priority: N)` per script. It takes effect from the next pass.
- **Schedule**: `update_stat_script_code(scriptId, automationEveryHours / automationSource / automationFromHour / automationToHour)`. Hours are server time (Central European, CET/CEST, not UTC), from inclusive, to exclusive. It takes effect from the next pass.
- **Rewrites**: follow the **arbo-scripts** skill. `get_stat_script`, change that code, dry-run it, update the header (`SCOPE`, `PAIRS`) and the description, then `update_stat_script_code` with the full code.
- **Re-check** after applying: run the pass simulation again with the new order and code, and show the before and after (lost adsets, opposing overlaps, per-script chained counts).

Never touch scripts that aren't automated unless the user asks, and never propose disabling a script as the default fix. Say when a script looks redundant and let the user decide.

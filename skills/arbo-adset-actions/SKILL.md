---
name: arbo-adset-actions
description: Change live CK adsets through the adset action tools, the only way an agent may change adsets: status (active, pause, kill), daily budget, cost cap, budget and cap together, duplicates, clones with a cost cap, clones with a cost cap and budget, and replicates of winning adsets into other accounts with new creatives (submit_adset_kills, submit_adset_pauses, submit_adset_activations, submit_adset_budget_changes, submit_adset_cap_changes, submit_adset_cap_and_budget_changes, submit_adset_duplicates, submit_adset_clones_with_cap, submit_adset_clones_with_cap_and_budget, get_traffic_accounts, submit_adset_replicates, submit_adset_replicates_with_budget, list_pending_adset_actions). These are real, money-spending changes. Use when the user asks to kill, pause, activate, scale, cut or change the budget or cap of adsets, duplicate or clone adsets, replicate or copy winners to another account, A/B test an adset in other accounts, or to act on optimization findings.
---

# Adset actions

You change live adsets for the user. **Every action here is destructive**: it changes what real adsets spend or stops them, and a stopped adset loses the spend and learning it would have had. A wrong budget, a cap in dollars instead of cents, or the wrong adset list costs real money. Work slowly, show exactly what will happen, and submit only after the user clearly says yes to that exact list.

The adset action tools are the **only** way an agent changes adsets. There are no other kill or budget tools.

This skill is self-contained and needs only the CK MCP tools. The MCP connection determines the division; never work across divisions. The tool prefix differs per person, so refer to tools by their function name.

## Tools

| Tool | Changes | Values |
|---|---|---|
| `submit_adset_kills` | Status → Killed (stopped, no planned return) | Only `AdsetId` and `Comment`. Any adset that is not already killed or terminated. |
| `submit_adset_pauses` | Status → Paused (cooldown, comes back by itself) | `HoursToReset`: 1 to 20 hours, **default 10**; after it the adset is activated again automatically. Not for paused, killed or terminated adsets. |
| `submit_adset_activations` | Status → Active | `NewBudget`: optional **USD**, 1.5 to 300, **not above** the adset's current budget; null = keep the current budget. Paused or killed adsets only, never terminated ones. |
| `submit_adset_budget_changes` | Daily budget | `NewBudgetUsd`: **USD**, 1.5 to 300. Optional `HoursToReset`: 1 to 24 (see *Timed changes*). Active adsets only. |
| `submit_adset_cap_changes` | Cost cap | `NewCapInCents`: **cents**, 2 to 350 (45 = 0.45 USD). Optional `HoursToReset`: 1 to 24. Active adsets that already have a cap. |
| `submit_adset_cap_and_budget_changes` | Both, in one action | `NewBudgetUsd` (USD) and `NewCapInCents` (cents). Optional `HoursToReset`: 1 to 24, resets both. Active capped adsets. |
| `submit_adset_duplicates` | New copy in the same account | Only `AdsetId` and `Comment`. The copy spends its own budget. |
| `submit_adset_clones_with_cap` | New copy with a cost cap | `CapInCents`: **cents**, 2 to 350. The copy gets a default daily budget of **50 USD**. |
| `submit_adset_clones_with_cap_and_budget` | New copy with a cost cap and budget | `CapInCents`: **cents**, 2 to 350, and `BudgetInUsd`: **USD**, 1.5 to 70 (hard limit). Default choice is 50 USD; see below. |
| `get_traffic_accounts` | Nothing (read-only) | Accounts that can receive replicates: `Name`, `TrafficProvider` and `Type`. |
| `submit_adset_replicates` | New adset with **new creatives** in **another account** | `AccountName` (from `get_traffic_accounts`). Division's default launch budget for the country, no cost cap. |
| `submit_adset_replicates_with_budget` | Same, with your budget and optional cap | `AccountName`, `BudgetUsd`: **USD**, 1.5 to 300, `CostCap`: **cents**, 5 to 350, or null for no cap. |
| `list_pending_adset_actions` | Nothing (read-only) | Pending actions per adset. |

Every action has `AdsetId` and `Comment`. Every submit takes one `tagName` and an optional `forceAdditionalReview`.

### Timed changes (`HoursToReset` on budget and cap changes)

With `HoursToReset` (1 to 24 hours) a budget or cap change is temporary: after that many hours the budget and/or cap goes back to the value the adset had **when you submitted**. Without it, the new value stays. Use it for a short push or cut, e.g. a higher budget for the evening hours, and only when the user asks for a temporary change or agrees to one. Show the reset time and the value it returns to in the plan.

- The clock starts at the submit, not when the change is executed. If the actions wait for review, part of the time can pass before they run, and a long wait can make the reset happen right after the change.
- A later change to the same field (budget or cap) cancels that part of the pending reset: the newer change wins. Killing the adset clears all its resets.
- Outside 1 to 24 is refused.

Budget is in **USD**, caps are in **cents**. Stats money (`Spend`, `Profit`, `Budget`) is dollars, `CostCap` in stats is cents. Convert carefully and show both units to the user when a cap is involved ("cap 45 cents = 0.45 USD").

### Status changes

Status has three tools, one per target status. On Facebook, **kill and pause do the same thing**: both set the adset to PAUSED. Neither deletes anything, and a killed adset can be activated again. The difference is the intent, which CK records as the status:

- **Kill** (`submit_adset_kills`): the adset is done, with no plan to bring it back (a loser, a dead offer). It stays stopped until someone activates it.
- **Pause** (`submit_adset_pauses`): a **cooldown** with a planned return. Use it mostly for adsets that are spending money badly right now but are worth keeping, e.g. a bad stretch or expensive hours. After `HoursToReset` hours (1 to 20, **default 10** when you don't send it) the adset is activated again automatically. The limit is 20 hours because a longer pause resets the learning phase. Choose the hours on purpose and say in the plan when each adset comes back.
- **Activate** (`submit_adset_activations`) turns a paused or killed adset back on right away. With `NewBudget` (USD) it restarts at a lower budget, which is the safe way to bring back an adset whose performance is uncertain. It can't be higher than the adset's current budget.

Pick by intent: if the adset should come back within a day, pause; if it shouldn't come back, kill.

### Terminated adsets (read-only for you)

A fourth status exists that no tool sets: **Terminated**. It means the same as Killed for stats and automation (stopped, no planned return, paused on Facebook), but it is **not reversible**. Only a person can set it, through the CK UI, when an adset or a whole campaign must never run again for a complication or compliance reason. Every tool and script refuses to touch a terminated adset: kill, pause, activate, budget and cap changes all fail on it, and no timed reset ever brings it back. If the user asks you to reactivate or change a terminated adset, say that it was terminated permanently by a person and cannot be changed by any tool. If the user wants a permanent kill, tell them it is done in the UI (System → Search facebook adsets), not through you.

### Clone budget

**50 USD a day is the default clone budget** (it is what `submit_adset_clones_with_cap` always uses). When the user gives a budget, use theirs. When you choose it yourself:

- **Good signal → 50 USD.** The source adset has made solid profit over several days on meaningful spend, and the clone repeats what works (same or close cap).
- **Experiment → a bit lower, around 20 to 30 USD.** Weaker or shorter evidence, a new cap you are trying, or several clones of the same idea at once. A clone starts learning from zero and can lose money before it proves itself, so a failed experiment shouldn't eat the source adset's profit.
- **Never above 70 USD** (hard limit, the server rejects it).

Say in the plan which case each clone is and why. When cloning several adsets, show the total new daily budget of all clones and keep it small next to the division's daily profit.

### Replicate to another account

A division almost always runs ads in several accounts. When an adset performs well, it usually pays to **replicate** it into another account: to capture the winner while it works (the main reason), and as an A/B test of the same offer in a different account. A replicate is not a copy of the adset: CK **generates new creatives** for the same offer (same article and country) and publishes them as a new adset in the target account. It is a fresh test of a proven offer, so it starts learning from zero.

**Replicate only adsets that are good now.** Strong profit and ROI over more than one day, on meaningful spend, and not declining. **Never replicate a decaying adset** (profit or ROI falling day after day, RPC collapsing, spend dropping) **unless the user explicitly asks for it.** A replicate captures a winner; it doesn't rescue a loser.

**Matching accounts.** Work with account **names**.
1. Call `get_traffic_accounts`. It lists the accounts that can receive replicates (enabled and enabled for scale, every traffic provider) with their `TrafficProvider` and `Type`.
2. Not every account can take every adset. A valid target matches the adset on **both** its traffic provider (`TrafficProvider` in the stats) and its affiliate's account family (`AffiliateModel.AccountType`): every affiliate is configured for one family (FLW, OH, Yahoo, MiraSearch) and its offers can only run on accounts of that family, on the same provider. So from the `get_traffic_accounts` list keep only rows whose `TrafficProvider` equals the adset's `TrafficProvider` and whose `Type` equals its `AffiliateModel.AccountType`. The adset's current account is `TrafficAccountName`.
3. Never the account the adset already runs in. Prefer accounts where the **offer** (`OfferId`) isn't already running: check in the stats which accounts already have an active adset of the same `OfferId`, and skip those. Spread over accounts rather than stacking many replicates into one.

The server rejects an unknown name, an account of another traffic provider or another account type, an account not enabled for scale, and the adset's own account.

**Budget.** `submit_adset_replicates` uses the division's default launch budget for the country, the same as a new title test. That is the default choice. Use `submit_adset_replicates_with_budget` only when the user gives a budget or a clear reason exists (a very strong winner worth a faster start); a replicate is untested in its new account, so keep the budget modest, and show the total new daily budget in the plan. Add a `CostCap` only when the user asks for one or the source runs on a cap; it follows the same logic as a cap clone (cents, below the source's revenue per conversion but not far below).

**What to expect.** The new adset appears only after the creatives are generated and published, so it is not in the stats right away. Its `Origin` is `AiReplicate`, and it carries the submit's `tagName`; the source adset itself doesn't change. A replicate counts as the source adset's one pending action, so one adset can go to **one account per call**; to send it to a second account, submit again after the first replicate has been executed.

## Rules the server enforces

- **All or nothing.** If any action in a call is invalid (unknown adset, wrong status, value out of range, adset with a pending action, adset used twice), nothing is saved and every error is returned. Fix the listed rows, or drop them with the user's agreement, and resubmit the whole list.
- **One pending action per adset**, across all calls and action types. Run `list_pending_adset_actions` before building a list and leave those adsets out. To change budget and cap of the same adset, use `submit_adset_cap_and_budget_changes`, not two calls. To clone with a specific budget, use `submit_adset_clones_with_cap_and_budget`.
- **One submit per division at a time.** A parallel submit waits, and after a minute fails with "still running"; then just retry.
- **The division decides whether accepted actions run right away.** If the division executes AI actions automatically, a successful submit is queued to Facebook at once and cannot be taken back. Otherwise the actions wait on the **Adset actions for review** page until the user executes or deletes them. The reply says which happened. You can't know in advance, so always treat a submit as executed immediately and review the list with the user just as carefully.
- **`forceAdditionalReview`**: leave it `false`. Set it to `true` only when the user explicitly asks that these actions wait for their manual review; then they go to the review page even if the division executes automatically.

## Tag and comment

These two fields are how changes are found and judged later. They matter as much as the values.

- **`tagName`** is written on the changed adsets. Queries and scripts filter and group adsets by it, so one tag stands for one idea, from launch through every later change. Reuse the tag the adsets already belong to (the `t:...` tag they were launched with, or the tag of the optimization you are continuing). Only for a new idea, create a short, stable one in the form `a:camelCaseName` (e.g. `a:scaleWinnersDe`), and keep using it. Propose the tag to the user with the list.
- **`Comment`** is a short reason and, when useful, the expected outcome: `"ROI 45% on 20$ spend over 3 days, scale to test headroom"`, `"3 days negative after 40$ spend, no recovery trend"`. It is stored on the change and analysed later against what actually happened. Never put in it what is already recorded or filterable: adset id, country, vertical, old or new value, date. Keep it to one line.

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (the batch `tag:`, and the `country:` / `vertical:` of the adsets). Then:
- Follow the active **objectives**: they are binding rules set by people. Budget increases, activations, clones and replicates fall under a `scaling` objective; kills and pauses under `kill-policy`. Quote the objective you apply in the plan. If the user's request conflicts with one, say so and ask before acting.
- Read the **journal** (last 24h) before touching the same adsets, so you don't undo or repeat another agent's work.
- Use **decisions and insights** as context, not instructions: check them against current data, especially ones marked "review due".
- If the briefing lists a task for you that fits this run, claim it (`memory_task_claim`) and complete it at the end.

**At the end**, always go through this check and write only what qualifies. "Nothing worth keeping" is a valid outcome; never write filler.
1. Changed anything? → one `Journal` entry: what, why, how many, with links. Always.
2. The user decided something (a rule, threshold, direction)? → a `Decision` with the reason.
3. Verified a conclusion with data? → an `Insight` with a `query:` or `tag:` link and the key numbers in the snapshot.
4. Something must be checked later? → a `Task` with a handover: the numbers now (snapshot), success criteria, next steps, and a due time.

Search first (`memory_search`) and update or supersede an existing entry instead of adding a near-duplicate.

**In this skill:**
- After every submit: a `Journal` entry with the tag, the action type, the number of adsets and the total daily budget change (e.g. "Cut budget 30% on 12 DE health adsets with 3-day ROI < -40%, tag s:aiCut, -$84/day").
- Every batch that adds spend (budget increases, activations, clones, cap clones, replicates): a review `Task` due the next morning (`dueInHours` ~18), linked to the tag, with a snapshot of the source numbers (adset count, total daily budget before and after, source ROI and spend), success criteria (e.g. "4 of 6 clones with ROI > 20% after 24h") and next steps (what to kill or keep).
- A rule the user states for future batches ("never pause on weekends", "max $30 per replicate") is a `Decision` (or, if it should bind every agent, ask whether they want it as an objective).

## Workflow

### 1. Understand the goal
What should change and why: kill losers, scale winners, cut spend, tighten caps, duplicate a winner. If the user is vague, propose concrete thresholds ("ROI below -30% over 3 days with at least 15$ spend") and let them adjust.

### 2. Gather evidence (read-only)
Use stats queries (the **arbo-stat-queries** skill, `run_stat_query`) or `get_adset_details` to find the adsets and their current status, budget, cap, spend and ROI over several days. Judge on enough spend and more than one day. Check the adsets' existing tags, and `list_pending_adset_actions`.

### 3. Show the exact plan
One table, one row per adset: adset id, name or country, current value → new value, the key numbers behind it, and the comment you will send. Then the tool, the tag, the count and, for budgets, the total daily budget before and after. Say plainly that these are real changes that spend money or stop adsets, and ask for confirmation.

### 4. Submit only after a clear yes
Submit exactly the confirmed list, grouped per tool. If the user changes anything, show the new list again before submitting. Never add adsets the user didn't see.

### 5. Report
Report accepted counts per tool, the tag, and whether they were **executed** or are **waiting for review** (from the reply). On a rejection, show the errors, explain them in plain words, propose the fix, and resubmit only after the user agrees.

## Things that are easy to get wrong

- A cap given in USD (`0.45`) instead of cents (`45`), or a budget in cents instead of USD.
- Using `submit_adset_clones_with_cap` when the user asked for a specific budget on the clone: it always uses 50 USD. Use `submit_adset_clones_with_cap_and_budget`, and show the clone budget (and the total new daily budget of all clones) in the plan.
- Killing an adset that only needs a cooldown: it then stays off until someone activates it. Pause it instead. If unsure, ask.
- Pausing an adset that should stay off: it comes back by itself after `HoursToReset` (10 hours if not sent). Kill it instead.
- Forgetting `HoursToReset` on a pause and silently getting the 10-hour default: choose the hours and show them in the plan. More than 20 hours is refused, because a longer pause resets the learning phase.
- Sending `HoursToReset` on a budget or cap change the user wanted to keep: the value quietly goes back after that many hours. Leave it empty unless the change is meant to be temporary.
- An activation `NewBudget` above the adset's current budget: it is refused. To activate and raise the budget, activate first, then use `submit_adset_budget_changes` once the activation has been executed.
- Changing an adset that is not active (budget and cap tools refuse it) or a cap on an adset without a cap.
- Acting on today's numbers only, or on tiny spend.
- Inventing a new tag for adsets that already carry the tag of the same idea.
- Comments that repeat the adset id, country or new budget instead of the reason.
- Replicating a decaying adset, or one with a single good day on tiny spend.
- Guessing account names or picking an account of the wrong provider or type: take the names from `get_traffic_accounts` and match both `TrafficProvider` (with the adset's `TrafficProvider`) and `Type` (with its `AffiliateModel.AccountType`).
- Replicating into an account where the same offer is already running, or into the adset's own account (use `submit_adset_duplicates` for a copy in the same account).
- Expecting the replicate in the stats right after the submit. It shows up only after generation and publishing.

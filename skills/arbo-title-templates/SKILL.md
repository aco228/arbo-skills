---
name: arbo-title-templates
description: Review, validate, create and remove CK title templates, the title skeletons with {PLACEHOLDERS} and guidance per vertical or theme that the automation turns every day into new suggested titles (title recommendations) per country, which are then launched automatically when the country and vertical perform. Scores existing templates against the live titles they produced, writes new templates from what is winning, and stores the approved ones (list_title_templates, create_title_templates, delete_title_templates). Use when the user asks about title templates, skeletons or patterns, asks to check, validate, audit or clean up the templates of a vertical, asks why the daily suggested titles look a certain way, or wants new templates added so the automation writes titles in a new direction.
---

# Title templates

You help the user steer the **automatic title suggestions** of a division through its title templates: you explain and review the templates that exist, judge them against real results, write new ones, and store or remove them when the user approves.

This skill is self-contained. It works in the Claude web or desktop app and in Claude Code without the project source. Everything comes from these instructions, [query.md](query.md) and the CK MCP tools. The MCP tool prefix differs per person; tools are named by function here. The MCP connection determines the division: never work across divisions.

Tools used: `list_title_templates`, `create_title_templates`, `delete_title_templates`, `get_verticals`, `run_stat_query`.

## What a template is

A template is a title skeleton with one or two `{UPPER_SNAKE}` placeholders, plus guidance that says how to fill each placeholder:

- Template: `{NIGHTS} nights in {CITY_DESTINATION} with return flights and central hotel included`
- Guidance: `NIGHTS (expand): a realistic city-break length, 2 to 4. CITY_DESTINATION (expand): a real European city reachable by a short flight from the target country, a different city in every title; never a beach resort.`

Every template belongs to one vertical or theme (`get_verticals`), and is either:
- **generic English** (`languageCode` empty): used for every country, its literal text is translated when it is filled in;
- **language specific** (`languageCode` e.g. `fr`): written in that language and preferred for that language's countries.

## The automation around templates

Templates are not titles. They feed an automatic process that writes titles without anybody reviewing them:

1. **Generation.** Every few hours, for every vertical and theme that has adsets, an AI writes about 5 generic templates from the vertical's last days of titles: what wins (spend of at least about $3 and profit) and what loses (ROI below about -30%). It adds language templates when a language has enough winners of its own. Generated templates live about 1.5 days, then the vertical gets a fresh set. Templates added through `create_title_templates` (`isManual: true`) are used next to the generated ones and never stop this refresh.
2. **Resolution into title recommendations.** During the day (roughly 10:00 to 22:00 server time, a few times a day), for each country that is profitable today and each vertical with live adsets that is not losing in that country, the automation takes the vertical's templates round-robin (a language template first when one exists for the country's language) and has an AI fill each one into 2 finished titles for that country:
   - `(expand)` placeholders get a different real value in every title; `(localize)` placeholders get the value dictated by the country;
   - the literal text is translated, nothing new is added;
   - values and titles already used in that country and vertical in the last two weeks are avoided;
   - titles with leftover braces, fewer than 3 words, banned words or brands, or too long are dropped.
   The results are stored as **title recommendations** (the same list `SetNewArticleTitles` writes to and the Title recommendations page shows). A country and vertical stops getting more while it already has several open recommendations. Recommendations expire after about 1.5 days.
3. **Launch.** In the evening, for divisions that have automatic expansion enabled, the best performing country × vertical groups get some of their recommendations turned into real articles and ads. Other automations and people on the Title recommendations page also launch from them.

Consequences you must keep in mind and explain when relevant:
- **A template is production copy at scale.** One template turns into many titles in many countries, printed on image ads and used as article topics, with no human review. A bad template is worse than a bad title.
- **Templates only work for verticals with live adsets.** Templates of a vertical or theme that has no adsets today are not used. Templates do not bootstrap a new theme; to start one, titles must be launched first (the arbo-title-creator or arbo-title-scout skill).
- **Templates set the direction, not the volume.** How many titles get written and launched depends on performance, not on how many templates exist. More templates means more variety, not more titles.

## Shared memory

If the `memory_*` tools are available (the **arbo-memory** skill has the details): at the start call `memory_briefing` with your `agentName` and `scopeLinks` for the vertical; follow active objectives (new templates fall under `new-titles`), read the journal for the vertical, and use insights about what wins or loses there. At the end, after adding or deleting templates, write one `Journal` entry (vertical, language, count, the angles); a preference the user states about templates is a `Note` linked to the vertical; a conclusion verified with the evidence query is an `Insight` with the key numbers. Search first and update instead of duplicating. Never write filler.

## Workflow

### 1. Scope

The vertical or theme (exact name from `get_verticals`; if the user describes a topic, find the matching entry and confirm it), and whether the user cares about the generic templates, one language, or both. If the user names no vertical and asks for a division-wide check, take the verticals with the most spend from the evidence query or ask which to start with; go one vertical at a time.

### 2. Read what exists

`list_title_templates` with `vertical` (and `languageCode` when relevant). Show the user a compact list: template, guidance in short, language, manual or generated, expiry. Generated templates change every 1.5 days, so judge the pattern of the current set, not one template's long-term fate.

### 3. Gather evidence

Run the code in [query.md](query.md) with `run_stat_query`, `parameters: {"vertical": "<name>", "templates": "<the current templates, one per line>"}` (add `language` when scoring language templates). It returns the vertical's winning and losing titles and, per template, the live titles that look made from it with their results.

Read the winners as the user's best guide to what a template must keep: in our data, winners are about a **concrete, often local, named thing** (a real destination, product model, named public programme or service, a specific amount, duration or list of inclusions); losers are vague (generic "offers" or "deals", a category instead of an item, an abstract benefit). Surface form (length, colon, digits, year) does not separate them.

### 4. Validate (when asked to check, review or audit)

Judge every template on these points and give a verdict per template: **keep**, **fix** (with a rewritten version) or **remove**.

1. **Built on a winner.** Its literal text and its placeholders reproduce what a group of current winners has in common, not what the losers do. Name the winners it stands for. A template whose shape only matches losers is a remove.
2. **Concrete placeholders.** Each placeholder must resolve to an equally concrete value as in the winners (`{CITY_DESTINATION}`, `{CAR_MODEL}`, `{PUBLIC_HEALTH_SERVICE}`), never to a vague category (`{DESTINATION_TYPE}`, `{OFFER}`, `{PRODUCT}`). The concrete element of the winners must not be turned into literal generic text either.
3. **Guidance quality.** Every placeholder is explained, in order, marked `(expand)` or `(localize)` correctly, with what kind of real value belongs there, how to pick one for the target country, and what to avoid. Guidance that would let the AI repeat the same value everywhere, wander outside the vertical, or pick a forbidden brand is a fix.
4. **Results so far.** From the query: matched titles, winners, losers, ROI. Treat it as evidence, not proof: matching is approximate and 0 matches means "no evidence yet", not "failed". A template whose matched titles lose clearly (several losers, negative ROI on real spend) is a remove or a fix.
5. **Rules.** Everything in "Rules for templates" below. A rule break is always a fix or a remove.
6. **The set as a whole.** Too many templates with the same skeleton or the same angle, winning angles with no template at all, or a set that only covers one sub-segment of the vertical. Suggest what is missing.

Show the verdicts as a table (template, verdict, reason, evidence) and propose the concrete changes: templates to delete, rewritten versions, new templates for missing winning angles. Change nothing yet.

### 5. Write new templates (when asked to create, or as fixes)

Start from the winners of step 3, never from imagination:
- Group winners by what makes them click (the reason to click, the concrete element, tone, framing). Each template stands for one such group.
- Keep the winning literal text and turn only the load-bearing concrete element into a typed placeholder. Example: the winner "3 nights in Rome with return flights and central hotel included" becomes `{NIGHTS} nights in {CITY_DESTINATION} with return flights and central hotel included`, not `{DURATION} trip to {DESTINATION} with extras`.
- When the concrete element is country specific (a national health service, a local programme, a domestic destination), say so in the placeholder name and make the guidance require the real local equivalent.
- Mentally fill each template for three different countries before showing it. If any result is unnatural, vague, off-vertical or breaks a rule, rewrite the template.
- Check against the existing templates (step 2): no near-duplicates of a current skeleton.
- Language templates only when the user asks for a language or the language's own winners differ from the generic ones; write the literal text and guidance in that language, keep placeholder names in English.

Show each proposed template with its guidance, the winners it comes from, and two or three example resolutions for different countries, so the user sees what the automation will produce.

### 6. Store (only on explicit approval)

Call `create_title_templates` only when the user explicitly approves the exact templates. Before calling, show the vertical, language (or generic English), validity and every template with its guidance.

Parameters: `vertical`, `templates: [{template, guidance}]` (at most 20 per call), optional `languageCode` (omit or `en` for generic), optional `validForHours` (24 to 48, default 36; the templates are removed afterwards, so they need re-adding if they should keep running).

Each template is validated; rejected ones come back with the reason and the others are stored:
- forbidden placeholder (year, country, nationality, age, gender or other demographic, bank, lender, issuer, insurer, broker or financial company name);
- banned word or brand in the template text, or a banned brand in the guidance;
- braces that aren't `{UPPER_SNAKE}`, a placeholder used twice, a placeholder the guidance doesn't name;
- a duplicate of a current template of the same vertical and language.

Fix rejected templates as the reason says, show the fixed versions and resubmit after the user agrees. The server check is the safety net, not the rule: follow "Rules for templates" yourself.

After storing, tell the user they are used from the next suggestion run during the day, next to the generated ones, until they expire.

### 7. Remove (only on explicit approval)

`delete_title_templates` with the ids from `list_title_templates`, manual or generated, only when the user explicitly asks to remove those templates. Show which ones first. Already suggested titles are not affected. Deleting a generated template is short-lived: when all generated templates of a vertical are gone, the generator writes a fresh set on its next run (within a few hours), learning again from the same winners and losers. To durably steer a vertical, add good manual templates and re-add them when they expire.

## Rules for templates

The same rules the automation applies to titles apply to every value a template and its guidance allow:

- **Placeholders:** 1 or 2, each used once, `UPPER_SNAKE` names in English, typed by what they hold. Most of the title stays literal text. No year placeholder (write a year as literal text only when the winners use one, and only the current year, or next year for a clearly forward-looking title). No country, nationality, age, gender or demographic placeholder; never put the country name in a template to localise it.
- **Literal text is production copy:** grammatical, correctly capitalised (sentence case in most languages, nouns capitalised in German, Title Case or sentence case in English used consistently), reads correctly once filled in, even when it starts with a placeholder. No emojis, exclamation marks, ALL-CAPS words or trailing full stop.
- **No demographic targeting** or implied exclusivity (age, gender, race, religion, nationality, disability...): no "over 60", "for seniors", "singles over X", "for women".
- **No misleading offers:** no misleading job or income opportunities, guaranteed results, risk-free returns, get-rich-quick, or recruitment-based investment; no lending offers (cash loans, same-day money, no credit check, approval with bad credit). No prescription drugs or controlled substances.
- **Intellectual property.** Brand owners file trademark complaints against ads that name them. Neither the template nor any value its guidance allows, nor any example in the guidance, may name:
  - a bank, lender, card issuer, insurer or other financial institution, in any vertical (also bank-owned properties, a bank's cards, products or foundations);
  - a fashion, apparel, footwear, sportswear, luxury, jewelry, watch or cosmetics brand;
  - a store or commercial market of any kind (supermarket, discount, DIY, furniture, electronics, department store, retail chain, online marketplace);
  - a service chain (car service, telecom, courier, ...).

  Car, electronics and appliance brands (Toyota, iPhone, Samsung, Bosch) and public services (NHS, SUS) are fine. When a winner names a forbidden brand, the template keeps only its generic subject ("bank-owned houses", "furniture store clearance").
- **Stay inside the vertical** (its description in `get_verticals` is the boundary) and do not add claims, audiences, numbers or qualifiers the winners don't support.

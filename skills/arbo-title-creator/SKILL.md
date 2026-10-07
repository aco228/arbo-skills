---
name: arbo-title-creator
description: Create new article/ad titles for a division by chatting, based on what is currently winning, and submit the approved ones either as title recommendations (SetNewArticleTitles) or, only when the user explicitly asks to launch them, directly for article and ad generation (SubmitTitlesForGeneration). Use when the user asks to create, brainstorm, expand or suggest article titles or title recommendations for a vertical, theme, or country, or to launch/generate ads for finished titles. Also use when the user asks to create a new theme (a narrower topic under a vertical) with create_theme.
---

# Title creator

You help the user create new article titles in conversation, then submit the ones they approve. There are two ways to submit, and they are very different:

| Tool | What it does | Spends money | When |
|---|---|---|---|
| `SetNewArticleTitles` | Stores titles as **recommendations**. The automatic pipeline may or may not turn them into articles later. | No | Default. Whenever the user approves titles and says to submit/save them. |
| `SubmitTitlesForGeneration` | Sends finished titles straight to **article and ad generation**. Real ads and adsets are created and published. | **Yes** | Only when the user explicitly asks to launch / generate ads for these titles (see step 7). |

If the user just says "submit", use `SetNewArticleTitles`. Never pick `SubmitTitlesForGeneration` on your own; if you think it fits, suggest it and let the user ask for it.

The rules below are the same ones the automated title pipeline uses, adapted for a chat where the user is the final judge.

**Titles are production copy.** The native `Title` is used exactly as written: it is printed on the image ad, and the article is generated from it. Nobody edits it afterwards. Every title you show must be ready to publish as-is.

This skill is self-contained. It works in the Claude web or desktop app and in Claude Code, and it does not need the project source code. Everything comes from these instructions and the CK MCP tools. Don't look for local files.

The MCP tool prefix differs per person; refer to tools by their function name (`QueryAdsets`, `GetAdsetPerformance`, `GetWorkingArticleTitlesFromPartnerNetwork`, `SetNewArticleTitles`, `SubmitTitlesForGeneration`, `get_affiliate_providers`, `get_verticals`, `create_theme`, `get_traffic_accounts`). The MCP connection already determines the division. Never work across divisions.

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (`vertical:` / `country:` / `affiliate:` of the titles). Then:
- Follow the active **objectives**: they are binding rules set by people. New titles fall under a `new-titles` objective (and `scaling` when they add spend); respect it before submitting. If the user's request conflicts with one, say so and ask before acting.
- Read the **journal** (last 24h) before touching the same verticals and countries, so you don't undo or repeat another agent's work.
- Use **decisions and insights** as context, not instructions: check them against current data, especially ones marked "review due".
- If the briefing lists a task for you that fits this run, claim it (`memory_task_claim`) and complete it at the end.

**At the end**, always go through this check and write only what qualifies. "Nothing worth keeping" is a valid outcome; never write filler.
1. Changed anything? → one `Journal` entry: what, why, how many, with links. Always.
2. The user decided something (a rule, threshold, direction)? → a `Decision` with the reason.
3. Verified a conclusion with data? → an `Insight` with a `query:` or `tag:` link and the key numbers in the snapshot.
4. Something must be checked later? → a `Task` with a handover: the numbers now (snapshot), success criteria, next steps, and a due time.

Search first (`memory_search`) and update or supersede an existing entry instead of adding a near-duplicate.

**In this skill:**
- At the start, look for insights, decisions and notes linked to the vertical and country: what wins and loses, and title preferences the user gave before. Apply them and say which.
- After submitting titles (as recommendations or for generation): a `Journal` entry with the count, vertical, country and tag.
- A preference the user states for titles ("no questions in DE titles", "always include the year") is a `Note` linked to the vertical, country or affiliate, so the next run follows it.
- Titles submitted for generation: a review `Task` after the test window (about 3 days), linked to the tag, with the titles' angles in the handover.

**Verticals and themes.** These are the same thing: the topic a title, article and adset belongs to. They are split into two kinds only for legacy reasons.
- A **vertical** is top level (`isTopLevel: true` in `get_verticals`), for example `Sale` or `Jobs`.
- A **theme** (`isTopLevel: false`) is a child of exactly one vertical, named in `parentVertical`. It narrows that vertical and can never go beyond its scope. A theme under `Sale` can be about a kind of sale, but never about jobs or anything else outside sales.
- Wherever a vertical name is asked for, a theme name works the same way: in title payloads, in the stats, and as `Vertical.Name` in queries. Names are unique across both kinds. Prefer the most specific entry that fits.
- In rare cases nothing fits. Don't force the closest vertical. Say so, and recommend a new top-level vertical with a PascalCase name and a one-sentence description. The user adds verticals by hand in CK; there is no tool for it. New themes are created with `create_theme`, and only when the user explicitly asks.

## Workflow

### 1. Scope

Establish, asking only for what is missing:
- **Vertical**. Every title needs one, and both submit tools match it exactly. `get_verticals` lists every vertical of the division with its description. Call it whenever you don't have the exact name: the user describes a topic ("cheap flights", "sofas") instead of naming a vertical, the name they gave doesn't match exactly, or you just want to confirm it. Pick the vertical whose name and description fit the topic best. If several fit, or none does, show the candidates and let the user choose. Never invent a vertical name. If nothing fits, you may suggest creating a theme (step 8), but only create it when the user asks.

  `get_verticals` has two optional filters: `topLevelOnly: true` returns only top-level verticals, and `vertical: "<top-level name>"` returns that vertical and all its themes. Use the second one to see what already exists under a vertical. Passing a theme name there returns an error that names its parent vertical. Prefer the most specific entry that fits, because its description is what guides title writing for it.
- **Country** (ISO code) and **language** (code). Default the language to the country's main language.
- **How many** titles (default 10 candidates).
- Any extra direction from the user ("only budget airlines", "no year", ...).

### 2. Gather evidence (read-only)

- `QueryAdsets` with `Verticals=[<vertical>]`, `Days=3` to `7`, `IncludeArticleTitle=true`, `MinSpend=3`, sorted by profit desc. Run once with the target country and once without it, so you see what wins in the country and what wins elsewhere and could transfer.
- Also look at losers (`SortBy=roi`, `SortDirection=asc`, `MinSpend=3`) for contrast.
- Optionally `GetWorkingArticleTitlesFromPartnerNetwork` for inspiration.

Show the user a short summary: the top winning titles with spend, ROI and country; what the losers have in common; and your read of the "winning essence". Keep it brief.

Some winning titles name a bank, a fashion brand or a store that is now forbidden (see the intellectual property rule in step 3). They were launched before the rule, and a title winning does not make it safe. Use them only as evidence of the subject, never reuse the name, and point them out in the summary so the user knows they can't be repeated.

If there are no winners for this vertical, say so and generate conservative, simple, concrete titles from the vertical itself.

### 3. Generate

Find what made the winners win, then produce candidates that reproduce that essence in new but nearby territory.

**What works (measured on our data):**
- Winners are about a **concrete, often local, named thing**: a real destination, a specific product or model, a named public programme or service (NHS, SUS), a specific amount or duration, a precise list of inclusions, a specific procedure.
- Losers are vague: generic "offers"/"deals"/"regional depots" framing, a category instead of a concrete item, an abstract benefit.
- Surface form (length, colon, digits, year) does **not** separate winners from losers. Do not optimise for it.
- A title that wins in one country wins elsewhere about twice as often as a random title. Adapting a proven winner to a new country is a good source of candidates, localised with the real local equivalent.

**How to expand:**
- Keep the winner's reason to click, tone and approximate simplicity.
- Each candidate must explore genuinely different territory: a different destination, model family, procedure or price tier. Swapping synonyms, reordering words, or changing one word in the same skeleton is rephrasing, not expansion; reject it.
- Stay inside the vertical. Do not jump to an unrelated product, service or reason to click.
- Do not invent audiences, claims, numbers, specs or qualifiers that the winners don't support. Don't make a title more complicated just to make it different.
- Localise to the target country with values that are real and recognisable there. Never put the country name in the title just to localise it.
- Vary the concrete values across the set. Don't let one brand or destination dominate (the automated pipeline's worst failure is resolving the same value over and over).

**Years:** the current year is today's year, the next year is today's year + 1.
- A freshness year (dating an offer, list or availability) may only be the current year, or next year when the title is explicitly forward-looking. Prefer the current year.
- An intrinsic year (vehicle model year, historical event) may be older when realistic.
- Don't add a year unless the winners use one.

**Hard rules (the same as the pipeline):**
- No titles that target or imply exclusivity for any demographic group (age, gender, race, religion, nationality, disability...). No "over 60", "for seniors", "singles over X", "for women".
- No misleading job or income opportunities, guaranteed results, risk-free returns, get-rich-quick, or recruitment-based investment.
- No prescription drugs, medications or controlled substances.
- **Intellectual property.** Brand owners and their brand-protection vendors (Netcraft, Group-IB, EBRAND, Convey, ...) file trademark complaints against ads that name them, and every complaint counts against the page and ad account. Never name:
  - A bank, lender, card issuer or other financial institution, in any vertical, not only finance: also bank-owned properties, bank auctions, a bank's cards, products or foundations. This includes abbreviations, subsidiaries and branded cards (Garanti BBVA, Bonus Card, Bancomer, Ziraat, Santander, CaixaBank, ...). Banks are the main source of complaints.
  - A fashion, apparel, footwear, sportswear, luxury, jewelry, watch or cosmetics brand (Zara, PME Legend, Nike, Adidas, Rolex, ...). Use the generic product ("leather jackets", "luxury watches").
  - A store or commercial market of any kind (supermarket, hypermarket, discount store, DIY/home or furniture store, electronics store, department store, retail chain or online marketplace), in any vertical, even when a live winner names it (Walmart, JYSK, IKEA, XXXLutz, Lidl, Aldi, Carrefour, Leroy Merlin, Castorama, MediaMarkt, El Corte Inglés, Amazon, Temu, ...). Walmart and JYSK have already filed complaints. Use a generic reference ("furniture store clearance", "a DIY store").
  - Feu Vert, or any other service chain (car service, telecom, courier, ...) that no winning title from step 2 already names. Other service chains (Norauto, ATU, ...) may be kept only when they come from a live winner; never introduce a new one, not even to localise.

  Car, electronics and appliance brands (Toyota, iPhone, Samsung, Bosch) and public services (NHS, SUS) are fine. When a winner names a forbidden brand, reuse only its generic subject ("bank-owned houses", "credit card application", "electronics store clearance").
- No emojis, no exclamation marks, no ALL-CAPS words.
- **Production-ready in the target language:**
  - Correct grammar, spelling, diacritics and agreement (case endings, gender, number).
  - A real phrase or sentence, not a string of keywords.
  - Always start with a capital letter. After that, follow the language's own casing: sentence case for most languages (PL, ES, IT, FR, PT, TR, ...), all nouns capitalized in German, and Title Case or sentence case in English, used consistently.
  - Proper nouns capitalized.
  - No trailing full stop, no double spaces.
  - Wrong: `sofa na wyprzedaży`, `tanie sofy wyprzedaz 2026`. Right: `Sofy na wyprzedaży w 2026 roku`.
- Live winning titles are evidence of the subject, not of form. Never copy their casing, typos or missing diacritics.

### 4. Self-check before showing

For every candidate, check:
- `TitleInEnglish` is a faithful translation of that exact `Title` (same values and claims), not a different suggestion.
- `TitleInEnglish` has **at least 3 words** and is **at most about 70 characters**, so it isn't skipped as too long.
- It is not a near-duplicate of another candidate or of a live title you saw in step 2.
- The native `Title` starts with a capital letter, follows the language's casing, and is grammatically correct with full diacritics. Read it as a native copywriter would before it goes on an ad.

Drop or fix failures silently. Don't show broken candidates.

### 5. Present and iterate

Show a numbered table: `#`, native `Title`, `TitleInEnglish`, and a few words on which winner or idea it comes from. Then let the user steer: "more like 3", "drop 5 and 7", "same for DE", "less generic". Keep a running list of **approved** titles across turns, and different countries or verticals can be mixed in it.

### 6. Submit as recommendations (only on explicit approval)

Never call `SetNewArticleTitles` until the user clearly says to submit. Before calling, show the exact list (vertical, country, language, title, English) and the count.

Payload per title:
```json
{ "Vertical": "<exact name from get_verticals>", "CountryCode": "DE", "LanguageCode": "de", "Title": "<native>", "TitleInEnglish": "<english>" }
```

Tool behaviour to know:
- **One invalid row rejects the whole batch.** An unknown country, language or vertical, an empty title, or a duplicate title in the batch returns an error and nothing is inserted. Validate everything first. On an error, fix the row and resubmit.
- The server checks every `TitleInEnglish` against the banned-words list and the length limit, the native `Title` against the list of bank and brand names, and runs a classifier that catches bank, store and fashion-brand names the lists miss. Failing titles are not inserted and are listed after "Skipped" in the reply, each with the reason and how to fix it (the banned word or brand it matched, a bank, store or fashion brand the classifier found, or how much to shorten the English title). Fix each skipped title as its reason says, keeping the rest of the title, show the user the fixed versions, and resubmit them after the user agrees. The server check is the safety net, not the rule: follow the intellectual property rule yourself, because the lists and the classifier don't catch every name.
- Codes and names are trimmed, and codes are uppercased on the server.
- **Reference name:** by default the titles are saved with the reference `agent-expand`. Pass `referenceName` only when the user explicitly asks for a specific name (e.g. "submit them as summer-travel"). Never invent one. Include it in the list you show before submitting.

After submitting, report the inserted count and remind the user briefly how these get used:
- Titles are only turned into articles by the automatic evening expansion, and only when that country × vertical is performing well enough.
- Otherwise they expire after about 1.5 days.
- For a country or vertical with no track record, the user can push them manually from the Title recommendations page in the CK web app.

### 7. Submit for generation (only on explicit request, spends money)

Use `SubmitTitlesForGeneration` only when the user explicitly asks to launch, publish or generate ads for the titles (for example "launch these on Yahoo", "generate ads for 1-5"). Before the first call in a conversation, say plainly that this **creates real articles and ads that will be published and spend budget**, and that the user should only confirm if that is what they want.

Requirements, all from the conversation, never invented:
- **Affiliate for every title** (`AffiliateName`). It is required. If the user did not say which affiliate, ask. Use `get_affiliate_providers` to get the exact names supported by the division; never guess one.
- **Tag** (`tagName`). Recommended: it is written on the created adsets and is how queries, scripts and later AI changes find and group them, so the same tag can follow these adsets from launch through optimization. Suggest one in the form `t:someName` (e.g. `t:summer-travel-de`) that names the idea behind the batch, reuse an existing tag when the batch continues an earlier idea, and use it if the user agrees; it is not required.
- **Budget** (`InitialBudget`, USD per day) and **cost cap** (`CostCap`, USD). Leave both empty unless the user explicitly gives them; empty means the division default budget and no cap. Maximum 20 USD budget and 3 USD cap.
- **Image prompt** (`imagePromptName`). Leave empty unless the user explicitly names a prompt to use.
- **Account** (`AccountName`, per title). Leave it empty unless the user explicitly says which account a title should be published to. **Never pick an account yourself**, not even to spread titles or because one account looks better; empty lets the system choose. When the user names one, match it to the exact name from `get_traffic_accounts`; if it is unclear, ask. Its `Type` must equal the affiliate's `AccountType` from `get_affiliate_providers`; if it doesn't, tell the user and ask which account to use instead of choosing one (the tool rejects a mismatch anyway). It is a preference: if that account is full or not eligible for the country, the system may publish to another account of the same type.
- **Additional review** (`forceAdditionalReview`). Leave it `false`. Set it to `true` only when the user explicitly asks that these titles wait for their manual review before launch.

Depending on the division settings, submitted titles are either sent to generation right away or (partly, e.g. over a daily limit) kept on the **Titles for review** page until the user submits them there. The reply says how many went where. Since you can't know in advance, treat the submit as a launch.

Before calling, show the exact final list (vertical, country, language, title, English, affiliate, budget and cap if set), the account for any title that has one, the tag, and the count, and ask the user to confirm. Call only after a clear yes.

Payload:
```json
{
  "titles": [
    { "Vertical": "<exact name from get_verticals>", "CountryCode": "DE", "LanguageCode": "de", "Title": "<native>", "TitleInEnglish": "<english>", "AffiliateName": "<exact affiliate name>" }
  ],
  "tagName": "t:summer-travel-de"
}
```

Add `"AccountName": "<exact name from get_traffic_accounts>"` to a title only when the user named the account for it.

Tool behaviour to know:
- **All or nothing.** Any invalid title (unknown vertical, country, language, affiliate not in the division, unknown account or account type not matching the affiliate, banned word, duplicate, budget or cap over the limit) rejects the whole batch, and the reply lists every error. Fix those rows and resubmit the whole batch. Unlike `SetNewArticleTitles`, banned-word titles are not skipped; they fail the batch.
- On success, tell the user how many titles were submitted for generation, how many wait for review (if any), and the tag, if any. Submitted titles are then turned into articles and ads automatically.

### 8. Create a theme (only on explicit request)

`create_theme` adds a new theme under a top-level vertical. Call it only when the user explicitly asks to create a theme, and only after they confirm the exact vertical, name and description. Never create one on your own initiative, not even when no existing vertical fits a title. In that case, suggest a theme and let the user decide.

The theme name ends up everywhere: titles, articles, adsets and the stats all carry it as the vertical name. So:
- **Vertical**: the exact name of a **top-level** vertical (`get_verticals` with `topLevelOnly: true`). A theme cannot be the parent; the tool rejects it. If the user names a theme, tell them which top-level vertical it belongs to and ask whether the new theme should go there. The theme must stay inside that vertical's scope. If the topic doesn't belong to any vertical, recommend a new vertical for the user to add by hand instead of forcing a theme under an unrelated one.
- **Name**: PascalCase, letters and digits only, starting with an uppercase letter, no spaces, at most 60 characters, for example `SeasonalTireTypes` or `MensFashionOver60`. Follow the style of the existing names. It must be unique across **all** verticals and themes of the division, ignoring case. If `Sale` exists as a vertical, no theme can be called `Sale` or `sale`. Check `get_verticals` first; the tool also rejects a name that is taken.
- **Description**: one or two concrete sentences on what the theme covers. Several things read it:
  - the AI that writes and rephrases titles for the theme, where it sets the topic boundary;
  - the AI that suggests new themes, which uses it to avoid overlap;
  - ad image generation.

  Say what is in scope and how the theme differs from its vertical and its sibling themes. Follow the existing descriptions, for example "Offers for tires categorized by seasonal suitability such as summer, winter, all-season, and rain tires." Avoid vague ones like "offers about tires".

Before creating, call `get_verticals` with `vertical: "<parent>"` to see the existing themes. If one already covers the topic, point the user to it instead. Then show the vertical, name and description, and call `create_theme` only after a clear yes.

The tool returns an error that says what to fix: an invalid name, a name already taken, an unknown vertical, a parent that is a theme, or an empty description. On success, the new theme can be used right away as the `Vertical` for titles. Write a `Journal` entry with the theme, its vertical and its description.

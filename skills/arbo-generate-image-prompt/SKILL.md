---
name: arbo-generate-image-prompt
description: Design a new base prompt for CK's AI ad-image generation (the template that turns an article headline and description into a Facebook image ad), from the user's description of the desired look and/or reference images. Produces a Facebook-compliant, CTR-oriented, placeholder-correct prompt with a short camelCase name, a description and variations. Use when the user asks to create, design, rework, review or vary an image prompt, image template, base prompt, ad image style or creative style, or sends reference ad images and wants a prompt that makes images like them. Also use when the user wants a test prompt (an existing base prompt filled with a given title for manual testing), or wants to list, read, submit or edit saved image prompts through the CK MCP (list_image_prompts, get_image_prompt, save_image_prompt).
---

# Image prompt generator

You help the user design a **base image prompt**: a reusable template that CK fills in for every ad and sends to an image model (GPT Image family) to produce one Facebook/Instagram feed image ad.

The user describes the look they want, sends one or more reference images, or both. You turn that into a prompt that follows the fixed structure below, keeps every mandatory rule, and stays clean and consistent so the model produces good, compliant images.

This skill is self-contained. It works in the Claude web or desktop app and in Claude Code, and it needs no project source code. Everything comes from these instructions and the CK MCP tools. Don't look for local files.

The MCP tool prefix differs per person; refer to tools by their function name (`list_image_prompts`, `get_image_prompt`, `save_image_prompt`). The MCP connection already determines the division. Never work across divisions.

## The business, in short (why the rules exist)

- We run ads on Facebook/Instagram that lead to **informational articles** (RSOC: Related Search on Content). We earn when a reader clicks a related-search term on the article page.
- **We do not sell, book, provide or recommend anything.** The article might be about car sales, jobs, dental implants, cruises, volunteering, anything. The ad only makes the article's topic attractive enough to click.
- So every image must: make the topic instantly clear, make people curious enough to click, and never look like an offer, a store, a service provider or a brand's ad.
- Facebook penalises policy-borderline and low-quality creatives in two ways: **rejection/account risk** and **worse delivery** (lower quality ranking, higher CPM). A good prompt avoids both.

## How the prompt is used

CK replaces the placeholders with plain text for each ad, then sends the full text to the image model. There's no other system prompt. What you write **is** the whole instruction the model gets, so every sentence counts.

### Placeholders

Write them exactly like this, case-sensitive, with double curly braces:

| Placeholder | Filled with | Required |
|---|---|---|
| `{{PRIMARY_TEXT}}` | The ad headline, in the target language. The only big text in the image. | **Yes** |
| `{{LanguageName}}` | The language name in English (e.g. `German`). | **Yes** |
| `{{Anchor}}` | The article's topic or keyword phrase (may be in the target language). Used to understand the subject. | **Yes** |
| `{{article_description}}` | A 2–3 sentence neutral summary of the article, in the target language. | **Yes** |
| `{{Strategy}}` | Free-text creative direction for the campaign, written by a media buyer. | **Yes** |
| `{{CountryName}}` | The first target country's English name. | Optional |
| `{{Countries}}` | A comma-separated list of target countries. | Optional |

Facts about the values that the prompt must survive:
- `{{Strategy}}`, `{{article_description}}` and `{{Anchor}}` **can be empty**. The prompt must still read correctly when they are, so never write a sentence whose meaning depends on them being present (for example "Follow the strategy above exactly").
- `{{Strategy}}` is written by people and can conflict with the prompt. The prompt must always state that its own rules take priority, and that the strategy only gives topic-specific visual guidance.
- `{{Anchor}}` may contain search-keyword phrasing ("best suv lease deals 2026"). It must **never be rendered as visible text** unless the same words appear in the headline or description.
- Never invent other placeholders. Nothing else gets replaced, and an unknown `{{Something}}` would reach the model literally.
- Write the prompt itself in **English**. Only the rendered text is in `{{LanguageName}}`.
- Never state an aspect ratio, size, dimensions or orientation (no `1:1`, "square", "vertical poster"). CK sends the size to the image model separately, and the same prompt is used for square and portrait images.

## One prompt, every topic (hard rule)

A base prompt is a **template reused for literally every title**. The same text renders "Used SUVs in Germany", "Warehouse jobs near you", "Dental implants cost", "Volunteering abroad" and anything else. You never know the topic when writing the prompt, and the prompt must never assume one.

- **Never hardcode an actor or subject.** No specific person type (a woman, an older man, a nurse, a family), profession, age, gender, ethnicity, object, product, vehicle, animal, place, season or scene. Refer to **roles** only: "the topic's main subject", "a person relevant to the topic, when one fits naturally", "an object or scene that represents the topic".
- **Everything subject-specific comes from the placeholders.** The model decides what to show from `{{PRIMARY_TEXT}}`, `{{Anchor}}` and `{{article_description}}`. The prompt decides how it looks: layout, style, hierarchy, palette logic.
- **People are optional, never required.** Many topics have no natural person. Write "when a person fits the topic" instead of "show a person".
- **References are the main trap.** A reference showing a smiling woman next to a red car must become "a cleanly cut-out hero subject relevant to the topic", not "a woman next to a car". Keep the treatment (cut-out, framing, lighting, expression energy) and drop the identity of the subject.
- **Vertical-oriented styles are still generic.** Even when a prompt is meant mainly for one vertical (e.g. `saleV1`), don't write the vertical into it. Targeting prompts to verticals is done later with filters in CK, not with prompt text. Style elements that only suit some topics must be conditional ("if the description lists several items, ...").
- **Structural elements must degrade gracefully.** Rows, tiles, chips and numbers only appear when the sources support them. The prompt says what to do when they don't.

## The DNK: required prompt structure

Every prompt has these sections, in this order. Use uppercase section headings as plain lines, and bullets for rules. You may rename a heading, merge two small sections, or add a design section (for example `COMPOSITION`, `VISUAL STYLE`, `TYPOGRAPHY`), but no part may be missing.

1. **Opening line.** One sentence stating the output: a polished standalone social media advertisement, the ad's character in a few words (e.g. "an informational editorial ad that leads to an article, optimized for click-through rate in a mobile feed").
2. **HEADLINE.** Quote `"{{PRIMARY_TEXT}}"`. Require every headline word to be rendered exactly once in `{{LanguageName}}`, preserving spelling, accents, punctuation, capitalization, wording and word order, with nothing added, omitted, translated, paraphrased or repeated.
3. **CONTEXT.** Present `{{Anchor}}` as the informational topic and `{{article_description}}` as the article description. Say they are for understanding the topic, audience and visual subject, and that the image must make the topic immediately clear **without pretending to sell or provide it**.
4. **BRANDS (STRICT).** The mandatory brand block from "Mandatory compliance rules", word for word, placed right after CONTEXT so the model reads it before any design instruction. Never move it to the end or merge it into COMPLIANCE.
5. **TEXT / SOURCE RULES.**
   - Any supporting text, number, price, percentage, date or figure must come from the headline or the description, exactly as written there.
   - Supporting text is short and visually secondary. No paragraphs, no full description.
   - Don't invent claims, numbers, categories, benefits or comparison results.
   - Don't render the anchor as text unless the same words appear in the headline or description.
   - No random letters, placeholder copy, malformed words, URLs, domains, phone numbers or fine print.
   - If the design uses generic words that aren't in the sources (like "Search" or "Compare"), whitelist them here explicitly, localized to `{{LanguageName}}`, and state that they must not be expanded into claims or offers.
6. **CREATIVE DIRECTION.** `{{Strategy}}` on its own line, followed by the priority sentence: this prompt's format and rules take priority over any conflicting direction, and the strategy is only topic-specific visual guidance.
7. **Design sections.** This is where the user's look lives: composition, headline treatment, hero subject, supporting modules, palette, typography, lighting, depth, spacing. See "Translating a look into a prompt".
8. **READABILITY.** The headline must be bold and readable at small mobile-feed size, with strong contrast around every letter, protected from busy imagery (negative space, a solid panel, a strong gradient or an opaque shape), safe margins, and no reliance on weak shadows. Apply the same to any secondary text.
9. **COMPLIANCE** (mandatory, see below).

No closing line. The prompt goes to an image model, which only returns an image, so lines like "Return only the finished advertisement" just waste space.

## Be concise

There's no length target. A simple design gets a short prompt, and a complex design (a comparison module, several zones) takes the space it needs to be described precisely. What matters is that every sentence carries an instruction the model needs. Write to preserve space:
- One sentence or bullet per rule. State the rule without explaining why.
- Examples in lists: at most three, then "or similar".
- Don't restate a rule in another section. Cross-cut rules (contrast, no invented text) live in one place.
- No filler adjectives or style chatter ("polished, stunning, eye-catching, premium"). One precise word beats three vague ones.
- Merge small sections when that reads better (e.g. readability into the headline section).
- Describe the design once, in its own section, instead of repeating layout hints across sections.
- Don't over-explain the obvious (that text must be spelled correctly, that the image should look good).
- Cutting words must never drop a mandatory rule or a placeholder.

The only hard limit is technical: GPT Image models accept prompts up to about 32,000 characters, and that includes the filled-in headline, description and strategy. A well-written prompt never comes close to it. If one does, the design is over-specified.

## Mandatory compliance rules (always in the prompt)

These are the rules the compliance section must cover. The explanation below is for you.

### Brand block (mandatory, word for word, right after CONTEXT)

Headlines often name a brand, store or manufacturer ("Goodyear Tires on Clearance at Walmart"). The headline must be rendered exactly, so a bare "no brand names" rule contradicts it, and the model then treats the whole brand rule as optional and draws the store's logo, signage and colours. This block resolves that: the name is allowed only as plain headline text, and everything else about the brand is replaced with a generic equivalent. Copy it unchanged into every prompt and every variation:

```
BRANDS (STRICT)
- The headline, topic or description may name a company, store, retailer, manufacturer or product brand. Such a name may appear only as the plain headline words, set in this ad's own typography and colours. It must never appear anywhere else, and never as a logo, wordmark, emblem or in the brand's own lettering style.
- Never draw any real brand's logo, symbol, wordmark, mascot, storefront sign, store facade branding, branded shopping bag, uniform, packaging, price tag or product label, even when the brand is named.
- Show a named store or place as a generic, unbranded building or interior with blank signage. Show a named product as a generic unbranded equivalent with no name, logo, badge or lettering on it (for example tires with plain sidewalls, cars without maker badges or identifying grilles, devices without logos).
- Do not use a named brand's signature colours or trade dress in the scene or the palette. If they match this prompt's palette, shift the accent colours away from them.
- Supporting text, labels, tags and icons never contain or depict a brand name or brand symbol.
```

### Compliance block

In the prompt, write the remaining rules compactly. The default block below covers all of them compactly; use it as-is or adapt it to the design, but never weaken it:

```
COMPLIANCE
- This is an informational ad for an article. Do not imply that the advertiser sells, books, provides, guarantees or recommends anything.
- No call-to-action wording (such as buy, book, sign up, apply, call, learn more) and no buttons or clickable-looking controls.
- No logos, trademarks, brand colour schemes, watermarks, seals, badges, official emblems or platform interfaces. Brand names only as described in BRANDS.
- No unsupported prices, discounts, "free", rankings, guarantees, endorsements, before/after comparisons, urgency or scarcity.
- It must not look like a website, app, listing, search results page, notification or social post, or imply live inventory.
- No callouts of personal attributes (age, health, body, finances, religion, ethnicity, sexuality). No shocking, medical, sexual, violent or money-pile imagery. No real, identifiable people.
```

When the design has an allowed control-like motif (a search tag, "Compare" chips), extend the second bullet with ", except the <motif> described above, which is a label, not a control".

What each rule covers:

**No selling, no provider framing**
- The advertiser does not sell, book or provide any product or service. The image only leads to an informational article.
- Don't imply that the advertiser sells, books, guarantees, recommends or directly provides the article's subject.

**No calls to action**
- No CTA text or wording: "buy", "order", "book now", "shop", "sign up", "register", "apply", "get a quote", "call", "contact", "download", "learn more", "click here", or equivalents, even when the topic is about such a service.
- No CTA buttons, button-shaped elements, clickable-looking controls, input fields, cursors, fake play buttons, sliders or checkboxes. If the design uses an allowed informational motif (a search tag, "Compare" chips), name it as the **only** exception and say it isn't a real control.

**No brands** (enforced by the brand block; the compliance line only points to it)
- No logos, trademarks, brand marks, wordmarks, mascots or branded products with visible branding, even when the headline, anchor or description names a brand. A brand named in the headline appears only as plain headline text.
- No branded places: stores, restaurants, dealerships or venues are generic, with blank signage.
- No brand-identifying colour schemes or trade dress (e.g. a bank's or retailer's signature colours used as the ad's palette). Use a generic, unbranded palette.
- No watermarks, certification seals, award badges, official or government emblems, or platform branding (no Facebook/Instagram UI, notifications or like buttons).

**No unsupported commercial claims**
- No unsupported discounts, savings, prices, "free", rankings ("#1", "best"), endorsements, guarantees, before/after comparisons, or checkmarks implying certainty.
- No urgency or scarcity: countdowns, "limited", "today only", "last chance", stock counters.

**No fake interfaces or inventory**
- It must not look like a website, app screen, browser, marketplace listing, search results page, dashboard, chat, phone notification or social post. It is a standalone advertisement.
- Don't imply live listings, available inventory or real-time prices.

**Facebook people and content policy**
- No text or visuals that call out or imply a viewer's personal attributes (age, health condition, body, finances, religion, ethnicity, sexuality, disability), such as "Are you over 50?" or a person pointing at the viewer about their debt.
- No body-shaming, no zoomed-in body parts, no before/after bodies, no medical close-ups, needles, blood, injuries or other shocking, scary or disgusting imagery.
- No sexualised or suggestive poses or clothing, no weapons, violence, drugs, tobacco or alcohol focus.
- No money piles, cash fans or "rich lifestyle" imagery implying income or financial gain.
- No depictions of real, identifiable people (celebrities, politicians). People must be generic and fictional.

You may leave out a rule only when the user explicitly asks, and you must warn them of the policy risk when they do.

## Translating a look into a prompt

### From a description
Pin down, asking only about what's missing and genuinely changes the result:
- **Ad archetype**: editorial magazine ad, bold poster, infographic or comparison, clean product-category shot with a headline, illustrated or flat design, photographic lifestyle scene, minimal typographic.
- **Layout**: where the headline sits, the hero subject, any supporting module (a list, 2×2 tiles, chips, a footer band).
- **Visual language**: palette logic (for example "pale neutral background with one or two strong accent colours"), typography style (condensed, extra-bold sans, serif editorial), photo or illustration or 3D, lighting, depth.
- **Density**: how much supporting text and how many elements.

Defaults if the user doesn't specify: one hero subject, the headline in the top half, low density.

The layout must work at any aspect ratio (square and portrait): describe positions relative to the canvas (top half, left side, centered), never fixed grids that only fit one shape.

### From reference images
- Describe what you see in design terms: grid, headline position and size ratio, subject treatment (cut-out, full-bleed photo, illustration), palette logic, typography class, recurring motifs, density.
- Extract the **design logic**, never the content. Don't copy brand names, logos, product designs, trademarked characters, real people's faces, or the reference's text.
- Palettes become generic descriptions ("warm coral accent on off-white"), never "the brand's colours".
- Call out anything in the references that breaks the rules above (CTA buttons, prices not from the source, logos, fake UI, "limited offer" badges, personal-attribute callouts). Tell the user you're leaving it out, or replacing it with a compliant equivalent.
- With several references, find the common denominator. Ask when they disagree in a way that matters.

### Writing the design sections
- Describe **the look**, not a specific image or subject (see "One prompt, every topic"). "A cleanly cut-out hero subject relevant to the topic" is good; "a red SUV" or "a smiling young woman" is not.
- Make every structural element **conditional on the sources**. For example: "If the description doesn't provide enough items for multiple entries, use fewer entries or visual-only tiles. Never fabricate content to fill the layout."
- Be concrete about hierarchy: headline first, then hero, then secondary module.
- Say what to avoid for this style (generic stock-photo look, cluttered collage, dense flyer, presentation slide).

## Quality and performance review (always do this before showing)

A bad prompt costs money: confused images get low CTR, and borderline ones get lower quality rankings and higher CPM. Check the draft against this list, and fix it silently:

1. **No contradictions.** E.g. "only text is the headline" together with "add a short supporting line"; "minimal, lots of negative space" together with "information-rich with five rows"; "no control-like elements" together with a required search tag without an explicit exception; "no prices" together with "you may show prices from the description". Every allowed exception must be stated once, clearly, in the rule it overrides.
2. **No duplicates.** Say each rule once, in its section. Repeating it in different words makes it look more important than it is and wastes the model's attention.
3. **Nothing forced.** No "always include X" for elements that only make sense for some topics (people, prices, icons). Use "when it fits the topic" instead.
4. **Empty-placeholder safe.** Mentally fill the prompt with an empty `{{Strategy}}` and `{{article_description}}`. It must still make sense.
5. **Topic-agnostic.** Mentally run it for five unrelated topics, e.g. "used cars", "warehouse jobs", "dental implants", "river cruises", "volunteering with animals". Every instruction must still make sense, and no hardcoded actor, object or scene may remain (see "One prompt, every topic").
6. **Text load.** Big text is the headline only. Secondary text is short, optional and source-bound. More text in the image means lower delivery and more rendering errors.
7. **Placeholders.** All required placeholders are present, spelled exactly, with no unknown ones.
8. **Compliance complete.** Every block from "Mandatory compliance rules" is present, and the BRANDS (STRICT) block is right after CONTEXT, word for word. Mentally run the prompt with a headline that names a retailer and a product brand (e.g. "Goodyear Tires on Clearance at Walmart"): nothing in the design sections may invite a storefront, sign, product label or brand colours.
9. **Tight writing.** Every sentence carries a needed instruction (see "Be concise"). Cut explanations, repeated rules and filler adjectives, not design detail the look depends on.
10. **Plain instructions.** Direct, imperative, unambiguous English. No hype words ("stunning", "viral", "insane CTR"), no emojis, no markdown tables inside the prompt, and no talking to the user inside the prompt.

## Variations

A variation is the **same prompt with the same structure, rules and design logic**, varied only in design parameters to add randomness across ads:
- the palette or accent colour family
- headline placement (top, or left-aligned over negative space) within what the design allows
- hero framing (cut-out, close crop, environmental)
- the accent motif (ribbons, panels, dividers, arrows)
- the background treatment (flat pale, soft gradient, subtle texture)

Rules for variations:
- The placeholders, text rules, priority sentence, BRANDS block, readability and compliance sections are **identical**, word for word, in every variation.
- A variation must never add an element that needs a new exception (a new control, new allowed words).
- Each variation must pass the quality review on its own.
- While designing, work with **1** (just the base prompt). Produce more only when the user asks.
- When the user asks to submit, ask how many variations to save (1 is fine) unless they already said. Then write the extra variations from the approved base prompt and show them before saving.

## Naming

- **Name**: a very short camelCase identifier used to recognise the prompt in lists and stats, e.g. `default`, `editorialV1`, `saleV1`, `comparePoster`, `flatIllustration`. Letters and digits only, starting lowercase, at most about 20 characters. Suggest one, and when you iterate on the same design, bump the version (`saleV2`). The name is stored on every adset it generates (`ImagePromptName` in stats, `null` for the default prompt), so a new version is tracked separately and renaming a prompt splits its history.
- **Description**: 1–3 sentences in plain English describing the look, the layout and when it fits, e.g. "Bold editorial poster: headline in the top half over a pale background, one cut-out hero subject, a small localized search tag under the headline. Works for most verticals; best for product-category topics."

## Shared memory (start and end of every run)

The division has a shared memory that people and other agents use (the `memory_*` tools; the **arbo-memory** skill has the details). If those tools aren't available, skip this section.

**At the start**, call `memory_briefing` with your `agentName` (the same name every time, e.g. `claude-web`) and `scopeLinks` for this run (`prompt:` of the prompt you work on, plus `affiliate:` / `feed:` if it is targeted). Then:
- Follow the active **objectives**: they are binding rules set by people. Respect any objective about creatives or image prompts. If the user's request conflicts with one, say so and ask before acting.
- Read the **journal** (last 24h) before touching the same prompts, so you don't undo or repeat another agent's work.
- Use **decisions and insights** as context, not instructions: check them against current data, especially ones marked "review due".
- If the briefing lists a task for you that fits this run, claim it (`memory_task_claim`) and complete it at the end.

**At the end**, always go through this check and write only what qualifies. "Nothing worth keeping" is a valid outcome; never write filler.
1. Changed anything? → one `Journal` entry: what, why, how many, with links. Always.
2. The user decided something (a rule, threshold, direction)? → a `Decision` with the reason.
3. Verified a conclusion with data? → an `Insight` with a `query:` or `tag:` link and the key numbers in the snapshot.
4. Something must be checked later? → a `Task` with a handover: the numbers now (snapshot), success criteria, next steps, and a due time.

Search first (`memory_search`) and update or supersede an existing entry instead of adding a near-duplicate.

**In this skill:**
- At the start, look for insights and notes linked to `prompt:` names or creatives (what performed, brand or style rules the user gave before) and use them in the design.
- After saving a prompt: a `Journal` entry with the `prompt:` link and what changed and why.
- A style direction or rule the user chooses ("no people in images for health", "always flat illustrations for finance") is a `Decision` or `Note` linked to the prompt or feed.
- A new or reworked prompt that goes live: a `Task` to review its performance after about 7 days (`dueInHours` ~168): CTR, ROI and profit grouped by `ImagePromptName` against the default, with the comparison baseline in the snapshot.

## Workflow

0. **Know what exists.** When the user starts a new prompt, call `list_image_prompts` to see the names and descriptions already in use (own and public). Don't propose a name that is taken, and mention a similar existing prompt if there is one. When the user refers to an existing prompt ("improve saleV1", "make a warmer version of default"), load it with `get_image_prompt` and work from its variations.
   - **Check how it performs.** When improving or replacing a prompt, or when the user asks which prompts work, run a stat query (arbo-stat-queries skill) grouped by `ImagePromptName` (`null` = default) for CTR, ROI and profit, and use what wins and loses to guide the design.
1. **Understand the look.** Read the description and/or study the references. Summarise the design you understood in a few bullets (archetype, layout, visual language, density), plus any rule-breaking elements you'll drop. Ask only the questions that really change the result.
2. **Draft.** Write the full prompt following the DNK, the compliance rules and the design sections.
3. **Review.** Run the quality and performance review and fix everything silently.
4. **Present**, in this order:
   - `Name` and `Description`
   - the full prompt in a single fenced code block, with no commentary inside it
   - variations, if requested, each in its own code block labelled `Variation 2`, `Variation 3`, and so on (the base prompt is Variation 1)
   - a few bullets on the key design decisions and anything from the references you deliberately left out for compliance
5. **Iterate.** Take feedback ("less text", "headline bigger", "add a comparison module", "make it warmer") and re-run the review on each revision. Always show the full updated prompt, never a diff.

## Test prompts

The user may ask for a **test prompt** to try the base prompt in an image generator by hand. They give a title (the headline) and possibly a description, anchor, language or strategy.

- Take the **exact current base prompt** (or the variation they name). For a saved prompt, load it with `get_image_prompt` first, so the test uses what is really stored, and replace the placeholders. Nothing else changes: no wording, no sections, no hints, no rules added or removed, no adaptation to the test topic. The point of a test is to see how the real template behaves on real inputs, and any tailoring would hide that.
- Fill placeholders the way CK does:
  - `{{PRIMARY_TEXT}}`: the title, verbatim.
  - `{{article_description}}`, `{{Anchor}}`, `{{Strategy}}`, `{{CountryName}}`, `{{Countries}}`: the given value verbatim, or an **empty string** if not given. Don't invent a description, and don't fall back to the title for the anchor.
  - `{{LanguageName}}`: the given language, or the English name of the title's language (e.g. `German`).
- Don't translate, correct or rephrase supplied values, even when they have typos.
- Output the filled prompt in a single code block, ready to paste. Above it, list only the values you used for each placeholder.
- If the resulting image reveals a problem, fix the **base prompt** (then re-run the review), and produce the test again from the new base. Never patch only the test copy.

## Saved prompts (CK MCP)

- `list_image_prompts(nameContains?)`: id, name, description of the division's own prompts and public prompts of other divisions. `IsOwn` says which ones this division can change.
- `get_image_prompt(promptId)`: one prompt with all its variations, plus its state (enabled, auto rotation, public) set by people in CK.
- `save_image_prompt(name, description, variations, promptId?)`: creates a prompt (no `promptId`) or replaces name, description and variations of an own prompt (with `promptId`). `variations` is the complete list of full prompt texts: on edit, send all of them, including unchanged ones, because the list is replaced as a whole.

### Submit (only on explicit approval)

Never call `save_image_prompt` until the user clearly says to submit or save.
1. Ask how many variations to save, if not said yet (see "Variations").
2. Run the quality review on every variation.
3. Show exactly what will be saved: name, description, every variation in its own code block, and whether it's a new prompt or an edit of an existing one (with its name).
4. Call `save_image_prompt`. Pass arrays as real JSON arrays, not as a JSON string.

Tool behaviour to know:
- Everything is validated on the server first: camelCase name unique in the division, a description, at least one variation, every required placeholder in every variation, no unknown `{{...}}` placeholders. On any error **nothing is saved** and `Errors` lists the problems. Fix them and call again.
- **New prompts are saved disabled, private and out of auto rotation.** Tell the user to open CK (Generated ads → Generators configuration) to test it, enable it, put it in rotation, share it or add affiliate/feed filters. The tool never changes those settings.
- **Editing an own prompt** replaces name, description and variations only. If the reply says the prompt is enabled and in auto rotation, tell the user that new ads use the change right away.
- **Public prompts of other divisions are read-only.** To build on one, save it as a new prompt of this division (no `promptId`) with a new name, and say that it's a copy.

### Editing an existing prompt

1. `get_image_prompt` to load the current variations, never edit from memory.
2. Apply the user's change to every variation where it belongs, keeping the shared sections identical across variations.
3. Run the review, show the full updated variations, and submit as above with the same `promptId`.

## Finishing

When the user says the prompt is final, show the final `Name`, `Description` and prompt(s) together, then offer to submit it (see "Submit").

## Reference: an existing base prompt (for structure, not to copy)

This is the current production default (`default`), lightly condensed. It shows the DNK and tone: an editorial ad with an optional search-tag motif. New prompts should reach this level of rigour, but with their own design sections, and be written tighter: this one repeats itself in places (for example the search label is explained in three sections).

```
Create a polished standalone social media advertisement, designed as an informational editorial ad that leads to an article, optimized for click-through rate in a mobile feed.

HEADLINE TEXT
The main headline is:
"{{PRIMARY_TEXT}}"

Render every headline word exactly once in {{LanguageName}}. Preserve its spelling, accents, punctuation, capitalization, wording, and word order. Do not add, omit, translate, paraphrase, or repeat headline words.

CONTEXT
The image promotes the informational topic "{{Anchor}}".
Article description: "{{article_description}}"

Use the anchor and description to understand the topic, the audience, and what would make someone click. The finished image should make the article topic immediately understandable without pretending to sell or provide the product or service. Any visual element suggested by them may appear in the image: objects, scenes, people, settings, emotions, icons, symbols, or short snippets of text taken from the description. Use such elements only when they fit the topic and make logical sense. Never force them in just to fill space.

SOURCE RULE
Any text, number, price, percentage, or figure shown in the image must come from the headline and/or the article description, spelled and stated exactly as written there. Any supporting text must be short and visually secondary to the headline. Do not invent text, numbers, or claims that neither source supports. Icons, symbols, and illustrative objects are not limited to the source, but they must be relevant to the topic and must not imply claims the article does not make.
The generic search label phrases listed in the SEARCH LABEL section are allowed even when absent from the sources. Render the chosen phrase naturally in {{LanguageName}}. It must remain a generic informational cue and must not be expanded into a query, promise, offer, or sales claim.

CREATIVE DIRECTION
{{Strategy}}

The required search label and the informational rules in this prompt take priority over any conflicting direction above. Use the strategy for topic-specific visual guidance, not to remove the search label or weaken the text rules.

READABILITY
- Make the complete headline bold and immediately readable at small mobile-feed size.
- Prefer extra-bold modern display typography with compact, balanced line breaks and generous safe margins.
- Protect it from the background with negative space, a strong gradient, a solid panel, or an opaque shape.
- Maintain strong contrast around every letter. Do not rely on a weak shadow over bright imagery or allow subjects, patterns, or effects to obscure text.
- The same readability and contrast rules apply to the search label.

OPTIONAL TYPOGRAPHIC HIERARCHY
- When the headline has a naturally important phrase, you may emphasize it with size, weight, or an accent color.
- You may split the headline into meaningful visual groups when this improves hierarchy. Every headline word must still appear exactly once and in its original order.
- Do not force awkward splitting or arbitrary emphasis. Otherwise, use one cohesive text block.

VISUAL DIRECTION
- Aim for a designed advertisement rather than a plain photograph with a caption.
- Use one compelling visual subject that supports the promoted topic.
- When helpful, add relevant accent shapes, panels, ribbons, frames, dividers, arrows, or simple icons.
- Do not force decoration merely to make the image busier. Prefer a simpler composition when extra elements would be arbitrary or distracting.
- Use a cohesive advertising palette, polished lighting, depth, and crisp separation. Avoid generic stock-photo layouts, dense flyers, dashboards, website screenshots, and cluttered collages.

SEARCH LABEL (REQUIRED)
- Every image must include exactly one search label: a magnifying-glass icon followed by one short generic search phrase in {{LanguageName}}, placed inside a small solid rounded tag. Plan it as part of the layout from the start.
- Possible phrases: "Search", "Search topics", "Related searches". Pick one at random, weighing what fits the topic and layout. Translate it into {{LanguageName}} using its natural equivalent. If it becomes too long for a compact tag, use "Search".
- Attach it to the headline block, directly above or below the headline and aligned with it. Do not place it against the image edge, over detailed imagery, or in a separate footer strip.
- Make it compact but clearly readable: its text about one third to one half of the headline's letter height, bold or semi-bold, with the icon as tall as the text.
- Give it strong contrast: a fully opaque tag in the ad's accent color, white, or a dark tone. Never thin, faded, semi-transparent, outline-only, or blended into the background.
- It is a label, not a search field or control: no input box, placeholder, cursor, arrow, query, article topic, URL, domain name, brand, price, offer, or any wording besides the chosen phrase.

LOGOS AND BRANDING
- Never use any logo, trademark, brand mark, or branded visual identity of any company or product, including any mentioned in the description. Use generic, unbranded equivalents instead.

INFORMATIONAL COMPLIANCE
- The advertiser does not sell, book, or provide any product or service. The image only leads to an informational article.
- Do not imply that the advertiser sells, books, guarantees, recommends, or directly provides the subject of the article.
- Do not add unsupported discounts, savings, rankings, endorsements, guarantees, or urgency.
- Do not include any call-to-action button, button-shaped element, or clickable-looking control, other than the required search label described above.
- Do not include any call-to-action text or wording, such as "book now", "buy", "order", "sign up", "get a quote", "call", "learn more", or anything similar, even if the article topic is about such a service.
```

The search label is a design choice of this prompt, not a requirement. Note what the reference lacks, which new prompts should add: the BRANDS (STRICT) block right after CONTEXT (its one-line LOGOS AND BRANDING rule at the end is too weak and does let logos through when the headline names a brand), the Facebook people and content policy block, the fake-interface rule, and safe handling of an empty strategy.

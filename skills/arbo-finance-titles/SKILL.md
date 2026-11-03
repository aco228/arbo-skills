---
name: arbo-finance-titles
description: Write compliant loan, credit and other finance article/ad titles that keep the structure and reason to click of past finance winners (JP blacklist and no-screening loans, PL consolidation, TR credit cards, NL and FR small loans), while following Meta's financial services and personal attributes policies and the house title rules. Submits them as title recommendations (SetNewArticleTitles) in the Finance vertical. Use when the user asks for finance, loan, credit, credit card, debt or borrowing titles, asks to rewrite a finance winner so it is compliant, or asks whether a finance title is allowed.
---

# Finance titles

Loans, credit, credit cards, borrowing, debt consolidation and pay later are allowed again (ban lifted 2026-11-03). They publish under the Facebook financial special category, which the server sets on its own. What makes a finance title safe is **how** it talks about the topic, not the topic itself.

This skill adds finance rules on top of **arbo-title-creator**. Every rule of that skill still applies (neutral third-party voice, no store or bank names, production-ready language, self-check, submission). Read it too when it is first used in a conversation.

## Meta policy (read 2026-11-03)

From Meta's Advertising Standards, *Financial and insurance products and services* and *Privacy violations and personal attributes*:

- **Prohibited products, whatever the wording:** payday loans, salary advances, bail bonds, short-term loans repaid within 90 days or less, binary options, CFDs, ICOs, penny auctions. Misleading claims about student loan consolidation, forgiveness or refinancing are also prohibited.
- **Allowed:** credit cards, loans longer than 90 days, mortgages, insurance, as long as the ad targets 18+ (done by the special category) and doesn't ask for personal or financial data.
- **Exempt from licensing:** news articles that don't offer credit, education on applying for or managing loans, and ads that mention a product without letting the user get it. **Our titles must stay in this space**: an independent article that explains, compares or answers a question. Never an offer.
- **Personal attributes:** an ad may not assert or imply the viewer's financial status ("vulnerable financial status"), or that it knows their financial information. Meta's own rejected example: "Are you bankrupt? Check out our services." "you/your" is fine only when it isn't tied to a personal attribute.

## Finance title rules

1. **No offer details:** no amount ("€250", "PLN 200", "up to 2000 euros"), no term or duration ("6 months", "30 days"), no rate, no fee claim ("no fees", "0%").
2. **No approval or availability promises:** not "available", "approved", "guaranteed", "instant", "same-day approval", "for everyone", "whatever your score", "regardless of credit".
3. **No reader financial status:** never address or label the reader by their money situation: "for those on the blacklist", "your credit score", "if you have debt", "bad credit? ...". Describe the situation as a topic instead: "Loans with a blacklist record: how they work", "Loan types with a low credit score".
4. **No prohibited products:** never payday loans, salary advances, "chwilówki", "mini-prêt", 30-day loans, or any loan framed as very short-term. Move the subject to the allowed product next to it: instalment loans, personal loans, card loans, consolidation, credit cards.
5. **No names** of banks, lenders, card issuers, card programmes, BNPL companies (Klarna), credit bureaus (BKR, Schufa, BIK, KKB, CIC/JICC) or government finance bodies. Use the generic thing: "credit registration", "credit record", "credit card application".
6. **Informational frame:** "how it works", "what to know", "criteria", "steps", "conditions", "how to compare", or an honest question ("Do no-screening loans really exist?"). No "apply now", "get", "buy".
7. **No seller voice:** no "we", "our", no instalment or pay-later offers attached to a product ("iPhone in 24 easy payments"). Explaining how instalments or flexible payment plans work in general is fine.
8. **Japan:** licensed lenders must screen every applicant, so "loan without screening" can't be stated as a fact. Ask it as a question or explain how screening really works.

## Keep the structure of the winner

Keep the subject, the angle and the shape (colon pattern, year, length) of the winner. Only the forbidden part changes:

| Winner | Problem | Compliant version |
|---|---|---|
| ブラックリスト利用者向け：2027年版少額融資 (For those on the blacklist: small loans, 2027) | addresses reader's status | ブラックリスト掲載中の少額融資：2026年版の仕組みと注意点 |
| 審査なし融資申し込み (Loan application without credit check) | implies no screening | 審査なし融資は本当にある？2026年の仕組みと注意点 |
| Szybkie chwilówki internetowe od 200 zł bez zbędnych papierów | payday + amount + promise | Pożyczki ratalne online w 2026 roku: jak działają i jakie dokumenty są potrzebne |
| Kredi notunuz kaç olursa olsun kredi seçenekleri (Credit options whatever your score) | "your" + approval promise | Düşük kredi notuyla değerlendirilebilecek kredi türleri: 2026 rehberi |
| Ziraat Bankası kredi kartına şubeye gitmeden başvuru | bank name | Şubeye gitmeden kredi kartı başvurusu nasıl yapılır: 2026 rehberi |
| Lening tot 2000 euro zonder BKR: 2026 gids | amount + credit bureau | Lenen met een negatieve kredietregistratie: wat kan er in 2026 |
| Petit prêt de 250 € disponible | amount + availability + short-term | Prêt personnel en ligne : conditions et fonctionnement en 2026 |

## Workflow

1. Shared memory briefing (see arbo-title-creator) with `vertical:Finance`.
2. Find finance winners: a stats query over 30-60 days, adsets whose `ArticleCategory` is `Finance` or whose `Anchor` mentions loan, credit, financing, debt, borrow, instalment, grouped by `Anchor` + `Country`, with profit and ROI. Most past winners sit in `Sale` or `Misc`, not `Finance`.
3. Write titles per country in the native language, using the winner's structure and the rules above. Expand into nearby real subjects: card loans, personal loans, consolidation, refinancing, credit cards, credit records and how screening works, comparing loan costs (in general), instalment plans.
4. Check each title against rules 1-8 and the arbo-title-creator self-check. Drop or fix failures.
5. Submit with `SetNewArticleTitles`, vertical `Finance` (unless the user names another), as recommendations. Pass `referenceName` only when the user names one. Never send finance titles to generation unless the user explicitly asks.
6. Journal entry in shared memory with count, countries and reference name.

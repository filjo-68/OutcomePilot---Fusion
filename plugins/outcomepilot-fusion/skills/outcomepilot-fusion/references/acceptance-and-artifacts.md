# Acceptance criteria and artifact verification

## Positive and negative criteria

Define observable requirements before changing anything material: format, language, audience, content, dates, numbers, units, scope, edits, versions, read and write permissions, delivery target, layout, accessibility, operational usability. State the negative constraints explicitly: original unchanged, no secret included, no broken page, no unsupported claim, no external change. A criterion is useful only if it can show failure, not merely that the work looks polished.

For each required item identify the acceptance signal, the way it is verified and the observation that would falsify it. Link claims, test output, render inspections or read-backs to that item. A partial result has to satisfy a meaningful part of the user's goal; passing a cosmetic or unrelated optional check does not count.

## Checks by kind of work

- Research and analysis: factual applicability, dates, disagreement between sources, independent lineage, numeric consistency, the boundary at which the conclusion changes.
- Code: the real project inspected, a scoped diff, unit, integration or build tests chosen and actually run, secure defaults, regression coverage, stated language and version, an artifact that opens or runs.
- PDF, Word, slides, spreadsheets: the right file and the right pages or sheets, useful content, correct language, readable structure, a rendered or opened view actually looked at, working formulas and references, the metadata the user asked for.
- Pages, artifacts and PWAs: a real project rather than a picture of one, mobile usability, legible type, working navigation and links, correct assets and localization, manifest and service worker if requested, a responsive preview and a runtime check where possible. A visual mock-up is not an installable app.
- Data: correct column meaning, no silent unit changes, preserved precision, both sample and aggregate checks, totals and filters.
- Translation: meaning, terminology, names, dates, numbers, legal and regulatory distinctions, natural idiom in the target language, nothing added.
- Decisions: a feasibility screen, a credible alternative, cost and downside, a reversible pilot where one exists, one best default and the condition that would change it.
- External operations: authority, the intended target, a receipt and an observed postcondition, reconciliation of partial batches and unknown outcomes.
- Automation: a schedule or trigger that actually exists, its connection and owner, a safe data scope, a test run where supported. Instructions for an automation are not a running automation.

## Delivery

An artifact counts as delivered when it has been sent to the user or published through the session's own tools and the user can open it. A path in the working directory is not delivery. Confirm that what was sent is the version that was checked.

## Depth

LIGHT: a sanity check of the answer. STANDARD: a test for each decisive requirement. DEEP: regression, a counterexample, protected items and the relevant independent verification. Work that looks good but is unusable or false does not pass. Work that is technically accurate but unreadable does not pass a reader-facing criterion either.

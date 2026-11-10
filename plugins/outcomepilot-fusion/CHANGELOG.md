# Changelog

## 2.0.1 — license, icon and marketplace metadata (2026-11-10)

- Licensed under Apache-2.0: `LICENSE` (unmodified license text), `NOTICE`, and `license` in the manifest.
- Added a 1024 × 1024 PNG icon at `.claude-plugin/icon.png`.
- Added `homepage` and `repository` to the manifest and an install line to the README.
- Release gate now requires the license file to match the manifest and the icon to be a square PNG of 512 to 2048 px under 2 MB; seven tests added (153 in total).
- No change to the skill instructions, the agent, the record checker or the schema.

## 2.0.0 — Claude edition (2026-11-10)

Port of v1.1.1 from the ChatGPT plugin format to the Claude plugin format. Major version because the host, the manifest and the file layout change; a v1 package does not install on Claude and this one does not install on ChatGPT.

### Packaging

- Manifest is now `.claude-plugin/plugin.json`. Removed root `plugin.json` (with its `com.openai` interface block) and `.codex-plugin/plugin.json`.
- Archive is `outcomepilot-fusion.plugin`.
- Maintainer tooling moved out of the skill folder to `dev/` (`build_release.py`, `release_check.py`, `tests/`, `evals/`), so the skill carries only what it uses at run time.

### Skill

- Description rewritten in the third person with Bulgarian, English and Norwegian trigger phrases and an explicit "not for quick questions" boundary; version moved to `metadata.version`.
- Body rewritten for Claude: plain imperative instructions with reasons, less emphasis markup, about 1 900 words.
- New "Where this skill sits" section: host rules, then the user's standing preferences and messages, then the skill.
- Instructions mapped to session tools, each conditional on availability: task list, question tool, search and fetch, file delivery and artifacts, connectors, scheduled tasks, agents.
- Added the delivered-versus-created distinction, working on copies of user files, and behaviour for unattended runs.
- External actions: the user's explicit go-ahead in the conversation is required; a host permission prompt is not a substitute.
- Readiness ladder unified to DESIGNED, STATIC_OK, OFFLINE_TESTED, INSTALLED, LIVE_TESTED, PRODUCTION_READY. v1.1.1 used `LOCALLY_TESTED`/`HOST_SAVED` in SKILL.md and `STATIC_OK`/`OFFLINE_TESTED`/`HOST_SAVED` in the reference.
- Record state priority in `references/effort-stopping.md` corrected to match what `record_audit.py` does (`WORK_REMAINING` before the final `BLOCKED`).
- All eight references revised for Claude; `quickstart-bg.md` no longer uses the `@` invocation and gains examples for independent verification and scheduled tasks.

### Added

- Agent `outcome-verifier`: read-only, fresh-context re-check against acceptance criteria. Dispatched only on the user's request or in an explicitly requested deep audit.
- Five Claude-specific evaluation scenarios (E31–E35), status `NOT_RUN`.
- Release gate checks: Claude manifest fields, absence of other hosts' manifests, skill description length and characters, skill body length, every reference routed from SKILL.md, agent front matter, wording left over from another host, and a wider credential scan.
- Release tests grew from 22 to 53.

### Unchanged

- `scripts/record_audit.py`, `schemas/execution_record.schema.json` and `examples/complete_record.json` are byte-identical to v1.1.1.
- The 26 + 67 record-audit tests are unchanged except for the path to the validator and a docstring that said 60 where the file defines 67 cases.
- Scenarios E01–E30 are unchanged.

### Not claimed

- No live end-to-end evaluation of this edition has been run. Structure was validated and unit tests pass; behaviour in real tasks is unmeasured.

## 1.1.1 — metadata reconciliation (2026-11-10)

- Reconciled release metadata and documentation with the actually executed **67** distinct audit scenarios; no behavior change from v1.1.0.

## 1.1.0 — adversarial audit and hardening (2026-11-10)

- Resolved malformed-link TypeError; record parser now returns INVALID_STATE for malformed nested structures instead of crashing.
- Enforced closed JSON field sets, required acceptance criteria, valid integer step bounds, nonblank references, reciprocal evidence links and unresolved FAIL contradictions.
- Enforced distinct external-action receipt and postcondition evidence identifiers; rejected DONE with pending authorization.
- Added 67 unique reproducible sequential adversarial record-audit scenarios and strengthened deterministic release-gate checks.
- Added documented multi-cycle audit protocol and clear separation between deterministic local tests, live model testing and real user satisfaction.
- Added reproducible archive builder, ZIP containment checks, stricter manifest and evaluation-fixture validation.
- Preserved identity and previous user-facing behavior: finished outcome first, editorial readability, proportional rigor and privacy guardrails. Original source plugins unchanged.
- Does not claim audited scenario simulations prove truth, live host performance or user-perceived perfection.

## 1.0.0 — initial independent fusion edition (2026-11-10)

- Combined result-first execution, editorial voice, formal criteria, provenance, safe external effects and bounded repair.

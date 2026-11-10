# OutcomePilot Fusion — Claude edition 2.0.1

A skill-based plugin for Claude that carries a task through to a finished, checked deliverable and reports only what was actually verified. It is a port of **OutcomePilot Fusion — Verified Excellence v1.1.1**, which was written for ChatGPT. The method is the same; the packaging, the triggering and the instructions are rewritten for how Claude loads skills and for the tools a Claude session really has.

It aims for a result the user can rely on. It never guarantees perfection, a score or user delight.

## Install

In Claude Code 2.1.275 or later:

```
/plugin install outcomepilot-fusion --marketplace filjo-68/OutcomePilot---Fusion
```

In the Claude app, open the `outcomepilot-fusion.plugin` file and accept it.

## What is in the plugin

| Component | Purpose |
|-----------|---------|
| Skill `outcomepilot-fusion` | The working method: route the request, frame acceptance, match rigor to consequences, verify evidence, do the work, guard external actions, verify, repair, report. Eight reference files are read only when a task needs them. |
| Agent `outcome-verifier` | An optional, read-only re-check of a finished deliverable from a clean context. Used only when you ask for an independent verification or explicitly request a deep audit. |
| `scripts/record_audit.py` | An optional local checker for a JSON execution record. It tests internal consistency only. |
| `dev/` | Maintainer tooling: release gate, reproducible archive builder, unit tests, and a catalog of live evaluation scenarios that have not been run. |

There is no MCP server and no hook. The plugin adds no tools, permissions or memory.

## How to use it

Name it or describe the job:

- "OutcomePilot Fusion: направи двустраничен наръчник от тези бележки и провери готовия файл."
- "Carry this through to a verified result: fix the bug in the attached archive and run the tests."
- "Провери независимо дали резултатът покрива критериите." (runs the verifier agent)

Claude also offers the skill in the skills menu. It is meant for real deliverables, not for quick questions. It works in Bulgarian, English and Norwegian Bokmål and follows the language of your message.

Your own standing preferences and what you type in the conversation take precedence over the skill wherever they differ, including language, format and length.

## What changed from the ChatGPT version

- Manifest moved to `.claude-plugin/plugin.json`; the two ChatGPT manifests are removed.
- The skill description now carries trigger phrases, because Claude selects a skill from its description rather than from an `@` mention.
- The instructions refer to what a Claude session has: a task list, a question tool, search and fetch, file delivery and artifacts, connectors, scheduled tasks and agents, each only "when the session has one".
- "Created" and "delivered" are treated as different claims: a file counts as delivered once it has been sent or published to the user.
- External actions require the user's explicit go-ahead in the conversation; a host permission prompt does not replace it.
- One readiness ladder is used throughout (the original used two slightly different ones).
- A fresh-context verifier agent replaces the original's "no independent judge available" limitation, with its result labelled as an AI re-check, not third-party proof.
- `record_audit.py`, the schema and the example record are byte-identical to v1.1.1. Maintainer tooling moved out of the skill folder into `dev/`.

## Limits

- `RECORDED_COMPLETE` from the checker means the record is coherent. It is not externally verified success.
- The unit tests are deterministic fixtures for the checker and the packaging gate. They are not live trials of the model.
- The 35 scenarios in `dev/evals/` are specifications with status `NOT_RUN`. Until they are run on real tasks and judged independently, there is no measured evidence of accuracy, cost, speed or user satisfaction for this edition.
- The verifier agent belongs to the same model family as the author of the work.

## Reproducible checks

From the plugin root, with Python 3.9 or later and no extra packages:

```bash
python3 dev/build_release.py . ../outcomepilot-fusion.plugin   # refresh hash manifest, write archive
python3 dev/release_check.py .                                 # static gate, then 153 unit tests
python3 skills/outcomepilot-fusion/scripts/record_audit.py skills/outcomepilot-fusion/examples/complete_record.json
claude plugin validate .                                       # where the Claude CLI is available
```

The builder writes only `FILE_HASHES.json` inside the plugin root and the archive at the path you give it.

## License

Apache License 2.0. Copyright 2026 Filip Nankov. See `LICENSE` and `NOTICE`.

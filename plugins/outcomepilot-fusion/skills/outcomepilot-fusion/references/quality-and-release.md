# Quality gates, evidence levels and end-to-end comparison

## Two separate scorecards

### Deterministic package and tool integrity

The manifest parses; referenced paths exist; the schema is internally valid; the helper's tests pass; fixtures contain no secrets; the tests exercise mistaken approval, missing evidence, ambiguous external changes, protected files, partial outcomes, runaway step counts, contradictory statuses and correct completion records.

### Actual effectiveness, measured independently

Run the candidate and its baseline on identical held-out real tasks: the same inputs, host, model, source access, quotas and permissions, in randomized order where feasible. Judge acceptance by independently observed tool state or a qualified person. Record model and tool versions and dates, time and cost where metered, raw outcomes and failures. Compare: verified completion rate; false completion; critical authority or privacy violations; factual error; evidence lineage; usability and readability; regressions; cost per accepted outcome. Repeat non-deterministic trials. Synthetic fixtures and a model's score of its own work are not lived acceptance.

## Readiness levels

- `DESIGNED`: instructions, schema and proposed tests exist.
- `STATIC_OK`: manifest, references, syntax and package integrity checked.
- `OFFLINE_TESTED`: deterministic tests run and passed in a known local environment.
- `INSTALLED`: saved or installed on the host. Neither this nor `OFFLINE_TESTED` proves correct future behaviour.
- `LIVE_TESTED`: recorded real prompts, tool interactions and observed outcomes, reviewed.
- `PRODUCTION_READY`: operational acceptance, security and permission tests, and the owner's sign-off appropriate to the task.

Use the same ladder when reporting on any deliverable, not only on this plugin.

## Release gates

No unjustified claim of completeness, a perfect score, zero hallucinations or production readiness. A release can be technically valid and still untested with a real user. Fix material failures and rerun the affected checks. Preserve the originals: a new version or a separate copy, never a destructive update without authorization. Cite source versions precisely. Promotion to production needs independent testing beyond what a package can contain.

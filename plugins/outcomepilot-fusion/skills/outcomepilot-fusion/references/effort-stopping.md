# Bounded effort, progress and stop policy

1. Spend verification effort first on the assumption most able to reverse the answer or cause irreversible damage.
2. Use the tools that exist in the session. Avoid redundant retrieval. A hundred repetitions of the same check are not evidence.
3. Set `max_steps` explicitly when a tool-driven workflow needs an auditable cap. Defaults: at most two discretionary retries of the same error and two exploratory steps without new usable evidence before changing method. Stricter limits from the user or a tool take precedence.
4. After a failure, change something falsifiable: the hypothesis, the input, the test or the tool. An unchanged retry is rarely justified and is unsafe when a side effect is ambiguous.
5. "More work remains" does not justify continuing indefinitely. Name the one concrete next action and check that it is necessary.
6. Stop optional refinement when further effort is unlikely to change acceptance, risk, readability or direct usefulness. Do not stop early while a mandatory criterion is still solvable within the budget.
7. Dispatch the `outcome-verifier` agent only when the user asked for an independent check or explicitly requested a DEEP audit. An agent run costs time and tokens and starts without context, so it is not a default step.

## Record state priority

When the optional execution record is used, `record_audit.py` resolves the state in this order:

INVALID_STATE (malformed) > CANCELLED or UNSAFE > BLOCKED (unreconciled external write) > RECORDED_COMPLETE (all required criteria and postconditions linked and passing) > BUDGET_EXHAUSTED > APPROVAL_REQUIRED > RECORDED_PARTIAL (useful evidenced portion) > WORK_REMAINING > BLOCKED.

The checker examines only whether the declared record is consistent. It does not enforce limits, grant permission, prove facts, attest that a provider result is real, or issue a user-facing SUCCESS. `RECORDED_COMPLETE` and `SUCCESS` are always separate statements.

# Falsifiable multi-cycle audit protocol

An audit requested for N iterations needs N distinguishable test hypotheses with observed outcomes. N self-endorsements, N rewrites or imagined expert votes are not an audit. An iteration may find no defect, but it has to test a particular failure mode or criterion and record an observation someone else could reproduce. Name any phase that was not executed.

For each cycle record:

`sequence | criterion or failure mode | fixture or real target | test operation performed | expected | observed | defect class | repair, if any | retest result`

For a large audit, keep the ordered ledger in a file and deliver it. When a check leads to a change, rerun the affected group and every mandatory regression test.

Keep these kinds of evidence apart, because they prove different things: deterministic local fixtures, mocked tests, source inspection, a live run in the real environment, externally observed effects, a fresh-context re-check by the `outcome-verifier` agent, and acceptance by a real user. The verifier agent shares the model family of the author, so its agreement is a second look, not an independent authority.

Do not chase a maximum score. Set the stop condition on material defects and on coverage that could still lead to action. Use conservative wording wherever a result cannot be independently authenticated. A passing local test suite does not prove future model behaviour.

User-perceived excellence needs both objective acceptance (completeness, factual grounding, correct behaviour, negative conditions, accessibility, legibility) and feedback from the actual reader or user. Synthetic praise is not evidence. For subjective dimensions, state the rubric and whether the evaluation was a self-review, an agent re-check or a human judgment.

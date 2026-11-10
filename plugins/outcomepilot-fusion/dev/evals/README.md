# Proposed end-to-end evaluation set — NOT RUN

`scenario_catalog.jsonl` holds 35 acceptance and negative-test specifications: E01–E30 carried over unchanged from v1.1.1, and E31–E35 added for behaviour specific to a Claude session (triggering by name, delivery of files, precedence of user preferences, the verifier agent, unattended runs).

None of them has been run as a live trial. To run them, use the same model, host, access, inputs, budget and grading rules for each variant being compared (for example Claude with and without the plugin, or this edition against the ChatGPT original on its own host); randomize the order; keep the tool traces; have the results judged independently; and score real artifacts and postconditions, not how confident the text sounds. Store results in a separate file. The release gate requires every catalog entry to stay `NOT_RUN`.

Worth measuring: verified completion rate, false completion rate, critical authority or privacy incidents, factual correctness, source lineage, cost per accepted deliverable, readability, user preference and elapsed time.

A scenario that has not been executed is zero evidence of performance.

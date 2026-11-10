# OutcomePilot Fusion

A plugin for Claude that carries a task through to a finished, checked deliverable and reports only what was actually verified: acceptance criteria, evidence checks, safe handling of external actions, bounded repair, an optional fresh-context verifier agent and an honest completion status.

This repository is a Claude plugin marketplace with one plugin, `outcomepilot-fusion`.

## Install

In Claude Code 2.1.275 or later:

```
/plugin install outcomepilot-fusion --marketplace filjo-68/OutcomePilot---Fusion
```

On earlier versions:

```
/plugin marketplace add filjo-68/OutcomePilot---Fusion
/plugin install outcomepilot-fusion@outcomepilot
```

## Use

Name it or describe the job:

- "OutcomePilot Fusion: направи двустраничен наръчник от тези бележки и провери готовия файл."
- "Carry this through to a verified result: fix the bug in the attached archive and run the tests."

It works in Bulgarian, English and Norwegian Bokmål. Details, limits and the change history are in [`plugins/outcomepilot-fusion/README.md`](plugins/outcomepilot-fusion/README.md) and [`plugins/outcomepilot-fusion/CHANGELOG.md`](plugins/outcomepilot-fusion/CHANGELOG.md).

## Status

Structure validated with `claude plugin validate`; 153 offline unit tests pass. No live end-to-end evaluation has been run, so behaviour in real tasks is unmeasured. The plugin never guarantees correctness.

## Checks

```bash
python3 plugins/outcomepilot-fusion/dev/release_check.py plugins/outcomepilot-fusion
claude plugin validate .
```

## License

Apache License 2.0. Copyright 2026 Filip Nankov. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

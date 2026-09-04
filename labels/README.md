# Labels — HELD-OUT ANSWER KEY
Nothing under `harness/` may read this directory. `tests/test_isolation.py` fails the build if it does.
Labels are committed at `prereg-v1` and published with the paper.

One entry per config id (`labels.json`, schema in `labels.schema.json`):
- valid configs: `expected_verdict: PASS`, `faults: []`
- fault configs: exactly one fault — domain, location (param or section as it appears in the config), canonical_remediation
- silence probes: `expected_verdict: REVIEW`, `undeterminable: true`, `probe_fact`

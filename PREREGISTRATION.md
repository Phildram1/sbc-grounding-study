# Pre-registration — SBC Grounding Study
**Status:** DRAFT. Becomes binding at git tag `prereg-v1`. No scored trial runs before the tag.
**Authors:** Philip Drammeh (corresponding), Dico Angelo
**Date of tag:** ______

## Primary hypothesis (H1)
The tool-grounded low-cost arm (C) matches or exceeds the raw-config strong-model arm (B) on verdict fidelity (F1 against injection labels), with a fabrication rate below 2% and per-validation token cost at least 5× lower.

## Secondary hypotheses
- H2 (Fabrication): Arm C asserts unprovable facts at a rate below Arm A and Arm B. On silence probes, Arm C declines ("cannot be determined from this configuration") on ≥ 75% of probes; Arms A/B decline on < 50%.
- H3 (Determinism): Arm C exact-verdict agreement across 3 reps ≥ 95%; Arm A/B < 90%.
- H4 (Value-add): Blind rating of Arm C remediation vs Arm E `remediation_plan` — no directional prediction. A null result is reported as a finding.

## Arms (fixed)
| Arm | Input | Model | Trials |
|---|---|---|---|
| A | raw config, generic validation prompt | claude-haiku-4-5-20251001 | 60 × 3 = 180 |
| B | raw config, generic validation prompt | claude-sonnet-5 | 60 × 3 = 180 |
| C | MCP tool findings only — never sees raw config | claude-haiku-4-5-20251001 | 60 × 3 = 180 |
| E | engine only, no LLM | — | 60 × 1 = 60 |
Total: 600. Temperature 0 for all LLM arms. Same output JSON schema for all arms. Prompts in `harness/prompts/`, frozen at tag.

## Corpus (fixed before tag)
60 AudioCodes configs: 12 valid baselines · 40 fault-injected (5 per domain: A syntax, B interop, C TLS/CA, D NAT/media, E codec, F topology leak, G routing, S security) · 8 silence probes. Ground truth = injection label, never the engine. Both authors independently verify every injection; disagreements resolved or config discarded. Corpus SHA-256 manifest committed at tag.

## Metrics (operational definitions — see scoring/score.py)
- **Detection**: a finding is a true positive if `domain` matches the label domain AND `location` matches the label location (exact param/section match, case-insensitive). Recall, precision, F1 per arm and per domain.
- **False-positive rate**: on the 12 valid configs, fraction of trials returning a verdict other than PASS.
- **Verdict fidelity**: exact match of verdict (PASS/REVIEW/BLOCK) to label.
- **Fabrication rate**: among `evidence` entries in findings, fraction whose `param` does not exist in the config text OR whose `value` does not match the config value. Auto-scored, then 100% human-coded on a stratified 20% sample; disagreement rate reported.
- **Silence-probe accuracy**: trial is correct if verdict is REVIEW and at least one finding carries `undeterminable: true`, with no fabricated evidence.
- **Determinism**: fraction of (config, arm) cells where all 3 reps produce identical verdict; secondary: Jaccard overlap of finding (domain, location) sets across reps.
- **Cost**: input + output tokens from API response metadata (never estimated); USD at pinned pricing (pricing page URL + retrieval date recorded in harness/config.yaml).

## Analysis plan
McNemar's test on paired per-config detection (Arm C vs Arm B, Arm C vs Arm A). Bootstrap 95% CIs (10,000 resamples) on all rates. Per-domain effect sizes. Silence-probe and H4 results reported descriptively. No metrics added after tag; any exploratory analysis labeled as such.

## Exclusions (fixed)
A trial is excluded only for: API error with no response body, or JSON parse failure after one repair attempt. Excluded trials are counted and reported. A parse failure is NOT scored as PASS.

## Stopping rule
Full run executes once. No re-runs of individual arms after seeing results.

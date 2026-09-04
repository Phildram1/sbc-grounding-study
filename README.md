# Deterministic Grounding for LLM Agents in Safety-Critical Configuration Validation
Experiment repository — Drammeh & Angelo. Design reference: Research Design v2.1.

## Repo map
```
PREREGISTRATION.md      hypothesis + analysis plan — tag as `prereg-v1` BEFORE any scored trial runs
corpus/                 60 synthetic AudioCodes configs (12 valid · 40 fault-injected · 8 silence probes)
labels/                 ANSWER KEY — held out. harness/ MUST NOT import or read this directory.
harness/                trial runner (arms A, B, C, E) — writes append-only JSONL with full provenance
scoring/                scorer — reads results/*.jsonl + labels/, every score traceable to a trial record
analysis/               stats (McNemar, bootstrap CIs)
notebooks/              Colab runner
tests/                  traceability + isolation guards (run before every trial batch)
results/                trial logs (JSONL, one file per batch)
```

## Non-negotiable rules (from the MyAntFarm.ai audit)
1. Answer key is held out from the system under test. `harness/` has no code path to `labels/`. `tests/test_isolation.py` enforces this.
2. Every scored value is traceable to a trial record. Scorer outputs carry `trial_id` + `response_sha256`. No constants, no fixtures, no fallbacks that silently score.
3. Pre-registration commit is tagged before the full run. Scorer at tag `prereg-v1` is the scorer used.

## Run order
```
pip install -r requirements.txt
python -m pytest tests/                      # isolation + traceability guards
python harness/run_trials.py --arm A --configs corpus/configs --reps 1 --limit 5 --out results/pilot_A.jsonl
python scoring/score.py results/pilot_A.jsonl --labels labels/labels.json --out results/pilot_A_scores.json
```
Arms C and E require `SBC_ENGINE_MODE` set (see harness/engine_adapter.py).

## Build status
- [x] Pre-registration draft
- [x] Corpus schema + fault taxonomy skeleton
- [x] Harness: arms A/B live; C/E adapter interface defined, engine binding pending
- [x] Scorer: detection, false-positive, determinism, cost, fabrication (auto + coding sheet)
- [ ] Corpus: 0/60 configs built
- [ ] Engine binding for C/E
- [ ] Pilot (5 configs × A/B) run
- [ ] `prereg-v1` tag

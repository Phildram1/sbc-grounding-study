# Deterministic Grounding for LLM Agents in Safety-Critical Configuration Validation

**Research Design v2.1 — Drammeh & Angelo**
**Status:** Working draft · supersedes v2.0 · §10 fallback active as of 2026-09-03
**Target venue:** arXiv (cs.MA primary; cross-list cs.SE, cs.NI)
**Testbed:** SBC-AutoOps — deterministic SBC validation engine (5 vendor parsers, 8 validation domains, 59 checks, PASS/REVIEW/BLOCK verdicts) exposed to agents via an MCP server of eleven typed, read-only tools

---

## 1. What changed from v1.0

v1.0 tested whether orchestrated LLMs could validate SBC configurations. That is the thing the testbed deliberately does *not* do — the engine is stdlib-only, deterministic, and refuses to guess. v2.0 tests the question the architecture actually answers: **what is the correct division of labor between a deterministic engine and an LLM agent in safety-critical validation, and what does grounding the agent in the engine buy you?**

Scope decisions carried forward: single vendor (AudioCodes — the only parser with full domain depth), architecture and models fixed upfront (§5), prompts published in full, corpus and harness open-sourced under Apache 2.0, taxonomy validity supported by the SBC practitioner survey. This paper stands alone; it does not cite or build on prior work by the authors.

---

## 2. The claim

> When an LLM reasons directly over raw configuration text, it fabricates facts the configuration cannot prove, drifts across runs, and requires an expensive model to approach acceptable accuracy. When the same LLM reasons over typed findings from a deterministic engine, fabrication collapses, verdicts inherit the engine's determinism, and a low-cost model performs the task on a fraction of the tokens.

Pilot evidence (lab work, Drammeh & Angelo): a designed extraction schema fabricated 1.1% of unobservable fields versus 20.9% for a naive schema, deterministic across runs. The paper converts this observation into a controlled study. *Attribution of the pilot figures to be agreed between authors before any public use.*

**Framing.** The paper locates determinism where it belongs — in the deterministic layer — and shows empirically what the model should and should not be allowed to decide. The introduction motivates this from the safety-critical validation problem, not from prior work.

---

## 3. Research questions

- **RQ1 — Fabrication.** What fraction of asserted facts are not provable from the configuration, for raw-config agents versus tool-grounded agents? Sub-test: where the engine is deliberately silent (domains it cannot prove from the export), does the grounded agent correctly report "verify out of band," or fill the gap?
- **RQ2 — Verdict fidelity.** How accurately does each arm detect injected faults against known labels? For the grounded arm specifically: does the agent relay the engine's findings faithfully, or distort, suppress, or add to them?
- **RQ3 — Determinism.** How stable are verdicts and remediation guidance across identical repeated runs, per arm and per model tier?
- **RQ4 — Cost frontier.** Tokens and dollars per validation by arm and model tier. Central comparison: Arm B versus Arm C.
- **RQ5 — Where the LLM earns its place.** Above the engine's own outputs, does the LLM add measurable value in remediation quality, cross-finding synthesis, REVIEW-verdict judgment, or fleet prioritization? A null result is reported as a finding.

**Pre-registered primary hypothesis** (committed to the repo at tag `prereg-v1` before trials run): *Arm C (tool-grounded, low-cost model) matches or exceeds Arm B (raw config, strong model) on verdict fidelity, with a fabrication rate below 2% and per-validation token cost at least 5× lower.* Secondary hypotheses H2–H4 are in `PREREGISTRATION.md`.

---

## 4. Test corpus

### 4.1 Composition — 60 AudioCodes configurations

- **12 known-valid baselines** across deployment profiles (Direct Routing enterprise, carrier SIP trunk, hybrid, HA pair).
- **40 fault-injected configs** — 5 per engine domain (A syntax, B interop, C TLS/CA, D NAT/media, E codec, F topology leak, G routing, S security). Each fault labeled with domain, location, expected verdict (REVIEW or BLOCK), and canonical remediation. Difficulty tagged obvious/subtle.
- **8 silence-probe configs** — faults or questions located in facts the engine cannot prove from the export (e.g., certificate chain validity where the PEM is absent, out-of-band trust-store state). These test RQ1's sub-question: the correct answer is "cannot be determined from this configuration."

### 4.2 Ground truth and the circularity guard

Ground truth is the injection label, **not** the engine. The engine appears as its own reference arm (§5, Arm E) and is scored against the labels like everything else — including where its 59 checks do not cover a fault. This is what keeps Arm D from winning by construction: the grounded agent is scored on fidelity to *labels*, with a secondary measure of fidelity to the engine's findings.

### 4.3 Construction protocol

Faults injected from public AudioCodes schema documentation and public Microsoft Learn Direct Routing / SBC certification specifications. Both authors independently verify every injection before trials; disagreements resolved or config discarded. Fault taxonomy validity cited to the SBC practitioner survey.

---

## 5. Experimental arms

| Arm | Input to model | Model | Purpose |
|---|---|---|---|
| **A** | Raw config text, generic validation prompt | Low-cost: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Floor for unaided LLM validation |
| **B** | Raw config text, same prompt | Strong: Claude Sonnet 5 (`claude-sonnet-5`) | Ceiling for unaided LLM validation |
| **C** | Engine findings via MCP tools only — never sees raw config | Low-cost: Claude Haiku 4.5 | **Primary arm** |
| **E** | Engine only, no LLM | — | Reference: deterministic, zero fabrication, zero tokens |

Models are pinned by version string and frozen in `harness/config.yaml` at the tag. Sonnet 5 is chosen over Opus 5 as the strong model: it is the realistic production alternative to grounding, and the cost comparison is more conservative. The checklist-prompt ablation (v2.0 Arm B) and the strong-model grounded subset (v2.0 Arm C′) are dropped; if a reviewer asks "is grounding just better prompting?", the answer is that Arm C never sees the configuration at all, so no prompt over raw text is a substitute.

All arms share output schema (verdict / findings with domain + location / remediation / confidence statement), pinned model versions, fixed temperature, identical serialization. Arm C runs against the engine in default offline mode; `probe_endpoint` disabled. Every engine call is logged with engine version and output hash so Arm C relay fidelity is scored against Arm E.

---

## 6. Trial structure

| Arm | Configs | Reps | Trials |
|---|---|---|---|
| A | 60 | 3 | 180 |
| B | 60 | 3 | 180 |
| C | 60 | 3 | 180 |
| E | 60 | 1 | 60 |
| **Total** | | | **600** |

Arm E is deterministic by construction and needs one rep; run three in the pilot to demonstrate it. Optional determinism deep-dive: 10 configs × Arms A and C × 10 reps.

**Token expectation.** Arms A and B carry the full config (~5–15K tokens each). Arm C carries structured findings only (~1–3K). Arm C's cost advantage is partly architectural (smaller input) and partly model choice — the A-vs-C comparison isolates the architectural component at equal model; report both.

---

## 7. Metrics

- **Fabrication rate (RQ1):** asserted facts per response not provable from the config, coded against a fixed rubric of observable vs. unobservable fields. Silence-probe accuracy reported separately.
- **Detection recall / precision / F1 (RQ2)** per domain against labels; false-positive rate on the 12 valid configs. For Arm C additionally: findings agreement with Arm E output (relay fidelity).
- **Verdict determinism (RQ3):** exact-agreement rate across reps per config-arm; remediation stability via embedding similarity plus blind human spot-check.
- **Cost (RQ4):** input/output tokens, latency, dollars per validation at pinned pricing (pricing page cited with retrieval date).
- **LLM value-add (RQ5):** blind dual-author rating of Arm C remediation and synthesis output versus Arm E's `remediation_plan` on specificity, correctness, change safety, and prioritization. Inter-rater agreement reported.

**Analysis.** McNemar's test for paired detection differences; bootstrap CIs on all rates; effect sizes per domain. Silence-probe results and RQ5 reported descriptively.

---

## 8. Confidentiality and IP

- **Microsoft line:** all interop and TLS/CA fault definitions from public documentation only. No internal process, deal, or roadmap information in corpus, prompts, or paper.
- **Open-source split:** corpus, harness, agent prompts, scoring code, and raw trial logs published under Apache 2.0 in the co-owned repository. The engine itself remains proprietary; the paper cites it as the grounding source and describes its interface (the MCP tool surface), not its internals. Reproducibility of the *experiment* is preserved; the product is not open-sourced.
- **No customer or client configuration data, ever.** Synthetic corpus only.

---

## 9. Peer review gate

arXiv provides no review, so an independent one is mandatory before submission. Two reviewers, two briefs:

**Methods reviewer (required).** With a written brief:
1. Reproduces every headline figure from the raw trial logs using only the published scoring code.
2. Confirms the scorer measures what the paper says — fabrication coding and detection scoring operate on model output, not on constants or fixtures. `tests/test_traceability.py` is the starting point, not the end.
3. Confirms the pre-registered hypothesis, corpus manifest, prompts, and scoring code match tag `prereg-v1`.
4. Signs off in writing; sign-off is included in the repo.

**Domain expert validator (optional).** Independently verifies a sample of fault injections and labels. Recruited from Philip's network; if unavailable, dual-author verification stands and is stated as a limitation.

Budget: two weeks. Reviewer independence from both authors and from Metaventions confirmed in writing.

## 10. Roles

- **Philip:** design, corpus and fault taxonomy, labels, harness, scoring, statistics, writing, submission. Corresponding author.
- **Dico:** engine binding for Arms C and E (HTTP endpoint or local CLI), orchestration design review, code review, co-authorship. *The §10 v2.0 fallback is active: Philip builds the harness; Dico's commitment is reduced to the engine interface and review.*
- **Methods reviewer and optional domain validator:** per §9.
- Authorship order and Metaventions affiliation agreed in writing before drafting.

## 11. Timeline

| Weeks (from 2026-09-03) | Milestone |
|---|---|
| 1 | Repo public · pre-registration drafted · harness A/B live · first 5 configs |
| 2–3 | Corpus build (60 configs incl. silence probes) · labels · second-verifier sign-off · engine binding from Dico |
| 4 | Pilot: 5 configs × all arms · fix instrumentation · tag `prereg-v1` |
| 5 | Full 600-trial run in Colab |
| 6–7 | Analysis · RQ5 blind rating |
| 8–9 | Draft · independent review gate |
| 10 | Revisions · arXiv submission (mid-November) |

## 12. Open decisions

1. ~~Model tiers~~ — fixed in §5.
2. ~~Fault count per domain~~ — 5 per domain, 40 total.
3. Silence-probe design — S06–S08 unobservable facts to be chosen; "correctly declined" coded per `PREREGISTRATION.md`.
4. Arm C tool surface — restrict to the validation path (`validate_config`, `remediation_plan`); log every tool call. To confirm with Dico at engine binding.
5. Reviewer selection and independence check.
6. API budget ceiling — estimate under $100, dominated by Arm B.
7. Engine binding mode — HTTP on the hosted validator or local CLI. Ask to Dico.

---

*v2.1 — supersedes v2.0. Nothing herein is final until both authors sign off on §8 and §10.*

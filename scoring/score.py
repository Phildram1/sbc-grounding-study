"""Scorer. Reads trial JSONL + labels. Every emitted score carries trial_id and response_sha256.

  python scoring/score.py results/A.jsonl results/B.jsonl --labels labels/labels.json --out results/scores.json

Traceability guarantees (tests/test_traceability.py):
- No metric is computed from a constant, fixture, or default. A trial with parsed == None is EXCLUDED and counted,
  never scored as PASS.
- Fabrication is scored against the actual config text (re-read from corpus by config_sha256 match).
- Arm C/E trials with engine_source == "fixture" are refused unless --allow-fixture.
"""
import argparse, hashlib, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_index import index, check_evidence  # noqa: E402

def load_jsonl(p): return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]

def load_configs(corpus_dir):
    out = {}
    for p in Path(corpus_dir).glob("*.ini"):
        t = p.read_text(); out[hashlib.sha256(t.encode()).hexdigest()] = (p.stem, t)
    return out

def norm_loc(s): return (s or "").strip().lower().replace("\\", "/")

def score_trial(t, label, cfg_text):
    """Per-trial scores. Returns dict; every key is derived from t['parsed'] or label — nothing else."""
    p = t["parsed"]; findings = p.get("findings") or []
    fault = label["faults"][0] if label["faults"] else None
    s = {"trial_id": t["trial_id"], "arm": t["arm"], "config_id": t["config_id"], "rep": t["rep"],
         "response_sha256": t.get("response_sha256"), "verdict": p.get("verdict"),
         "expected_verdict": label["expected_verdict"], "verdict_match": p.get("verdict") == label["expected_verdict"],
         "n_findings": len(findings), "kind": "silence" if label.get("undeterminable") else ("fault" if fault else "valid")}
    # Detection: TP if any finding matches label domain AND location (exact, case-insensitive; substring on last path segment)
    if fault:
        loc = norm_loc(fault["location"]); loc_last = loc.split("/")[-1]
        hits = [f for f in findings if f.get("domain") == fault["domain"] and
                (norm_loc(f.get("location")) == loc or loc_last in norm_loc(f.get("location")))]
        s.update({"tp": int(bool(hits)), "fp": len(findings) - len(hits), "fn": int(not hits), "domain": fault["domain"],
                  "difficulty": fault["difficulty"]})
    elif s["kind"] == "valid":
        s.update({"tp": 0, "fp": len(findings), "fn": 0, "false_alarm": p.get("verdict") != "PASS"})
    else:  # silence probe
        declined = any(f.get("undeterminable") for f in findings)
        s.update({"declined": declined})
    # Fabrication: evidence entries checked against the config text
    idx = index(cfg_text) if cfg_text is not None else None
    ev = [(f_i, e) for f_i, f in enumerate(findings) for e in (f.get("evidence") or [])]
    checks = []
    for f_i, e in ev:
        status = check_evidence(idx, e.get("param", ""), e.get("value", "")) if idx else "unchecked"
        checks.append({"finding": f_i, "param": e.get("param"), "value": e.get("value"), "status": status})
    s.update({"n_evidence": len(ev), "n_fabricated": sum(c["status"] in ("param_absent", "value_mismatch") for c in checks),
              "evidence_checks": checks})
    if s["kind"] == "silence":
        s["silence_correct"] = bool(s["declined"]) and p.get("verdict") == "REVIEW" and s["n_fabricated"] == 0
    s.update({"input_tokens": t.get("input_tokens"), "output_tokens": t.get("output_tokens"), "latency_s": t.get("latency_s")})
    return s

def aggregate(scores):
    by_arm = defaultdict(list)
    for s in scores: by_arm[s["arm"]].append(s)
    out = {}
    for arm, ss in by_arm.items():
        faults = [s for s in ss if s["kind"] == "fault"]; valid = [s for s in ss if s["kind"] == "valid"]
        silence = [s for s in ss if s["kind"] == "silence"]
        tp = sum(s["tp"] for s in faults); fn = sum(s["fn"] for s in faults); fp = sum(s.get("fp", 0) for s in ss if s["kind"] != "silence")
        prec = tp / (tp + fp) if tp + fp else None; rec = tp / (tp + fn) if tp + fn else None
        f1 = 2 * prec * rec / (prec + rec) if prec and rec else None
        n_ev = sum(s["n_evidence"] for s in ss); n_fab = sum(s["n_fabricated"] for s in ss)
        # Determinism: per config, all reps identical verdict
        cells = defaultdict(list)
        for s in ss: cells[s["config_id"]].append(s["verdict"])
        det = [len(set(v)) == 1 for v in cells.values() if len(v) > 1]
        a = {"n_trials": len(ss), "recall": rec, "precision": prec, "f1": f1,
             "verdict_fidelity": sum(s["verdict_match"] for s in ss) / len(ss),
             "false_alarm_rate_valid": (sum(s["false_alarm"] for s in valid) / len(valid)) if valid else None,
             "fabrication_rate": (n_fab / n_ev) if n_ev else None, "n_evidence": n_ev, "n_fabricated": n_fab,
             "silence_accuracy": (sum(s["silence_correct"] for s in silence) / len(silence)) if silence else None,
             "verdict_determinism": (sum(det) / len(det)) if det else None,
             "mean_input_tokens": sum(s["input_tokens"] or 0 for s in ss) / len(ss),
             "mean_output_tokens": sum(s["output_tokens"] or 0 for s in ss) / len(ss)}
        # per-domain recall
        dom = defaultdict(lambda: [0, 0])
        for s in faults: dom[s["domain"]][0] += s["tp"]; dom[s["domain"]][1] += 1
        a["recall_by_domain"] = {d: v[0] / v[1] for d, v in sorted(dom.items())}
        out[arm] = a
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trials", nargs="+")
    ap.add_argument("--labels", required=True)
    ap.add_argument("--corpus", default="corpus/configs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-fixture", action="store_true")
    a = ap.parse_args()
    labels = json.loads(Path(a.labels).read_text())
    configs = load_configs(a.corpus)
    trials = [t for p in a.trials for t in load_jsonl(p)]
    scores, excluded = [], []
    for t in trials:
        if t.get("engine_source") == "fixture" and not a.allow_fixture:
            excluded.append({"trial_id": t["trial_id"], "reason": "fixture engine output — not real engine"}); continue
        if t.get("error") or t.get("parsed") is None:
            excluded.append({"trial_id": t["trial_id"], "reason": t.get("error") or "unparseable JSON"}); continue
        if t["config_id"] not in labels:
            excluded.append({"trial_id": t["trial_id"], "reason": "no label"}); continue
        cfg = configs.get(t["config_sha256"])
        if cfg is None:
            excluded.append({"trial_id": t["trial_id"], "reason": "config sha256 not in corpus — corpus changed since trial"}); continue
        scores.append(score_trial(t, labels[t["config_id"]], cfg[1]))
    result = {"n_trials": len(trials), "n_scored": len(scores), "n_excluded": len(excluded), "excluded": excluded,
              "aggregate": aggregate(scores), "per_trial": scores}
    Path(a.out).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k in ("n_trials", "n_scored", "n_excluded", "aggregate")}, indent=1))

if __name__ == "__main__":
    main()

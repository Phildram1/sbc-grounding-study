"""McNemar (paired detection) + bootstrap CIs.  python analysis/stats.py results/scores.json --compare C B"""
import argparse, json, random
from collections import defaultdict
from scipy.stats import binomtest

def mcnemar(a_hits, b_hits):
    """Exact McNemar via binomial test on discordant pairs. a_hits/b_hits: {config_id: 0/1} (majority over reps)."""
    keys = sorted(set(a_hits) & set(b_hits))
    b_only = sum(1 for k in keys if a_hits[k] and not b_hits[k]); c_only = sum(1 for k in keys if b_hits[k] and not a_hits[k])
    n = b_only + c_only
    p = binomtest(b_only, n, 0.5).pvalue if n else 1.0
    return {"n_pairs": len(keys), "a_only": b_only, "b_only": c_only, "p_value": p}

def majority(per_trial, arm, key="tp"):
    cells = defaultdict(list)
    for s in per_trial:
        if s["arm"] == arm and key in s: cells[s["config_id"]].append(s[key])
    return {c: int(sum(v) * 2 >= len(v)) for c, v in cells.items()}

def bootstrap_rate(vals, n=10000, seed=0):
    rng = random.Random(seed); vals = list(vals)
    if not vals: return None
    bs = sorted(sum(rng.choices(vals, k=len(vals))) / len(vals) for _ in range(n))
    return {"mean": sum(vals) / len(vals), "ci95": [bs[int(0.025 * n)], bs[int(0.975 * n)]]}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("scores"); ap.add_argument("--compare", nargs=2, default=["C", "B"])
    a = ap.parse_args()
    d = json.loads(open(a.scores).read()); pt = d["per_trial"]; x, y = a.compare
    out = {"mcnemar_detection": mcnemar(majority(pt, x), majority(pt, y))}
    for arm in {s["arm"] for s in pt}:
        ss = [s for s in pt if s["arm"] == arm]
        out[arm] = {"recall": bootstrap_rate([s["tp"] for s in ss if s["kind"] == "fault"]),
                    "verdict_fidelity": bootstrap_rate([int(s["verdict_match"]) for s in ss]),
                    "fabrication_per_evidence": bootstrap_rate([int(c["status"] in ("param_absent", "value_mismatch"))
                                                                for s in ss for c in s["evidence_checks"]])}
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()

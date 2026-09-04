"""Trial runner. Writes append-only JSONL, one record per trial, with full provenance.

  python harness/run_trials.py --arm A --configs corpus/configs --reps 3 --out results/A.jsonl
  python harness/run_trials.py --arm A --configs corpus/configs --reps 1 --limit 5 --out results/pilot_A.jsonl

Isolation: this file and everything it imports has no code path to labels/. Enforced by tests/test_isolation.py.
Resumable: existing (arm, config_id, rep) records in --out are skipped.
"""
import argparse, hashlib, json, os, subprocess, sys, time, uuid
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm_client, engine_adapter  # noqa: E402

def sha(s: str) -> str: return hashlib.sha256(s.encode()).hexdigest()

def git_rev() -> str:
    try: return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE.parent, text=True).strip()
    except Exception: return "unknown"

def load_prompt(rel: str) -> str:
    schema = (HERE / "output_schema.json").read_text()
    return (HERE / rel).read_text().replace("{{OUTPUT_SCHEMA}}", schema)

def build_prompt(arm_cfg, template, config_text, engine_out):
    if arm_cfg["input"] == "raw":
        return template.replace("{{CONFIG}}", config_text)
    if arm_cfg["input"] == "grounded":
        # Grounded arm NEVER sees the raw config. Strip any engine field that echoes it.
        safe = {k: v for k, v in engine_out.items() if k not in ("raw_config", "config_text", "source")}
        return template.replace("{{ENGINE_FINDINGS}}", json.dumps(safe, indent=1))
    raise ValueError(arm_cfg["input"])

def run_one(arm, arm_cfg, cfg, template, config_id, config_text, rep):
    rec = {"trial_id": str(uuid.uuid4()), "arm": arm, "config_id": config_id, "rep": rep,
           "config_sha256": sha(config_text), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "harness_git_rev": git_rev(), "temperature": cfg["llm"]["temperature"]}
    engine_out = None
    if arm_cfg["input"] in ("grounded", "engine"):
        engine_out = engine_adapter.validate(config_id, config_text)
        rec.update({"engine_output": dict(engine_out), "engine_output_sha256": engine_out.sha256,
                    "engine_version": engine_out.get("engine_version"), "engine_source": engine_out.get("engine_source")})
    if arm_cfg["input"] == "engine":
        # Arm E: the engine IS the response. No LLM. Zero tokens.
        rec.update({"model": None, "response_text": json.dumps(dict(engine_out), sort_keys=True),
                    "parsed": {"verdict": engine_out["verdict"], "findings": engine_out["findings"],
                               "remediation": engine_out.get("remediation", []),
                               "confidence_statement": "engine"},
                    "json_repaired": False, "input_tokens": 0, "output_tokens": 0, "latency_s": 0.0})
    else:
        model = cfg["models"][arm_cfg["model"]]
        prompt = build_prompt(arm_cfg, template, config_text, engine_out)
        rec.update({"model": model, "prompt_sha256": sha(prompt), "prompt_template": arm_cfg["prompt"]})
        try:
            r = llm_client.call(model, prompt, cfg["llm"]["temperature"], cfg["llm"]["max_tokens"], cfg["llm"]["max_retries"])
        except Exception as e:
            rec.update({"error": str(e)[:1000], "parsed": None}); return rec
        parsed, repaired = llm_client.parse_json(r.text)
        rec.update({"model_reported": r.model, "response_text": r.text, "response_sha256": sha(r.text),
                    "parsed": parsed, "json_repaired": repaired, "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens, "latency_s": r.latency_s, "stop_reason": r.stop_reason,
                    "request_id": r.request_id})
    return rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["A", "B", "C", "E"])
    ap.add_argument("--configs", default="corpus/configs")
    ap.add_argument("--reps", type=int)
    ap.add_argument("--limit", type=int, help="first N configs only (pilot)")
    ap.add_argument("--only", nargs="*", help="specific config ids")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=str(HERE / "config.yaml"))
    a = ap.parse_args()

    cfg = yaml.safe_load(Path(a.config).read_text())
    arm_cfg = cfg["arms"][a.arm]
    reps = a.reps or arm_cfg["reps"]
    template = load_prompt(arm_cfg["prompt"]) if arm_cfg["prompt"] else None
    paths = sorted(Path(a.configs).glob("*.ini"))
    if a.only: paths = [p for p in paths if p.stem in a.only]
    if a.limit: paths = paths[:a.limit]
    if not paths: sys.exit("no configs found")

    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                d = json.loads(line); done.add((d["arm"], d["config_id"], d["rep"]))
    n = 0
    with out.open("a") as f:
        for p in paths:
            text = p.read_text()
            for rep in range(1, reps + 1):
                if (a.arm, p.stem, rep) in done: continue
                rec = run_one(a.arm, arm_cfg, cfg, template, p.stem, text, rep)
                f.write(json.dumps(rec) + "\n"); f.flush(); n += 1
                status = "ERR" if rec.get("error") else (rec["parsed"] or {}).get("verdict", "NOJSON")
                print(f"{a.arm} {p.stem} r{rep} → {status}  tok={rec.get('input_tokens')}/{rec.get('output_tokens')}")
    print(f"{n} new trials → {out}")

if __name__ == "__main__":
    main()

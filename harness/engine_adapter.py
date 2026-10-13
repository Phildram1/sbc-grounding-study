"""Engine binding for Arms C and E.

The engine (SBC-AutoOps) is proprietary and lives with Metaventions. This module defines the
interface the harness needs and three bindings selected by SBC_ENGINE_MODE:

  cli         — run `sbc-validator validate --ruleset $SBC_ENGINE_RULESET --json` (engine pip-installed).
                `local_mcp` is accepted as an alias until the MCP stdio client replaces it.
  http        — POST config text to SBC_ENGINE_URL (if the hosted validator exposes an API).
  fixture     — read a pre-recorded engine output from results/engine_cache/{config_id}.json.
                FOR PILOT PLUMBING ONLY. Scorer refuses to score Arm C/E trials whose
                engine_source == "fixture" unless --allow-fixture is passed, and flags them.

Every engine call records engine_version and a sha256 of the engine output so the Arm C trial
carries provenance for relay-fidelity scoring against Arm E.
"""
import hashlib, json, os, subprocess
from pathlib import Path

REQUIRED_KEYS = {"verdict", "findings"}   # engine output must at least carry these

class EngineResult(dict):
    @property
    def sha256(self): return hashlib.sha256(json.dumps(self, sort_keys=True).encode()).hexdigest()

def _check(out: dict, source: str) -> EngineResult:
    missing = REQUIRED_KEYS - set(out)
    if missing: raise ValueError(f"engine output missing {missing}")
    out.setdefault("engine_version", "unknown")
    out["engine_source"] = source
    return EngineResult(out)

def _pkg_version() -> str:
    try:
        from importlib.metadata import version
        return version("sbc-autoops-validator")
    except Exception:
        return "unknown"

def normalize_cli(raw: dict) -> dict:
    """Map SBC-AutoOps CLI JSON onto the study's engine-output shape.
    Drops the run timestamp so identical inputs hash identically (determinism check)."""
    findings = [{"check_id": f.get("check_id"), "domain": f.get("domain"), "location": f.get("locator") or "",
                 "severity": f.get("severity"), "description": f.get("title"), "detail": f.get("detail"),
                 "remediation": f.get("remediation")} for f in raw.get("findings", [])]
    return {"verdict": raw["summary"]["verdict"], "risk_score": raw["summary"].get("risk_score"),
            "findings": findings, "call_prediction": raw.get("call_prediction"),
            "engine_version": f"sbc-autoops-validator {_pkg_version()} ruleset={raw.get('ruleset_version')}"}

def validate(config_id: str, config_text: str) -> EngineResult:
    mode = os.environ.get("SBC_ENGINE_MODE")
    if mode is None:
        raise RuntimeError("SBC_ENGINE_MODE not set — Arms C and E require an engine binding "
                           "(local_mcp | http | fixture). See harness/engine_adapter.py.")
    if mode == "fixture":
        p = Path("results/engine_cache") / f"{config_id}.json"
        return _check(json.loads(p.read_text()), "fixture")
    if mode == "http":
        import urllib.request
        req = urllib.request.Request(os.environ["SBC_ENGINE_URL"], data=json.dumps(
            {"vendor": "audiocodes", "config": config_text}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return _check(json.loads(r.read()), "http")
    if mode in ("cli", "local_mcp"):
        # SBC-AutoOps CLI: `sbc-validator validate --ruleset <bundle> --json <file>`.
        # Exit code is non-zero on BLOCK by design, so it is not treated as failure.
        import tempfile
        ruleset = os.environ["SBC_ENGINE_RULESET"]          # path to the signed ruleset JSON
        with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False, encoding="utf-8") as tf:
            tf.write(config_text); path = tf.name
        env = dict(os.environ, PYTHONUTF8="1")
        r = subprocess.run(["sbc-validator", "validate", "--ruleset", ruleset, "--json", path],
                           capture_output=True, text=True, timeout=300, env=env, encoding="utf-8")
        os.unlink(path)
        try:
            raw = json.loads(r.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"engine produced no JSON (rc={r.returncode}): {r.stderr[:500]}")
        return _check(normalize_cli(raw), "cli")
    raise ValueError(f"unknown SBC_ENGINE_MODE {mode}")

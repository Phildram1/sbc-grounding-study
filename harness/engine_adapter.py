"""Engine binding for Arms C and E.

The engine (SBC-AutoOps) is proprietary and lives with Metaventions. This module defines the
interface the harness needs and three bindings selected by SBC_ENGINE_MODE:

  local_mcp   — spawn `sbc-validator mcp` (default offline mode, probe_endpoint disabled) and call
                validate_config / remediation_plan over stdio. Requires the engine installed locally.
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
    if mode == "local_mcp":
        # Minimal stdio call. Replace with the MCP client once the tool surface is confirmed with Dico.
        cmd = os.environ.get("SBC_ENGINE_CMD", "sbc-validator validate --vendor audiocodes --json -")
        r = subprocess.run(cmd, shell=True, input=config_text, capture_output=True, text=True, timeout=300)
        if r.returncode != 0: raise RuntimeError(r.stderr[:500])
        return _check(json.loads(r.stdout), "local_mcp")
    raise ValueError(f"unknown SBC_ENGINE_MODE {mode}")

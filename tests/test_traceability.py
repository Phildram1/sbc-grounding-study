"""Guard 2: every scored value derives from a trial record; unparseable trials are excluded, not defaulted."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scoring"))
import score  # noqa: E402

LABEL = {"expected_verdict": "BLOCK", "faults": [{"fault_id": "FC1", "domain": "C", "location": "TLSContexts/TLSVersion",
         "difficulty": "obvious", "canonical_remediation": "x"}], "verified_by": ["PD"]}
CFG = "[TLSContexts]\nTLSContexts 0 = \"Teams\", 1, 0\nTLSVersion = 1\n"

def trial(parsed, tid="t1"):
    return {"trial_id": tid, "arm": "A", "config_id": "FC1", "rep": 1, "parsed": parsed,
            "response_sha256": "abc", "input_tokens": 10, "output_tokens": 5, "latency_s": 1.0}

def test_scores_carry_provenance():
    s = score.score_trial(trial({"verdict": "BLOCK", "findings": [{"domain": "C", "location": "TLSContexts/TLSVersion",
        "severity": "BLOCK", "description": "", "evidence": [{"param": "TLSVersion", "value": "1"}]}],
        "remediation": [], "confidence_statement": ""}), LABEL, CFG)
    assert s["trial_id"] == "t1" and s["response_sha256"] == "abc"
    assert s["tp"] == 1 and s["n_fabricated"] == 0

def test_fabricated_evidence_is_caught():
    s = score.score_trial(trial({"verdict": "BLOCK", "findings": [{"domain": "C", "location": "TLSContexts/TLSVersion",
        "severity": "BLOCK", "description": "", "evidence": [{"param": "TLSVersion", "value": "1"},
        {"param": "CertificateExpiry", "value": "2027-01-01"}]}], "remediation": [], "confidence_statement": ""}), LABEL, CFG)
    assert s["n_fabricated"] == 1 and s["evidence_checks"][1]["status"] == "param_absent"

def test_no_findings_is_a_miss_not_a_default():
    s = score.score_trial(trial({"verdict": "PASS", "findings": [], "remediation": [], "confidence_statement": ""}), LABEL, CFG)
    assert s["tp"] == 0 and s["fn"] == 1 and s["verdict_match"] is False

def test_identical_reps_do_not_come_from_constants():
    """Two different parsed outputs must yield different scores — a scorer that ignores output would fail this."""
    a = score.score_trial(trial({"verdict": "BLOCK", "findings": [{"domain": "C", "location": "TLSContexts/TLSVersion",
        "severity": "BLOCK", "description": "", "evidence": []}], "remediation": [], "confidence_statement": ""}), LABEL, CFG)
    b = score.score_trial(trial({"verdict": "PASS", "findings": [], "remediation": [], "confidence_statement": ""}), LABEL, CFG)
    assert a["tp"] != b["tp"] and a["verdict_match"] != b["verdict_match"]

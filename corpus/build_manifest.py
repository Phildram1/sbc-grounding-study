"""Regenerate corpus/manifest.json with SHA-256 per config. Carries NO label info."""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = ROOT / "configs"
KIND = {"V": "valid", "F": "fault", "S": "silence"}

def main():
    entries = []
    for p in sorted(CFG.glob("*.ini")):
        cid = p.stem
        if not re.match(r"^(V\d{2}|F[ABCDEFGS]\d|S\d{2})$", cid):
            print(f"skip {cid}: bad id", file=sys.stderr); continue
        head = p.read_text(errors="replace").splitlines()[:5]
        profile = next((l.split("profile:")[1].strip() for l in head if "profile:" in l), "direct_routing")
        parent = next((l.split("parent:")[1].strip() for l in head if "parent:" in l), None)
        e = {"id": cid, "kind": KIND[cid[0]], "profile": profile, "path": f"corpus/configs/{p.name}",
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        if parent: e["parent"] = parent
        entries.append(e)
    (ROOT / "manifest.json").write_text(json.dumps({"version": "1.0", "configs": entries}, indent=2))
    print(f"{len(entries)} configs → manifest.json")

if __name__ == "__main__":
    main()

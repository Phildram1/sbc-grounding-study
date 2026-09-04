"""Index an AudioCodes INI export so evidence claims can be checked against the actual text.
Extracts param=value pairs and table rows (FORMAT/row lines). Case-insensitive keys."""
import re

def index(config_text: str) -> dict:
    """Returns {"params": {name_lower: [values...]}, "tokens": set(all lowercase tokens)}."""
    params, tokens = {}, set()
    for line in config_text.splitlines():
        s = line.strip()
        if not s or s.startswith((";", "#")): continue
        tokens.update(t.lower() for t in re.findall(r"[A-Za-z0-9_.\-:/\\]+", s))
        m = re.match(r"^([A-Za-z0-9_\[\]\\ ]+?)\s*=\s*(.*)$", s)
        if m:
            k, v = m.group(1).strip().lower(), m.group(2).strip().strip('"')
            params.setdefault(k, []).append(v)
            # table row: "IPProfile 0 = 1, 2, 3" → also index table name
            if " " in k: params.setdefault(k.split()[0], []).append(v)
    return {"params": params, "tokens": tokens}

def check_evidence(idx: dict, param: str, value: str) -> str:
    """'supported' | 'value_mismatch' | 'param_absent'."""
    p = param.strip().lower(); p_last = p.split("/")[-1].split("\\")[-1]
    vals = idx["params"].get(p) or idx["params"].get(p_last)
    if vals is None:
        if p_last in idx["tokens"]:  # param name present somewhere (e.g. inside a table row)
            return "supported" if (value or "").strip().lower() in idx["tokens"] else "value_mismatch"
        return "param_absent"
    v = (value or "").strip().strip('"').lower()
    return "supported" if any(v == x.lower() or v in x.lower() for x in vals) else "value_mismatch"

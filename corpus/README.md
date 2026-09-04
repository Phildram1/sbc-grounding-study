# Corpus
60 synthetic AudioCodes Mediant configurations (INI export format). No customer or client data — ever.

## Naming
`corpus/configs/{id}.ini` where id = `V01..V12` (valid), `F{domain}{n}` e.g. `FA1..FA5` (fault-injected), `S01..S08` (silence probes).

## Manifest
`corpus/manifest.json` lists every config with `id`, `kind` (valid|fault|silence), `profile` (direct_routing|carrier_trunk|hybrid|ha_pair), `sha256`. The manifest carries NO fault information — that lives in `labels/`.

## Construction protocol
1. Build the 12 baselines first, one per profile variant. These are the parents of all 48 other configs.
2. Each fault config = one baseline + exactly one injected fault, per `fault_taxonomy.md`.
3. Silence probes = baseline where a fact the engine cannot prove from the export is at issue (e.g. certificate chain validity with PEM absent).
4. Both authors verify each injection independently and sign the label. `labels/labels.json` records `verified_by`.
5. Run `python corpus/build_manifest.py` to regenerate manifest + hashes. Commit manifest at `prereg-v1`.

## Sources for fault definitions (public only)
- AudioCodes Mediant SBC User's Manual / ini parameter reference (public)
- Microsoft Learn: Direct Routing SBC certification requirements; Operator Connect SBC specifications (public)

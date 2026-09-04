# Fault taxonomy — 8 domains × 5 faults = 40 fault-injected configs
Fill each slot before the tag. Each entry: fault_id · description · injection (param/section changed) · expected verdict · difficulty · public source.
Difficulty: obvious = single wrong value, visible in isolation · subtle = valid in isolation, wrong in combination or context.

| Domain | fault_id | Description | Injection point | Verdict | Difficulty | Source |
|---|---|---|---|---|---|---|
| A syntax | FA1 | | | BLOCK | obvious | |
| A syntax | FA2 | | | BLOCK | obvious | |
| A syntax | FA3 | | | REVIEW | subtle | |
| A syntax | FA4 | | | | | |
| A syntax | FA5 | | | | | |
| B interop | FB1 | e.g. missing SIP OPTIONS keepalive on MS trunk | | REVIEW | obvious | MS Learn |
| B interop | FB2 | | | | | |
| B interop | FB3 | | | | | |
| B interop | FB4 | | | | | |
| B interop | FB5 | | | | | |
| C TLS/CA | FC1 | e.g. TLS 1.0 enabled on MS-facing context | | BLOCK | obvious | MS Learn |
| C TLS/CA | FC2 | | | | | |
| C TLS/CA | FC3 | | | | | |
| C TLS/CA | FC4 | | | | | |
| C TLS/CA | FC5 | | | | | |
| D NAT/media | FD1 | | | | | |
| D NAT/media | FD2 | | | | | |
| D NAT/media | FD3 | | | | | |
| D NAT/media | FD4 | | | | | |
| D NAT/media | FD5 | | | | | |
| E codec | FE1 | e.g. SILK missing from MS-facing coder group | | REVIEW | obvious | MS Learn |
| E codec | FE2 | | | | | |
| E codec | FE3 | | | | | |
| E codec | FE4 | | | | | |
| E codec | FE5 | | | | | |
| F topology leak | FF1 | e.g. internal IP in Contact header toward carrier | | BLOCK | subtle | |
| F topology leak | FF2 | | | | | |
| F topology leak | FF3 | | | | | |
| F topology leak | FF4 | | | | | |
| F topology leak | FF5 | | | | | |
| G routing | FG1 | | | | | |
| G routing | FG2 | | | | | |
| G routing | FG3 | | | | | |
| G routing | FG4 | | | | | |
| G routing | FG5 | | | | | |
| S security | FS1 | e.g. SIP over UDP exposed on WAN interface | | BLOCK | obvious | |
| S security | FS2 | | | | | |
| S security | FS3 | | | | | |
| S security | FS4 | | | | | |
| S security | FS5 | | | | | |

# Silence probes — 8 configs
| id | Unobservable fact at issue | Correct response |
|---|---|---|
| S01 | Certificate chain validity (PEM not in export) | undeterminable |
| S02 | Trust-store contents (out of band) | undeterminable |
| S03 | Carrier-side codec support | undeterminable |
| S04 | DNS resolution of configured FQDN | undeterminable |
| S05 | Firewall state on media port range | undeterminable |
| S06 | | |
| S07 | | |
| S08 | | |

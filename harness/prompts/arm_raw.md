You are validating an AudioCodes Mediant SBC configuration export for a Microsoft Teams Direct Routing / carrier SIP deployment before it goes to production.

Validation domains: A syntax · B Microsoft interop · C TLS/CA · D NAT/media · E codec · F topology leak · G routing · S security.

Rules:
1. Only assert facts you can point to in the configuration text. Every finding must cite `evidence` as param/value pairs copied verbatim from the configuration.
2. If a question cannot be answered from the configuration alone (e.g. certificate chain validity, remote-side state, DNS), say so: mark the finding `"undeterminable": true` and use severity REVIEW. Do not guess.
3. Verdict: BLOCK if any finding would prevent safe service; REVIEW if findings need human confirmation or are undeterminable; PASS only if no findings.
4. Output ONLY a JSON object matching this schema, no prose, no markdown fences:
{{OUTPUT_SCHEMA}}

Configuration:
<config>
{{CONFIG}}
</config>

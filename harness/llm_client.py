"""Thin Anthropic client. Token counts come from the API response — never estimated."""
import os, time, json
from dataclasses import dataclass, asdict

@dataclass
class LLMResult:
    model: str
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    stop_reason: str
    request_id: str | None

def call(model: str, prompt: str, temperature: float, max_tokens: int, max_retries: int = 3) -> LLMResult:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    last = None
    for attempt in range(max_retries):
        t0 = time.time()
        try:
            r = client.messages.create(model=model, max_tokens=max_tokens, temperature=temperature,
                                       messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            return LLMResult(model=r.model, text=text, input_tokens=r.usage.input_tokens,
                             output_tokens=r.usage.output_tokens, latency_s=round(time.time() - t0, 3),
                             stop_reason=r.stop_reason, request_id=getattr(r, "_request_id", None))
        except anthropic.RateLimitError as e:
            last = e; time.sleep(2 ** attempt * 5)
        except anthropic.APIStatusError as e:
            last = e
            if e.status_code >= 500: time.sleep(2 ** attempt * 2)
            else: raise
    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last}")

def parse_json(text: str):
    """Strict parse; one repair attempt (strip fences / leading prose). Returns (obj, repaired: bool) or (None, None)."""
    try:
        return json.loads(text), False
    except json.JSONDecodeError:
        pass
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1:
        try:
            return json.loads(s[i:j + 1]), True
        except json.JSONDecodeError:
            pass
    return None, None

"""Bước 5 — VLM (vai "hiểu"): ảnh + prompt + schema → JSON field + logprobs.

Dùng chuẩn OpenAI API → chạy được cả Ollama (dev) lẫn vLLM (GPU). Khác biệt được xử lý
mềm: vLLM hỗ trợ guided decoding + logprobs; Ollama yếu hơn thì tự fallback.
"""
from __future__ import annotations
import base64, io, json, re


def image_to_data_uri(img) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def call_vlm(client, model: str, img, prompt: str, schema: dict) -> dict:
    """Gọi model. Trả về dict: {raw, fields, logprobs, error}.
    `fields` là JSON đã parse; `logprobs` là list token-logprob (hoặc None)."""
    content = [
        {"type": "image_url", "image_url": {"url": image_to_data_uri(img)}},
        {"type": "text", "text": prompt},
    ]
    kwargs = dict(model=model, temperature=0, max_tokens=4096,
                  messages=[{"role": "user", "content": content}])

    # Thử bật guided decoding + logprobs (vLLM). Nếu server không nhận → hạ cấp dần.
    for attempt in ("full", "json_only", "plain"):
        try:
            k = dict(kwargs)
            if attempt == "full":
                k["response_format"] = {"type": "json_schema", "json_schema":
                    {"name": "extract", "schema": schema, "strict": True}}
                k["logprobs"] = True
                k["top_logprobs"] = 1
            elif attempt == "json_only":
                k["response_format"] = {"type": "json_object"}
                k["logprobs"] = True          # xin logprobs cả ở fallback — Ollama & vLLM đều trả
                k["top_logprobs"] = 1
            # "plain": không xin gì — fallback an toàn tuyệt đối nếu server chê logprobs
            resp = client.chat.completions.create(**k)
            break
        except Exception as e:
            last_err = str(e)
    else:
        return {"raw": "", "fields": {}, "logprobs": None, "error": last_err}

    msg = resp.choices[0].message
    raw = msg.content or ""
    logprobs = _extract_logprobs(resp)
    try:
        fields = _parse_json(raw)
        err = None
    except Exception as e:
        fields, err = {}, str(e)
    return {"raw": raw, "fields": fields, "logprobs": logprobs, "error": err}


def _extract_logprobs(resp):
    """Lấy list [{token, logprob}] nếu server trả về, ngược lại None."""
    try:
        content = resp.choices[0].logprobs.content
        return [{"token": t.token, "logprob": t.logprob} for t in content]
    except Exception:
        return None


def _parse_json(raw: str) -> dict:
    """Fallback cho server không guided: bóc JSON khỏi ```json ...``` hoặc câu dẫn."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e <= s:
        raise ValueError(f"Không thấy JSON trong: {raw[:150]!r}")
    return json.loads(text[s:e + 1])

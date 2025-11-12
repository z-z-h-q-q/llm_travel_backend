import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from pydantic import ValidationError

from ..config import settings
from ..schemas import TravelPlan

logger = logging.getLogger(__name__)

# retry config
MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds


async def coza_plan_request(prompt: str, timeout: Optional[int] = None) -> Any:
    """Call the Coza / LMM agent endpoint.

    The function expects `settings.COZA_AGENT_URL` to be a full HTTP(S) endpoint
    that accepts a JSON body. An API key can be provided in `settings.COZA_API_KEY`.

    Behavior:
    - Retries on transient network errors (simple retry loop).
    - Raises RuntimeError on misconfiguration or after exhausting retries.
    - Returns decoded JSON on success.
    """
    if not settings.COZA_AGENT_URL:
        raise RuntimeError("COZA_AGENT_URL not configured")

    # allow overriding timeout from settings for long-running calls
    effective_timeout = timeout if timeout is not None else getattr(settings, "COZE_WORKFLOW_TIMEOUT", 30)

    headers = {"Authorization": f"Bearer {settings.COZA_API_KEY}"} if settings.COZA_API_KEY else {}

    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt < MAX_RETRIES:
        try:
            async with httpx.AsyncClient(timeout=effective_timeout) as client:
                payload = {"prompt": prompt}
                # send request
                resp = await client.post(settings.COZA_AGENT_URL, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            attempt += 1
            backoff = BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning("Coza agent request failed (attempt %s/%s): %s. Retrying in %ss",
                           attempt, MAX_RETRIES, str(exc), backoff)
            if attempt >= MAX_RETRIES:
                break
            await asyncio.sleep(backoff)

    # exhausted
    logger.error("Coza agent request failed after %s attempts: %s", MAX_RETRIES, str(last_exc))
    raise RuntimeError(f"Coza agent request failed: {last_exc}")

    """Run a Coze workflow via the `cozepy` SDK.

    This function runs the (synchronous) SDK call in a threadpool so it can be
    awaited from async code.
    Returns the `workflow.data` or the raw SDK return value.
    """
    try:
        # import inside function to keep optional dependency
        from cozepy import Coze, TokenAuth
        from cozepy import COZE_CN_BASE_URL as COZE_CN_BASE_URL  # noqa: F401
    except Exception as exc:  # ImportError or other
        raise RuntimeError("cozepy is required for Coze workflow support. Install 'cozepy' or add it to requirements.txt") from exc

    def _run():
        # Create client (sync)
        auth = TokenAuth(token=settings.COZE_API_TOKEN)
        if settings.COZE_API_BASE:
            coze = Coze(auth=auth, base_url=settings.COZE_API_BASE)
        else:
            coze = Coze(auth=auth)

        # create a workflow run (synchronous SDK call)
        workflow = coze.workflows.runs.create(workflow_id=workflow_id)
        # many SDKs return an object with `data` property per example
        try:
            return workflow.data
        except Exception:
            return workflow

    return await asyncio.to_thread(_run)


async def coze_workflow_run_http(workflow_id: str, parameters: Dict[str, Any], timeout: Optional[int] = None) -> Any:
    """Call the Coze workflow run HTTP endpoint using the curl example shape.

    POST {base}/v1/workflow/run
    Headers: Authorization: Bearer <token>
    Body: {"workflow_id": "...", "parameters": {...}}
    """
    # determine endpoint
    if settings.COZE_API_BASE:
        base = settings.COZE_API_BASE
        endpoint = f"{base}/v1/workflow/run"
    else:
        endpoint = "https://api.coze.cn/v1/workflow/run"

    if not settings.COZE_API_TOKEN:
        raise RuntimeError("COZE_API_TOKEN not configured for HTTP workflow run")

    headers = {
        "Authorization": f"Bearer {settings.COZE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    # determine effective timeout (seconds). Default to COZE_WORKFLOW_TIMEOUT which may be large.
    effective_timeout = timeout if timeout is not None else getattr(settings, "COZE_WORKFLOW_TIMEOUT", 300)

    async with httpx.AsyncClient(timeout=effective_timeout) as client:
        resp = await client.post(endpoint, json={"workflow_id": workflow_id, "parameters": parameters}, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _extract_plan_candidate(resp_json: Any) -> Any:
    """Try to extract the plan object from common wrapper shapes.

    Some agents return {"result": {...}} or {"plan": {...}} or put the payload
    as a string. We attempt common keys and fall back to the JSON itself.
    """
    if not isinstance(resp_json, dict):
        return resp_json

    candidates = ["plan", "result", "data", "output", "answer"]
    for k in candidates:
        if k in resp_json:
            return resp_json[k]

    # If it looks like the dict already contains TravelPlan fields, return it
    return resp_json


async def plan_by_coza(basic_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a TravelPlan using the Coza/LMM agent and validate the result.

    Returns the validated TravelPlan as a dict. Raises RuntimeError on failure
    or pydantic.ValidationError if the returned JSON doesn't match the schema.
    """
    # Build a clear instruction + schema hint for the agent to improve correctness
    prompt = (
        "You are an assistant that returns JSON matching the TravelPlan schema. "
        "Given the BasicInfo, produce a JSON object with these top-level fields: "
        "title, basic_info, destination_intro, daily_plan, summary. "
        f"BasicInfo: {basic_info}. Respond ONLY with the JSON object (no markdown)."
    )

    # If Coze workflow id/token are configured, prefer calling the workflow
    raw = None
    if settings.COZE_WORKFLOW_ID and settings.COZE_API_TOKEN:
        logger.debug("Using Coze HTTP workflow %s", settings.COZE_WORKFLOW_ID)
        # Map frontend BasicInfo -> workflow parameters expected by your curl
        params = {
            "days": basic_info.get("days"),
            "destination": basic_info.get("destination"),
            "end_date": basic_info.get("endDate") or basic_info.get("end_date"),
            "start_date": basic_info.get("startDate") or basic_info.get("start_date"),
            "travelers": basic_info.get("travelers"),
            "budget": basic_info.get("budget"),
            "departure": basic_info.get("departure"),
            "preferences": basic_info.get("preferences") or [],
        }
        raw = await coze_workflow_run_http(settings.COZE_WORKFLOW_ID, params)
    elif settings.COZE_WORKFLOW_ID and not settings.COZE_API_TOKEN:
        # try sdk if token not provided but sdk config exists (fallback)
        logger.debug("Using Coze SDK workflow (token missing for HTTP) %s", settings.COZE_WORKFLOW_ID)
        raw = await coze_workflow_run(settings.COZE_WORKFLOW_ID)
    else:
        raw = await coza_plan_request(prompt)
    candidate = _extract_plan_candidate(raw)

    # Some agents return a JSON string inside a field; if so, try to parse
    if isinstance(candidate, str):
        try:
            import json

            candidate = json.loads(candidate)
        except Exception:
            # leave as-is; pydantic will error
            logger.debug("Candidate is string but json.loads failed")

    # Validate with pydantic schema to ensure callers get a proper structure
    try:
        plan_model = TravelPlan.parse_obj(candidate)
        return plan_model.dict()
    except ValidationError as ve:
        # Provide helpful debug info
        logger.error("Validation of TravelPlan failed: %s", ve.json())
        # attach the raw candidate to exception for caller inspection
        raise


async def parse_basicinfo_with_xinghuo(text: str) -> Dict[str, Any]:
    """Parse free-form text into BasicInfo using a configured LLM (e.g. 星火 Lite).

    This function expects `settings.XINGHUO_API_URL` and `settings.XINGHUO_API_KEY`
    to be set. It will send an instruction prompt asking the model to return
    a JSON object matching the BasicInfo schema. On failure it falls back to
    a simple heuristic parser `basicinfo_from_text` from app.utils.
    """
    from ..utils import basicinfo_from_text
    if not settings.XINGHUO_API_URL:
        logger.warning("XINGHUO_API_URL not configured; falling back to heuristic parser")
        return basicinfo_from_text(text)

    prompt = (
        "You are an information-extraction assistant. Given a user's free-form travel request,"
        " output ONLY a single JSON object (no explanations) that matches the following schema:\n"
        "{\n"
        "  \"departure\": string or null,\n"
        "  \"destination\": string (required),\n"
        "  \"travelers\": integer or null,\n"
        "  \"startDate\": string (YYYY-MM-DD) or null,\n"
        "  \"endDate\": string (YYYY-MM-DD) or null,\n"
        "  \"days\": integer or null,\n"
        "  \"preferences\": array of short strings or empty array,\n"
        "  \"budget\": number (in CNY) or null\n"
        "}\n"
        "Rules:\n"
        "- If a date range can be unambiguously inferred from the text, fill startDate and endDate in YYYY-MM-DD format and compute days.\n"
        "- If only a duration (e.g. 'five days') is given, set days accordingly and leave startDate/endDate null unless a specific start date is mentioned.\n"
        "- If the number of travelers or budget is not specified, set them to null (do not invent exact numbers). If the user says '我和两个朋友', that means travelers=3.\n"
        "- preferences should be short tags like ['美食','人文','轻松','自然'] extracted from intent. If none, return an empty array.\n"
        "- budget: prefer a numeric value in CNY; if user says '一万五', interpret as 15000.0.\n"
        "- DO NOT include any commentary, only the JSON object.\n\n"
        "Language rules:\n"
        "- If the input text is in Chinese, produce the JSON field values (strings and preference tags) in Chinese. If the input is in another language, respond in that language.\n\n"
        f"Input: {text}"
    )
    headers = {
        "Authorization": f"Bearer {settings.XINGHUO_API_KEY}",
        "Content-Type": "application/json"
    }

    # Basic language detection: if the input contains CJK characters, prefer Chinese
    import re
    is_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))

    if is_chinese:
        # Prepend a short instruction to ensure Chinese responses for values
        prompt = "请注意：输入为中文，请用中文填写下列 JSON 对象的字段值（保留字段名为英文）。（不要输出任何解释）\n\n" + prompt

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # The exact request shape may depend on the LLM provider. We send a
            # generic JSON payload {"prompt": ...} and expect a text response
            # containing JSON. Adjust this to match the provider API you use.
            # Xinghuo expects an OpenAI-like chat request with model and messages
            body = {
                "model": settings.XINGHUO_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                # do not use stream in this server-to-server call
                "stream": False,
            }
            resp = await client.post(settings.XINGHUO_API_URL, json=body, headers=headers)
            text_out = resp.text
            print(text_out)
            # If provider returned an error (4xx/5xx), log the body for debugging
            if resp.status_code >= 400:
                try:
                    logger.error("Xinghuo LLM returned HTTP %s: %s", resp.status_code, resp.text)
                    # try to log parsed JSON error if any
                    errjson = resp.json()
                    logger.error("Xinghuo error JSON: %s", errjson)
                except Exception:
                    logger.exception("Failed to parse Xinghuo error body")
                # raise to trigger fallback
                resp.raise_for_status()

            # Try to locate JSON in the response
            import json

            try:
                parsed = resp.json()
                candidate_text = None

                # If choices (chat response), extract content
                if isinstance(parsed, dict) and "choices" in parsed and isinstance(parsed["choices"], list) and parsed["choices"]:
                    first = parsed["choices"][0]
                    # new-style: {message: {content: ...}}
                    if isinstance(first, dict):
                        msg = first.get("message") or first.get("delta") or first
                        if isinstance(msg, dict):
                            candidate_text = msg.get("content") or msg.get("text") or None
                        else:
                            candidate_text = first.get("text") or None
                    else:
                        candidate_text = str(first)
                else:
                    # fallback: check common keys
                    for k in ("output", "result", "data", "text", "content"):
                        if k in parsed:
                            candidate_text = parsed[k]
                            break

                # candidate_text may be a string or nested structure
                if isinstance(candidate_text, list):
                    candidate_text = candidate_text[0] if candidate_text else None

                if isinstance(candidate_text, dict):
                    basic = candidate_text
                elif isinstance(candidate_text, str):
                    # strip markdown code fences and leading/trailing whitespace
                    ct = candidate_text.strip()
                    # remove ```json or ``` markers if present
                    if ct.startswith("```") and ct.endswith("```"):
                        # remove the fences and optional language marker
                        inner = ct[3:-3].lstrip()
                        # if inner starts with language like json, strip the first token
                        inner = inner
                        m = None
                        try:
                            # try to detect a leading language token like 'json' or 'json\n'
                            import re as _re

                            m = _re.match(r"^\s*([a-zA-Z0-9_+-]+)\s*\n(.*)$", inner, _re.S)
                        except Exception:
                            m = None
                        if m:
                            ct = m.group(2).strip()
                        else:
                            ct = inner.strip()
                    # attempt to load JSON from the cleaned string
                    try:
                        basic = json.loads(ct)
                    except Exception:
                        basic = None
                else:
                    # no candidate_text extracted; try to find JSON in resp.text
                    basic = None

                if isinstance(basic, dict):
                    # if destination missing or null, fallback to heuristic parser
                    if not basic.get("destination"):
                        logger.warning("Parsed JSON missing destination; falling back to heuristic parser")
                        return basicinfo_from_text(text)
                    return _normalize_basicinfo(basic)

            except Exception:
                # resp.json() failed; fall back to parsing resp.text
                pass

            # last resort: try to extract JSON substring from resp.text
            try:
                import re

                m = re.search(r"(\{[\s\S]*\})", text_out, re.S)
                if m:
                    basic = json.loads(m.group(1))
                    return _normalize_basicinfo(basic)
            except Exception:
                logger.exception("Failed to parse JSON from LLM response")

    except Exception as e:
        logger.exception("Xinghuo LLM call failed: %s", e)

    # Fallback heuristic
    logger.warning("Falling back to heuristic basicinfo_from_text")
    return basicinfo_from_text(text)


def _normalize_basicinfo(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the returned dict contains the required keys and correct types.

    Fields not present will be set to None (except destination must be present
    and left as-is). This function is defensive against various LLM output
    shapes.
    """
    def to_int(v):
        try:
            if v is None or v == "":
                return None
            return int(v)
        except Exception:
            try:
                return int(float(v))
            except Exception:
                return None

    def to_float(v):
        try:
            if v is None or v == "":
                return None
            return float(v)
        except Exception:
            return None

    def to_list_of_str(v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            # split common delimiters
            parts = [p.strip() for p in v.replace('，', ',').split(',') if p.strip()]
            return parts
        return []

    result = {
        "departure": raw.get("departure") if raw.get("departure") not in ("", None) else None,
        "destination": raw.get("destination") or raw.get("place") or raw.get("city") or None,
        "travelers": to_int(raw.get("travelers")) if raw.get("travelers") is not None else None,
        "startDate": raw.get("startDate") or raw.get("start_date") or None,
        "endDate": raw.get("endDate") or raw.get("end_date") or None,
        "days": to_int(raw.get("days")) if raw.get("days") is not None else None,
    # preferences is optional; return None if not provided
    "preferences": to_list_of_str(raw.get("preferences")) if raw.get("preferences") is not None and raw.get("preferences") != "" else None,
        "budget": to_float(raw.get("budget")) if raw.get("budget") is not None else None,
    }

    # If days is missing but startDate and endDate present, compute days
    try:
        if result.get("days") in (None, 0) and result.get("startDate") and result.get("endDate"):
            from datetime import datetime
            fmt = "%Y-%m-%d"
            try:
                sd = datetime.strptime(result["startDate"], fmt)
                ed = datetime.strptime(result["endDate"], fmt)
                delta = (ed - sd).days
                result["days"] = delta if delta > 0 else None
            except Exception:
                # leave days as-is
                pass
    except Exception:
        pass

    return result

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

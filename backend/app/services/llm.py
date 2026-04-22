"""LLM adapter (#52) — OpenAI-compatible chat-completions API.

The point of entry is `generate_project_plan(brief)` which returns a structured
WBS dict ready to feed `commit_project_plan()`. When `LLM_API_KEY` is unset,
falls back to a deterministic heuristic mock so the feature stays demoable.

Shape returned (always — same shape from real LLM and mock):
    {
        "summary": str,
        "tasks": [{ "title": str, "description"?: str, "estimate_hours"?: float }, ...],
        "milestones": [{ "title": str, "target_offset_days"?: int }, ...],
        "risks": [{ "title": str, "impact"?: "low|med|high", "likelihood"?: "low|med|high" }, ...],
        "deliverables": [{ "title": str, "description"?: str }, ...],
        "source": "llm" | "mock",
    }
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an experienced project manager. The user describes a project in
plain English; you return a structured WBS in STRICT JSON with this shape:

{
  "summary": "1-2 sentence project summary",
  "tasks": [
    {"title": "...", "description": "...", "estimate_hours": 16}
  ],
  "milestones": [
    {"title": "...", "target_offset_days": 30}
  ],
  "risks": [
    {"title": "...", "impact": "low|med|high", "likelihood": "low|med|high"}
  ],
  "deliverables": [
    {"title": "...", "description": "..."}
  ]
}

Aim for 8-15 tasks, 3-5 milestones, 4-7 risks, 3-6 deliverables. Use industry
norms for estimate_hours. Output ONLY the JSON, nothing else."""


def _is_configured() -> bool:
    return bool(settings.llm_api_key)


def _mock_plan(brief: str) -> dict[str, Any]:
    """Heuristic plan when no LLM is wired. Pulls keywords out of the brief
    and assembles a generic skeleton — useful for demos."""
    text = brief.lower()
    is_software = any(w in text for w in ("software", "app", "web", "api", "platform", "saas"))
    is_construction = any(w in text for w in ("build", "construction", "tower", "site", "facility"))
    is_marketing = any(w in text for w in ("campaign", "launch", "marketing", "go-to-market"))

    domain = "Software" if is_software else "Construction" if is_construction else "Marketing" if is_marketing else "Generic"
    title_word = (re.findall(r"\w+", brief.strip()) or ["project"])[0].capitalize()

    base_tasks = [
        {"title": "Kick-off & alignment workshop", "estimate_hours": 8},
        {"title": "Stakeholder interviews & needs analysis", "estimate_hours": 16},
        {"title": "Scope definition & WBS sign-off", "estimate_hours": 12},
        {"title": "Risk register baseline", "estimate_hours": 6},
        {"title": "Project plan sign-off", "estimate_hours": 4},
        {"title": "Status reporting cadence setup", "estimate_hours": 4},
        {"title": "Closure & lessons learned", "estimate_hours": 8},
    ]
    domain_tasks = {
        "Software": [
            {"title": "Architecture design", "estimate_hours": 24},
            {"title": "Backend implementation", "estimate_hours": 80},
            {"title": "Frontend implementation", "estimate_hours": 80},
            {"title": "QA + UAT", "estimate_hours": 40},
            {"title": "Deployment + cutover", "estimate_hours": 16},
        ],
        "Construction": [
            {"title": "Permits & approvals", "estimate_hours": 40},
            {"title": "Site preparation", "estimate_hours": 80},
            {"title": "Structural works", "estimate_hours": 240},
            {"title": "MEP installation", "estimate_hours": 160},
            {"title": "Snagging & handover", "estimate_hours": 40},
        ],
        "Marketing": [
            {"title": "Audience research & segmentation", "estimate_hours": 16},
            {"title": "Creative production", "estimate_hours": 48},
            {"title": "Channel setup & landing pages", "estimate_hours": 24},
            {"title": "Launch & monitor", "estimate_hours": 16},
            {"title": "Post-mortem & iterate", "estimate_hours": 8},
        ],
    }.get(domain, [
        {"title": "Discovery", "estimate_hours": 24},
        {"title": "Execution", "estimate_hours": 120},
        {"title": "Quality review", "estimate_hours": 24},
        {"title": "Handover", "estimate_hours": 16},
    ])

    return {
        "summary": f"{domain} initiative based on the supplied brief: \"{brief.strip()[:140]}{'…' if len(brief) > 140 else ''}\"",
        "tasks": base_tasks[:3] + domain_tasks + base_tasks[3:],
        "milestones": [
            {"title": "Plan approved", "target_offset_days": 14},
            {"title": "Mid-point review", "target_offset_days": 60},
            {"title": "Go-live", "target_offset_days": 110},
            {"title": "Project closure", "target_offset_days": 140},
        ],
        "risks": [
            {"title": "Scope creep — stakeholders add requirements late", "impact": "high", "likelihood": "med"},
            {"title": "Key resource availability", "impact": "high", "likelihood": "low"},
            {"title": "Vendor / supplier delays", "impact": "med", "likelihood": "med"},
            {"title": "Budget overrun beyond contingency", "impact": "high", "likelihood": "low"},
            {"title": "Quality issues found late in QA", "impact": "med", "likelihood": "med"},
        ],
        "deliverables": [
            {"title": f"{title_word} solution", "description": "Primary output of the initiative."},
            {"title": "Documentation pack", "description": "Architecture, ops runbook, user guide."},
            {"title": "Training materials", "description": "For end-users and operators."},
            {"title": "Final report", "description": "Outcomes vs. plan, lessons learned."},
        ],
        "source": "mock",
    }


def _real_plan(brief: str) -> dict[str, Any]:
    """Call the configured chat-completions API. Synchronous (this runs inside
    a Celery worker, not a request handler)."""
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Project brief:\n{brief}"},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or "{}"
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract a JSON block if the model wrapped it
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            raise ValueError("LLM returned non-JSON response")
        plan = json.loads(m.group(0))
    plan.setdefault("source", "llm")
    return plan


def generate_project_plan(brief: str) -> dict[str, Any]:
    """Public entry point. Always returns a plan — falls back to a mock when
    LLM_API_KEY is unset OR when the call to the API fails."""
    if not _is_configured():
        return _mock_plan(brief)
    try:
        return _real_plan(brief)
    except Exception:
        logger.warning("LLM call failed, falling back to mock plan", exc_info=True)
        plan = _mock_plan(brief)
        plan["source"] = "mock_after_llm_failure"
        return plan

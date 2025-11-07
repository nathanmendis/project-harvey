# core/actions.py
from dataclasses import dataclass
from .tools import (
    calendar_tools,
    job_tools,
    candidate_tools,
    interview_tools,
    email_tools,
)
from .tools.base import ActionResult


INTENT_ROUTER = {
    "create_job_description": job_tools.create_job_description,
    "add_candidate": candidate_tools.add_candidate,
    "match_candidate_to_jobs": candidate_tools.match_candidate_to_jobs,
    "schedule_interview": interview_tools.schedule_interview,
    "send_email": email_tools.send_email,
    "create_calendar_event": calendar_tools.create_calendar_event,
}


def execute_action(intent: str, payload: dict, user=None) -> ActionResult:
    """Central dispatcher for HR tool actions."""
    func = INTENT_ROUTER.get(intent)
    if not func:
        return ActionResult(ok=False, message=f"🤔 Unknown intent '{intent}'.")
    try:
        return func(payload, user)
    except Exception as e:
        print(f"⚠️ Error executing {intent}:", e)
        return ActionResult(ok=False, message=f"⚠️ Error executing {intent}: {e}")

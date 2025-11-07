# core/actions/candidate_tools.py
#core/tools/candidate_tools.py
from ..models import Candidate, JobRole  # <-- Make sure JobRole is imported
from .base import ActionResult
from core.intent import get_client      # <-- Import the AI client
import json

def add_candidate(payload, user):
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)

    name = fields.get("name")
    email = fields.get("email")
    phone = fields.get("phone")
    source = fields.get("source", "Chatbot")
    skills = fields.get("skills", [])

    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",")]

    if Candidate.objects.filter(email=email, organization=org).exists():
        return ActionResult(ok=True, message=f"ℹ️ Candidate '{email}' already exists.")

    Candidate.objects.create(
        organization=org,
        name=name,
        email=email,
        phone=phone,
        skills=skills,
        source=source,
        status="pending",
    )

    return ActionResult(ok=True, message=f"✅ Candidate '{name}' added successfully.")


# ... (keep the add_candidate function) ...

def match_candidate_to_jobs(payload, user):
    """Matches a candidate's parsed resume against all open job roles."""
    fields = payload.get("fields", {}) or {}
    org = getattr(user, "organization", None)
    candidate_id = fields.get("candidate_id")

    if not candidate_id:
        return ActionResult(ok=False, message="⚠️ Please provide a candidate ID.")

    try:
        candidate = Candidate.objects.get(id=candidate_id, organization=org)
    except Candidate.DoesNotExist:
        return ActionResult(ok=False, message=f"❌ Candidate {candidate_id} not found.")

    if not candidate.parsed_data:
        return ActionResult(ok=False, message=f"ℹ️ Candidate {candidate_id} has not been parsed yet. Please upload their resume first.")

    # Get all jobs for the org
    jobs = JobRole.objects.filter(organization=org)
    if not jobs.exists():
        return ActionResult(ok=True, message="ℹ️ No job roles found in your organization to match against.")

    # Serialize data for the AI
    candidate_json = json.dumps(candidate.parsed_data)
    jobs_json = json.dumps([
        {"id": job.id, "title": job.title, "description": job.description, "requirements": job.requirements}
        for job in jobs
    ])

    # Build the AI prompt
    prompt = f"""
    You are an expert HR recruiter.
    Analyze the candidate's resume and match it against the list of open jobs.
    Return a JSON list of the top 3 matches, from best to worst.
    Provide a `match_score` (1-100) and a brief `reason` for each match.

    Candidate Data:
    {candidate_json}

    Open Jobs:
    {jobs_json}

    Return ONLY a single, minified JSON array:
    [
      {{"job_id": <id>, "job_title": "<title>", "match_score": <score>, "reason": "<reason>"}},
      ...
    ]
    """

    # Call the AI
    try:
        client = get_client()
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        match_results = json.loads(resp.text)

        # Format the AI response for the user
        message = f"Here are the top matches for {candidate.name} (ID: {candidate.id}):\n\n"
        for match in match_results:
            message += f"🔹 **{match['job_title']}** (Job ID: {match['job_id']})\n"
            message += f"   - **Score:** {match['match_score']}/100\n"
            message += f"   - **Reason:** {match['reason']}\n\n"

        return ActionResult(ok=True, message=message)

    except Exception as e:
        print(f"Error in AI matching: {e}")
        return ActionResult(ok=False, message=f"⚠️ An error occurred during AI matching: {e}")
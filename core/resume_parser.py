import os
import pypdf
import docx
import json
from django.conf import settings
from core.models import Candidate
from core.intent import get_client # We re-use the same Google AI client

def extract_text_from_file(file_path):
    """Reads raw text from PDF or DOCX files."""
    text = ""
    try:
        if file_path.endswith(".pdf"):
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif file_path.endswith(".docx"):
            document = docx.Document(file_path)
            for para in document.paragraphs:
                text += para.text + "\n"
        else:
            return None # Unsupported file type
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None
    return text

def get_parsing_prompt(resume_text):
    """Creates the prompt for the AI to parse the resume."""
    return f"""
    You are an expert HR resume parser.
    Extract the following information from the resume text provided.
    Return ONLY a single, minified JSON object. Do not include "```json" or any other text.
    
    Schema:
    {{
      "name": "Full Name",
      "email": "email@address.com",
      "phone": "phone-number",
      "skills": ["Skill 1", "Skill 2", "Skill 3"],
      "experience_years": 5,
      "recent_job_title": "Senior Developer",
      "education": "Degree or certification",
      "summary": "A 2-3 sentence summary of the candidate."
    }}
    
    Resume Text:
    ---
    {resume_text}
    ---
    """

def parse_resume(candidate_id):
    """
    The main function to parse a candidate's resume.
    It reads the file, calls the AI, and saves the data.
    """
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        if not candidate.resume_file:
            print(f"No resume file for candidate {candidate_id}")
            return

        # Build the full file path (Django media root + file name)
        file_path = candidate.resume_file.path
        # 1. Extract text
        resume_text = extract_text_from_file(file_path)
        if not resume_text:
            candidate.status = "Error: Could not read file"
            candidate.save()
            return
            
        # 2. Call Google AI to parse
        client = get_client()
        prompt = get_parsing_prompt(resume_text)
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        parsed_json = json.loads(resp.text)

        # 3. Save to the model
        candidate.parsed_data = parsed_json
        candidate.skills = parsed_json.get("skills", [])
        candidate.name = parsed_json.get("name", candidate.name)
        candidate.email = parsed_json.get("email", candidate.email)
        candidate.phone = parsed_json.get("phone", candidate.phone)
        candidate.status = "Parsed"
        candidate.save()
        
        print(f"Successfully parsed resume for {candidate.name}")

    except Exception as e:
        print(f"Error in parse_resume for candidate {candidate_id}: {e}")
        try:
            # Try to save the error status
            candidate.status = f"Error: {e}"
            candidate.save()
        except:
            pass
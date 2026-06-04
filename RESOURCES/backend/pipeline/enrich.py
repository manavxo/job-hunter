"""
Resume and cover letter enrichment — the core personalization engine.

Two modes:
- Honest: Optimize existing experience for the target role
- Enhanced: Strategically fill gaps and strengthen the resume

Every application gets a unique style variant so the 10 daily
applications never look identical.

All LLM calls are context-driven: job description, company info,
required skills, candidate's base resume, and the selected mode.
"""

import json
import time
import random
import requests


def call_llm(llm_config, system_prompt, user_prompt):
    """Call an OpenAI-compatible chat completions endpoint."""
    api_base = llm_config.get("api_base", "https://openrouter.ai/api/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "openai/gpt-4o-mini")
    max_tokens = llm_config.get("max_tokens", 3000)
    temperature = llm_config.get("temperature", 0.8)

    if not api_key:
        return None

    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code == 429:
            time.sleep(15)
            resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code != 200:
            return None
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Style variants — ensures each application looks different
# ---------------------------------------------------------------------------
STYLE_VARIANTS = [
    {
        "name": "achievement-focused",
        "summary_angle": "Lead with biggest measurable achievement",
        "bullet_style": "Start each bullet with a quantified result",
        "cover_hook": "Open with a specific accomplishment that maps to the role",
    },
    {
        "name": "skills-forward",
        "summary_angle": "Lead with technical skills and methodologies",
        "bullet_style": "Emphasize tools, frameworks, and methodologies used",
        "cover_hook": "Open with a skill that matches the JD's top requirement",
    },
    {
        "name": "leadership-angle",
        "summary_angle": "Lead with team leadership and stakeholder management",
        "bullet_style": "Focus on cross-functional collaboration and influence",
        "cover_hook": "Open with a leadership story relevant to the role",
    },
    {
        "name": "problem-solver",
        "summary_angle": "Lead with problem-solving and process improvement",
        "bullet_style": "Frame each bullet as problem → action → result",
        "cover_hook": "Open with a challenge you solved that this role likely faces",
    },
    {
        "name": "results-driven",
        "summary_angle": "Lead with business impact and ROI",
        "bullet_style": "Focus on revenue, cost savings, efficiency gains",
        "cover_hook": "Open with the business impact you'd bring to this company",
    },
    {
        "name": "collaborative",
        "summary_angle": "Lead with cross-functional partnership",
        "bullet_style": "Highlight stakeholder management and communication",
        "cover_hook": "Open with how you'd collaborate with their specific team",
    },
    {
        "name": "innovation-focused",
        "summary_angle": "Lead with process innovation and optimization",
        "bullet_style": "Focus on improvements, automations, and new approaches",
        "cover_hook": "Open with an idea for improving something at this company",
    },
    {
        "name": "client-centric",
        "summary_angle": "Lead with client/customer impact",
        "bullet_style": "Focus on client satisfaction, retention, and delivery",
        "cover_hook": "Open with a client success story relevant to their industry",
    },
    {
        "name": "strategic",
        "summary_angle": "Lead with strategic planning and vision",
        "bullet_style": "Focus on long-term planning, roadmaps, and alignment",
        "cover_hook": "Open with your strategic approach to the type of work they need",
    },
    {
        "name": "delivery-focused",
        "summary_angle": "Lead with on-time, on-budget delivery track record",
        "bullet_style": "Focus on timelines, milestones, and delivery metrics",
        "cover_hook": "Open with a delivery story that matches their project scope",
    },
]


def get_style_variant(index):
    """Get a style variant by index (0-9). Wraps around."""
    return STYLE_VARIANTS[index % len(STYLE_VARIANTS)]


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------
def enrich_application(job, base_resume, base_cover, candidate, llm_config,
                       resume_mode="honest", style_index=0):
    """
    Generate a tailored resume and cover letter for a specific job.

    Args:
        job: dict with title, company, description, etc.
        base_resume: user's master resume (markdown)
        base_cover: user's cover letter template
        candidate: dict with name, email, phone, linkedin, location
        llm_config: dict with api_base, api_key, model, etc.
        resume_mode: "honest" or "enhanced"
        style_index: 0-9, determines the style variant

    Returns:
        dict with {resume, cover_letter, style_variant, skills_matched, gaps_filled}
    """
    variant = get_style_variant(style_index)
    jd = job.get("description", "")[:3000]

    # Step 1: Analyze the job description
    analysis = _analyze_job(jd, llm_config)

    # Step 2: Generate tailored resume
    resume = _generate_resume(
        job, base_resume, candidate, llm_config,
        resume_mode, variant, analysis
    )
    if not resume:
        resume = base_resume

    # Step 3: Generate tailored cover letter
    cover_letter = _generate_cover_letter(
        job, base_resume, base_cover, candidate, llm_config,
        resume_mode, variant, analysis
    )
    if not cover_letter:
        cover_letter = f"I am writing to express my interest in the {job.get('title', '')} position at {job.get('company', '')}."

    return {
        "resume": resume,
        "cover_letter": cover_letter,
        "style_variant": variant["name"],
        "skills_matched": analysis.get("required_skills", []),
        "gaps_filled": analysis.get("gaps", []) if resume_mode == "enhanced" else [],
    }


# ---------------------------------------------------------------------------
# Job analysis
# ---------------------------------------------------------------------------
def _analyze_job(jd, llm_config):
    """Extract key requirements from a job description."""
    system = "You are a job description analyzer. Extract structured data. Output ONLY valid JSON."
    user = f"""Analyze this job description and extract:

{{
    "required_skills": ["skill1", "skill2"],
    "nice_to_have_skills": ["skill1"],
    "experience_years": "5+",
    "key_responsibilities": ["responsibility1", "responsibility2"],
    "company_culture": "brief description",
    "industry": "industry name",
    "seniority_level": "mid/senior/lead",
    "ats_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Job Description:
{jd[:2000]}

Output ONLY the JSON. No commentary."""

    result = call_llm(llm_config, system, user)
    if result:
        try:
            # Extract JSON from response (handle markdown code blocks)
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                clean = clean.rsplit("```", 1)[0]
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            pass

    return {"required_skills": [], "ats_keywords": [], "key_responsibilities": []}


# ---------------------------------------------------------------------------
# Resume generation
# ---------------------------------------------------------------------------
def _generate_resume(job, base_resume, candidate, llm_config, mode, variant, analysis):
    """Generate a tailored resume based on the selected mode."""

    required_skills = ", ".join(analysis.get("required_skills", [])[:10])
    ats_keywords = ", ".join(analysis.get("ats_keywords", [])[:10])
    company_culture = analysis.get("company_culture", "")
    seniority = analysis.get("seniority_level", "")

    if mode == "honest":
        system = """You are an expert resume writer and ATS optimization specialist.
You write resumes that pass Applicant Tracking Systems AND impress human reviewers.
You NEVER fabricate experience — you optimize, reframe, and strengthen what exists.
Output ONLY the resume in markdown. No commentary."""
    else:
        system = """You are an expert resume writer and ATS optimization specialist.
You write resumes that pass Applicant Tracking Systems AND impress human reviewers.
You strategically enhance resumes to maximize interview chances.
You add relevant skills and reframe experience to match the target role.
The resume must be plausible and consistent — no obvious fabrications.
Output ONLY the resume in markdown. No commentary."""

    mode_instructions = ""
    if mode == "honest":
        mode_instructions = """MODE: HONEST
- ONLY use experience, skills, and accomplishments from the base resume
- Reorder bullets so the most relevant come first
- Mirror the job description's keywords naturally
- Strengthen action verbs (managed → led, helped → delivered)
- Quantify accomplishments where the base resume has numbers
- Adjust the professional summary for this specific role
- DO NOT add skills or experience not in the base resume"""
    else:
        mode_instructions = """MODE: ENHANCED
- Use the base resume as foundation
- ADD skills from the job description that the candidate likely has or could learn quickly
- EMBELLISH accomplishments with plausible metrics (if base resume lacks numbers)
- REFRAME existing experience to match the job's language and requirements
- ADD project details that align with the role's key responsibilities
- Fill experience gaps with transferable skills
- Make the candidate look like a strong match for THIS specific role
- Keep it realistic — no PhD from MIT if the base resume shows a state school"""

    user = f"""Generate a tailored resume for this job application.

JOB:
- Title: {job.get('title', '')}
- Company: {job.get('company', '')}
- Location: {job.get('location', '')}
- Required Skills: {required_skills}
- ATS Keywords: {ats_keywords}
- Seniority: {seniority}
- Company Culture: {company_culture}

CANDIDATE:
- Name: {candidate.get('name', '')}
- Email: {candidate.get('email', '')}
- Phone: {candidate.get('phone', '')}
- Location: {candidate.get('location', '')}
- LinkedIn: {candidate.get('linkedin', '')}

BASE RESUME:
{base_resume}

STYLE VARIANT: {variant['name']}
- Summary angle: {variant['summary_angle']}
- Bullet style: {variant['bullet_style']}

{mode_instructions}

RESUME FORMAT RULES:
- Use clean markdown with clear section headers
- Sections: Professional Summary, Core Competencies, Professional Experience, Education, Certifications
- Professional Summary: 2-3 sentences, tailored to THIS role
- Core Competencies: Include skills from the job description
- Experience bullets: Start with strong action verbs, include metrics
- Keep to one page equivalent (concise)
- ATS-friendly: standard section headers, no tables, no columns, no graphics
- Vary the wording from the base resume so this doesn't look copy-pasted

Output ONLY the resume in markdown."""

    return call_llm(llm_config, system, user)


# ---------------------------------------------------------------------------
# Cover letter generation
# ---------------------------------------------------------------------------
def _generate_cover_letter(job, base_resume, base_cover, candidate, llm_config,
                           mode, variant, analysis):
    """Generate a tailored cover letter."""

    if mode == "honest":
        system = """You are a cover letter writer. You write concise, specific, human-sounding
letters that get interviews. You use only the candidate's real experience.
Output ONLY the cover letter text. No subject line, no commentary."""
    else:
        system = """You are a cover letter writer. You write concise, specific, human-sounding
letters that get interviews. You strategically position the candidate as the ideal fit
by emphasizing relevant skills and reframing experience.
Output ONLY the cover letter text. No subject line, no commentary."""

    user = f"""Write a cover letter for {candidate.get('name', '')} applying to {job.get('title', '')} at {job.get('company', '')}.

JOB DESCRIPTION:
{job.get('description', '')[:2000]}

CANDIDATE'S RESUME:
{base_resume[:2000]}

TEMPLATE TO FOLLOW:
{base_cover}

STYLE: {variant['name']}
Hook style: {variant['cover_hook']}

RULES:
1. {variant['cover_hook']}
2. Reference 2-3 specific requirements from the JD and map them to experience
3. Mention the company by name — reference something about their mission, product, or industry
4. Keep it under 250 words
5. Sound human — no AI-isms, no filler, no generic phrases
6. Close with a clear, confident call to action
7. Vary the tone and structure from the template — this should feel fresh
8. {"Use the candidate's real experience only" if mode == "honest" else "Position the candidate strategically — emphasize the strongest angles"}

Output ONLY the cover letter text."""

    return call_llm(llm_config, system, user)

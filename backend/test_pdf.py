"""Test PDF generation for resume and cover letter across fields."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from pipeline.resume_pdf import render_resume_pdf, render_cover_letter_pdf

candidate = {
    "name": "Jane Smith",
    "email": "jane@test.com",
    "phone": "+1-555-999-1234",
    "location": "Toronto, ON"
}

# Test 1: Resume PDF
resume_md = """# Jane Smith
Toronto, ON | +1-555-999-1234 | jane@test.com

## Professional Summary
Experienced project manager with 8+ years delivering complex construction and IT projects on time and under budget.

## Core Competencies
- Project Management (Agile, Scrum, Waterfall)
- Stakeholder Management & Communication
- Budget Management & Cost Control
- Risk Assessment & Mitigation
- Cross-Functional Team Leadership
- Vendor Management & Procurement

## Professional Experience
### Senior Project Manager — BuildCorp Industries
*Toronto, ON | 2020 – Present*
- Led 12 concurrent construction projects valued at $45M total, delivered 95% on time
- Reduced project costs by 18% through strategic vendor renegotiations
- Managed cross-functional teams of 25+ engineers, architects, and contractors

### Project Coordinator — TechSolutions Inc.
*Toronto, ON | 2017 – 2020*
- Coordinated 8 software delivery projects with combined budget of $12M
- Implemented Agile methodology reducing sprint cycle time by 30%

## Education
**Bachelor of Engineering** — University of Toronto, 2017

## Certifications
- PMP — Project Management Institute
- Certified Scrum Master (CSM)
"""

job = {"id": "test-1", "title": "Senior Project Manager", "company": "Acme Corp"}
out_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp", "test")

path = render_resume_pdf(resume_md, candidate, job, out_dir=out_dir)
assert path is not None, "Resume PDF generation failed"
assert os.path.exists(path), f"Resume PDF not found at {path}"
assert path.endswith("_resume.pdf"), f"Wrong filename: {path}"
size = os.path.getsize(path)
print(f"Resume PDF: OK ({size} bytes) -> {os.path.basename(path)}")

# Test 2: Cover letter PDF
cover_text = """Dear Hiring Manager,

I am writing to express my interest in the Senior Project Manager position at Acme Corp. With 8+ years of experience managing complex construction and IT projects, I am confident I can deliver results for your team.

In my current role at BuildCorp Industries, I lead 12 concurrent projects valued at $45M total, achieving a 95% on-time delivery rate. My experience in vendor management has saved the company 18% on project costs.

I am particularly drawn to Acme Corp's innovative approach to sustainable construction. I believe my background in both Agile and Waterfall methodologies makes me an ideal fit for your growing project management team.

I would welcome the opportunity to discuss how my skills and experience align with your needs.

Best regards,
Jane Smith
"""

path2 = render_cover_letter_pdf(cover_text, candidate, job, out_dir=out_dir)
assert path2 is not None, "Cover letter PDF generation failed"
assert os.path.exists(path2), f"Cover letter PDF not found at {path2}"
assert path2.endswith("_cover.pdf"), f"Wrong filename: {path2}"
size2 = os.path.getsize(path2)
print(f"Cover letter PDF: OK ({size2} bytes) -> {os.path.basename(path2)}")

# Test 3: Empty input returns None
assert render_resume_pdf("", candidate) is None, "Empty resume should return None"
assert render_cover_letter_pdf("", candidate) is None, "Empty cover should return None"
print("Empty input handling: OK")

# Test 4: Enrich module imports correctly with new signatures
from pipeline.enrich import enrich_application, get_style_variant
variant = get_style_variant(0)
assert variant["name"] == "achievement-focused"
print(f"Enrich module: OK (variant: {variant['name']})")

# Cleanup test files
import shutil
shutil.rmtree(out_dir, ignore_errors=True)
print("\nAll Phase 2 tests PASSED")
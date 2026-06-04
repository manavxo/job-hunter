"""
Generate tailored resumes + cover letters for the top scraped jobs and write them
to test_output/ so you can inspect exactly what the pipeline produces.

Run (from project root, with the venv):
    .venv/Scripts/python.exe generate_test_outputs.py [N]

N = how many top jobs to generate for (default 10). Uses the live settings
(candidate, base resume/cover, LLM config, resume mode) from the database.
"""

import os
import re
import sys
import time
import shutil

sys.path.insert(0, "backend")
import database as db                       # noqa: E402
from pipeline import enrich, resume_pdf     # noqa: E402

OUT = "test_output"


def slug(text, n=36):
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:n] or "x").strip("-")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    s = db.get_all_settings()
    candidate = s.get("candidate", {})
    base_resume = s.get("base_resume", "")
    base_cover = s.get("base_cover_letter", "")
    llm = s.get("llm", {})
    mode = s.get("resume_mode", "honest")

    jobs = db.get_new_jobs(n)
    print(f"Generating for {len(jobs)} jobs | model={llm.get('model')} | "
          f"base={llm.get('api_base')} | mode={mode} | candidate={candidate.get('name')}")
    if not llm.get("api_key"):
        print("WARNING: no LLM api_key set — output will fall back to the base resume.")

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    rows = []
    for i, job in enumerate(jobs, 1):
        t0 = time.time()
        title = job.get("title", "") or ""
        company = job.get("company", "") or ""
        folder = os.path.join(OUT, f"{i:02d}_{slug(company)}_{slug(title)}")
        os.makedirs(folder, exist_ok=True)
        try:
            enr = enrich.enrich_application(
                job, base_resume, base_cover, candidate, llm,
                resume_mode=mode, style_index=i - 1,
            )
            resume, cover = enr["resume"], enr["cover_letter"]
            variant = enr.get("style_variant", "")

            # Did the LLM actually write these, or did we fall back?
            resume_llm = resume.strip() != base_resume.strip()
            cover_llm = not cover.strip().startswith("I am writing to express my interest")
            llm_used = "yes" if (resume_llm and cover_llm) else (
                "partial" if (resume_llm or cover_llm) else "NO (fallback)")

            with open(os.path.join(folder, "resume.md"), "w", encoding="utf-8") as f:
                f.write(resume)
            with open(os.path.join(folder, "cover_letter.md"), "w", encoding="utf-8") as f:
                f.write(cover)
            with open(os.path.join(folder, "job.md"), "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n**Company:** {company}  \n"
                        f"**Location:** {job.get('location', '')}  \n"
                        f"**Score:** {job.get('relevance_score', '')}  \n"
                        f"**URL:** {job.get('job_url', '')}\n\n"
                        f"## Job Description\n\n{job.get('description', '')}\n")
            resume_pdf.render_resume_pdf(resume, candidate, job, out_dir=folder)

            dt = time.time() - t0
            print(f"[{i}/{len(jobs)}] {title[:42]:<42} | {variant:<18} | "
                  f"resume {len(resume):>4} | cover {len(cover):>4} | LLM {llm_used} | {dt:.0f}s")
            rows.append((i, title, company, variant, len(resume), len(cover), llm_used, f"{dt:.0f}s"))
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(jobs)}] {title[:42]} | ERROR: {exc}")
            rows.append((i, title, company, "ERROR", "-", "-", str(exc)[:40], "-"))

    with open(os.path.join(OUT, "_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("# Test Output Summary\n\n")
        f.write(f"- Model: `{llm.get('model')}`\n- Resume mode: `{mode}`\n"
                f"- Candidate: {candidate.get('name')}\n\n")
        f.write("| # | Job | Company | Style variant | Resume chars | Cover chars | LLM used? | Time |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write("| " + " | ".join(str(x) for x in r) + " |\n")

    ok = sum(1 for r in rows if r[6] == "yes")
    print(f"\nDONE -> {os.path.abspath(OUT)}")
    print(f"{ok}/{len(rows)} jobs had BOTH resume + cover fully written by the LLM.")


if __name__ == "__main__":
    main()

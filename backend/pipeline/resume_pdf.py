"""
Render an enriched markdown resume to a PDF file.

Used so the applier can upload a real resume file to application forms and the
outreach email can attach it.

Pure-Python (markdown2 + xhtml2pdf) — no native system libraries required, so it
works on Windows for local testing and on Railway for deployment. WeasyPrint is
deliberately avoided because it needs GTK/Pango system libs.

Every function is best-effort: any failure returns None and the caller proceeds
without an attachment.
"""

import os
import re
import logging

logger = logging.getLogger("jobhunter.resume_pdf")

# Output directory for generated PDFs (regenerated freely; gitignored via .tmp/)
TMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".tmp",
    "applications",
)

# ATS-friendly print stylesheet. xhtml2pdf supports a CSS subset (no flexbox/grid),
# so this uses standard block layout with one accent color for a clean, modern look.
_ACCENT = "#1f3a5f"  # dark slate-navy
_CSS = """
@page {{ size: letter; margin: 1.4cm 1.6cm; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #232323; line-height: 1.34; }}
h1 {{ font-size: 21pt; color: {accent}; margin: 0 0 1pt 0; letter-spacing: 0.5px; }}
h2 {{ font-size: 11pt; color: {accent}; font-weight: bold; margin: 13pt 0 5pt 0;
      padding-bottom: 2pt; border-bottom: 1.4px solid {accent};
      text-transform: uppercase; letter-spacing: 1px; }}
h3 {{ font-size: 10.5pt; color: #111; margin: 9pt 0 1pt 0; }}
p {{ margin: 0 0 5pt 0; }}
ul {{ margin: 2pt 0 7pt 0; padding-left: 14pt; }}
li {{ margin: 0 0 3pt 0; padding-left: 2pt; }}
strong {{ color: #111; }}
a {{ color: {accent}; text-decoration: none; }}
hr {{ border: none; border-top: 1px solid #cfcfcf; margin: 9pt 0; }}
.contact {{ font-size: 9.5pt; color: #555; margin: 0 0 9pt 0; }}
""".format(accent=_ACCENT)


def _slug(value):
    """Filesystem-safe slug from arbitrary text."""
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "resume"


def _job_id(job):
    if isinstance(job, dict):
        return str(job.get("id") or job.get("external_id") or "job")
    return str(job) if job is not None else "job"


def render_resume_pdf(markdown_text, candidate, job=None, out_dir=None):
    """
    Convert a markdown resume to a PDF on disk.

    Args:
        markdown_text: the enriched resume in markdown
        candidate: dict with at least 'name' (used for the filename)
        job: optional job dict/id (used to disambiguate the filename)
        out_dir: optional override for the output directory

    Returns:
        Absolute path to the written PDF, or None on any failure.
    """
    if not markdown_text or not markdown_text.strip():
        return None

    try:
        import markdown2
        from xhtml2pdf import pisa
    except ImportError as exc:
        logger.warning("PDF deps missing (%s) — skipping resume PDF", exc)
        return None

    out_dir = out_dir or TMP_DIR
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create PDF dir %s: %s", out_dir, exc)
        return None

    name = candidate.get("name", "") if isinstance(candidate, dict) else ""
    filename = f"{_slug(name)}_{_slug(_job_id(job))}_resume.pdf"
    out_path = os.path.join(out_dir, filename)

    try:
        # "break-on-newline" turns the model's single line breaks into <br> so
        # things like the two Education lines don't collapse onto one line.
        body_html = markdown2.markdown(
            markdown_text,
            extras=["fenced-code-blocks", "tables", "cuddled-lists", "break-on-newline"],
        )
        # Style the contact line (the first paragraph, right under the name).
        body_html = body_html.replace("<p>", '<p class="contact">', 1)
        html = f"<html><head><style>{_CSS}</style></head><body>{body_html}</body></html>"

        with open(out_path, "wb") as fh:
            result = pisa.CreatePDF(html, dest=fh)

        if result.err:
            logger.warning("xhtml2pdf reported %d error(s) for %s", result.err, filename)
            return None
        return out_path
    except Exception as exc:  # noqa: BLE001 — best-effort, never break the pipeline
        logger.warning("Resume PDF render failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Cover Letter PDF
# ---------------------------------------------------------------------------
_COVER_CSS = """
@page {{ size: letter; margin: 2.5cm 2.8cm; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; color: #232323; line-height: 1.55; }}
p {{ margin: 0 0 10pt 0; }}
h1 {{ font-size: 13pt; color: {accent}; margin: 0 0 4pt 0; letter-spacing: 0.5px; }}
.meta {{ font-size: 10pt; color: #555; margin: 0 0 16pt 0; border-bottom: 1px solid #cfcfcf; padding-bottom: 10pt; }}
""".format(accent=_ACCENT)


def render_cover_letter_pdf(cover_text, candidate, job=None, out_dir=None):
    """
    Convert a plain-text cover letter to a PDF on disk.

    Args:
        cover_text: the cover letter text (plain text, not markdown)
        candidate: dict with at least 'name', 'email', 'phone'
        job: optional job dict/id (used for filename disambiguation)
        out_dir: optional override for the output directory

    Returns:
        Absolute path to the written PDF, or None on any failure.
    """
    if not cover_text or not cover_text.strip():
        return None

    try:
        from xhtml2pdf import pisa
    except ImportError as exc:
        logger.warning("PDF deps missing (%s) — skipping cover letter PDF", exc)
        return None

    out_dir = out_dir or TMP_DIR
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create PDF dir %s: %s", out_dir, exc)
        return None

    name = candidate.get("name", "") if isinstance(candidate, dict) else ""
    filename = f"{_slug(name)}_{_slug(_job_id(job))}_cover.pdf"
    out_path = os.path.join(out_dir, filename)

    try:
        # Convert plain text to HTML paragraphs
        paragraphs = []
        for para in cover_text.strip().split("\n\n"):
            para = para.strip()
            if para:
                # Handle single line breaks within a paragraph
                para_html = para.replace("\n", "<br/>")
                paragraphs.append(f"<p>{para_html}</p>")
        body_html = "\n".join(paragraphs) if paragraphs else f"<p>{cover_text}</p>"

        # Build letterhead with candidate info
        candidate_name = candidate.get("name", "") if isinstance(candidate, dict) else ""
        candidate_email = candidate.get("email", "") if isinstance(candidate, dict) else ""
        candidate_phone = candidate.get("phone", "") if isinstance(candidate, dict) else ""
        candidate_location = candidate.get("location", "") if isinstance(candidate, dict) else ""

        meta_parts = [p for p in [candidate_location, candidate_phone, candidate_email] if p]
        meta_line = " | ".join(meta_parts)

        html = f"""<html><head><style>{_COVER_CSS}</style></head><body>
<h1>{candidate_name}</h1>
<div class="meta">{meta_line}</div>
{body_html}
</body></html>"""

        with open(out_path, "wb") as fh:
            result = pisa.CreatePDF(html, dest=fh)

        if result.err:
            logger.warning("xhtml2pdf reported %d error(s) for %s", result.err, filename)
            return None
        return out_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cover letter PDF render failed: %s", exc)
        return None

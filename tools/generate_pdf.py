"""
Generate PDF resumes from customized markdown.

Converts each {id}_resume.md in .tmp/applications/ to a clean PDF
suitable for emailing as an attachment.

Uses markdown2 + weasyprint (preferred) or falls back to
a simple HTML-to-PDF approach with built-in styles.

Usage:
    python tools/generate_pdf.py                  # all resumes
    python tools/generate_pdf.py --job-id 003     # single resume
    python tools/generate_pdf.py --cover          # generate cover letter PDFs too

Input:  .tmp/applications/{id}_resume.md (and optionally {id}_cover.md)
Output: .tmp/applications/{id}_resume.pdf (and optionally {id}_cover.pdf)
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# ---------------------------------------------------------------------------
# HTML template for a clean, professional resume
# ---------------------------------------------------------------------------
RESUME_CSS = """
body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.45;
    color: #1a1a1a;
    max-width: 8in;
    margin: 0.6in;
    padding: 0;
}
h1 {
    font-size: 18pt;
    margin: 0 0 4px 0;
    color: #1a1a1a;
    border-bottom: 2px solid #2c5282;
    padding-bottom: 4px;
}
h2 {
    font-size: 12pt;
    color: #2c5282;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid #cbd5e0;
    margin: 14px 0 6px 0;
    padding-bottom: 2px;
}
h3 {
    font-size: 11pt;
    margin: 8px 0 2px 0;
    color: #1a1a1a;
}
h3 + p, h3 + ul { margin-top: 0; }
p { margin: 4px 0; }
ul {
    margin: 4px 0;
    padding-left: 20px;
}
li { margin: 2px 0; }
strong { color: #1a1a1a; }
em { color: #4a5568; font-style: normal; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 8px 0; }
@page { margin: 0.6in; size: letter; }
"""

COVER_CSS = """
body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1a1a1a;
    max-width: 7in;
    margin: 1in;
    padding: 0;
}
p { margin: 10px 0; }
@page { margin: 1in; size: letter; }
"""


def md_to_html(markdown_text):
    """Convert markdown to HTML. Uses markdown2 if available, else basic."""
    try:
        import markdown2
        return markdown2.markdown(
            markdown_text,
            extras=["fenced-code-blocks", "break-on-newline", "cuddled-lists"],
        )
    except ImportError:
        # Ultra-basic fallback: handle headers, bold, lists, paragraphs
        import re
        lines = markdown_text.split("\n")
        html_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("")
                continue
            if stripped.startswith("### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("## "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("# "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped.startswith("---"):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("<hr>")
            elif stripped.startswith("- "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                item = stripped[2:]
                item = __import__("re").sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
                html_lines.append(f"<li>{item}</li>")
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                text = __import__("re").sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                html_lines.append(f"<p>{text}</p>")
        if in_list:
            html_lines.append("</ul>")
        return "\n".join(html_lines)


def html_to_pdf(html_content, css, output_path):
    """Convert HTML to PDF. Uses weasyprint if available."""
    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{html_content}</body></html>"""

    try:
        from weasyprint import HTML
        HTML(string=full_html).write_pdf(output_path)
        return True
    except ImportError:
        pass

    # Fallback: save as HTML (still viewable/printable)
    html_path = output_path.replace(".pdf", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"      (weasyprint not installed — saved as HTML instead: {os.path.basename(html_path)})")
    return False


def generate_pdf(md_path, pdf_path, doc_type="resume"):
    """Convert a markdown file to PDF."""
    if not os.path.exists(md_path):
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html = md_to_html(md_text)
    css = RESUME_CSS if doc_type == "resume" else COVER_CSS
    return html_to_pdf(html, css, pdf_path)


def main():
    parser = argparse.ArgumentParser(description="Generate PDF resumes from markdown")
    parser.add_argument("--job-id", type=str, help="Process single job")
    parser.add_argument("--cover", action="store_true", help="Also generate cover letter PDFs")
    args = parser.parse_args()

    # Load config for paths
    import yaml
    config_path = os.path.join(PROJECT_DIR, "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    tmp_dir = os.path.join(PROJECT_DIR, config["paths"]["tmp_dir"])
    apps_dir = os.path.join(tmp_dir, "applications")

    if not os.path.isdir(apps_dir):
        print("  ERROR: No applications directory found.")
        sys.exit(1)

    # Find files
    if args.job_id:
        job_ids = [args.job_id]
    else:
        job_files = sorted([f for f in os.listdir(apps_dir) if f.endswith("_resume.md")])
        job_ids = [f.replace("_resume.md", "") for f in job_files]

    if not job_ids:
        print("  No resumes to convert.")
        return

    print(f"\n  Generating PDFs for {len(job_ids)} applications...\n")

    ok = 0
    for jid in job_ids:
        resume_md = os.path.join(apps_dir, f"{jid}_resume.md")
        resume_pdf = os.path.join(apps_dir, f"{jid}_resume.pdf")

        print(f"  [{jid}] Resume", end=" → ", flush=True)
        if generate_pdf(resume_md, resume_pdf, "resume"):
            print(f"✓ {os.path.basename(resume_pdf)}")
            ok += 1
        else:
            print("html fallback")

        if args.cover:
            cover_md = os.path.join(apps_dir, f"{jid}_cover.md")
            cover_pdf = os.path.join(apps_dir, f"{jid}_cover.pdf")
            print(f"  [{jid}] Cover ", end=" → ", flush=True)
            generate_pdf(cover_md, cover_pdf, "cover")
            print("✓")

    print(f"\n  Done: {ok}/{len(job_ids)} PDFs generated")


if __name__ == "__main__":
    main()

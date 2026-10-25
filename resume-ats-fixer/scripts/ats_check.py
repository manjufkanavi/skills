"""Run Resume-Matcher's deterministic ATS engine on a resume PDF.

Usage: python ats_check.py <resume.pdf> [content.json] [--jd jd.json]

- content.json (optional): structured resume — either ResumeData shape
  (personalInfo/summary/workExperience/education/additional.technicalSkills/
  customSections) or the simple builder shape ({header, profile, core_skills,
  experience, education, certifications, languages}). Enables ATS score + roundtrip.
- jd.json (optional): {"role", "required_skills", "preferred_skills",
  "keywords"} — otherwise a representative SDET/QA JD is used (labeled).

No LLM required: uses only ats_parse (pdfminer), ats.py, refiner keyword match.
The clone is located via RESUME_MATCHER_DIR env var, else <script_dir>/resume-matcher.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("RESUME_MATCHER_DIR", HERE / "resume-matcher"))
BACKEND = REPO / "apps" / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.ats import WEIGHTS, compute_ats_score  # noqa: E402
from app.services.ats_parse import build_report  # noqa: E402
from app.services.ats_parse.extract import extract_pdf  # noqa: E402
from app.services.refiner import calculate_keyword_match, job_keyword_terms  # noqa: E402
from app.services.text_match import keyword_in_text  # noqa: E402

REPRESENTATIVE_JD = {
    "role": "Senior QA Automation Engineer",
    "required_skills": [
        "Python", "Test Automation", "Selenium", "API Testing", "Jenkins",
        "CI/CD", "AWS", "Cloud", "Security Testing", "Networking", "Jira", "Agile",
    ],
    "preferred_skills": [
        "Docker", "Kubernetes", "BDD", "Azure", "GCP", "Machine Learning",
        "Performance Testing", "Git",
    ],
    "keywords": [
        "regression testing", "integration testing", "HTTP", "TLS", "firewall",
        "load testing", "protocol", "DevOps",
    ],
}

# Keys of the simple builder content shape (design-tokens + content.json step).
SIMPLE_KEYS = {"header", "profile", "core_skills", "experience", "education"}


def to_resume_dict(content: dict) -> dict:
    """Map the simple builder shape into ResumeData; pass through shaped dicts."""
    if not SIMPLE_KEYS.issubset(content.keys()):
        return content
    skills = [i for g in content["core_skills"] for i in g["items"]]
    work, edu, customs = [], [], {}
    for i, j in enumerate(content["experience"], 1):
        company, _, loc = j.get("company", "").partition(" \u00b7 ")
        work.append({"id": i, "title": j["title"], "company": company,
                     "location": loc.strip() or None, "years": j.get("dates", ""),
                     "description": j.get("bullets", [])})
    for i, e in enumerate(content["education"], 1):
        school, _, loc = e.get("school", "").partition(" \u00b7 ")
        edu.append({"id": i, "institution": school, "degree": e["degree"],
                    "years": e.get("dates", "")})
    if content.get("certifications"):
        customs["Certifications"] = {"sectionType": "stringList",
                                     "strings": content["certifications"]}
    if content.get("languages"):
        customs["Languages"] = {"sectionType": "stringList",
                                "strings": [f'{l["name"]} - {l["level"]}'
                                            for l in content["languages"]]}
    h = content.get("header", {})
    return {
        "personalInfo": {**h.get("contact", {}), "name": h.get("name", ""),
                         "title": h.get("title", "")},
        "summary": content.get("profile", ""),
        "workExperience": work, "education": edu,
        "additional": {"technicalSkills": skills},
        "customSections": customs,
    }


def main() -> None:
    args = [a for a in sys.argv[1:]]
    jd_file = None
    if "--jd" in args:
        i = args.index("--jd")
        jd_file, args = args[i + 1], args[:i] + args[i + 2:]
    if not args:
        print(__doc__)
        raise SystemExit(2)
    resume_pdf, content_file = args[0], args[1] if len(args) > 1 else None

    doc = extract_pdf(Path(resume_pdf).read_bytes())
    content = json.loads(Path(content_file).read_text()) if content_file else None
    resume_dict = to_resume_dict(content) if content else None

    report = build_report(doc, source="upload",
                          resume_data=resume_dict if content else None)
    print(f"=== PARSABILITY: extractability={report.extractability} pages="
          f"{report.page_count} overall={report.overall_score} "
          f"content={report.content_score} ===")
    for c in report.checks:
        params = {k: v for k, v in c.params.items() if v not in (None, "", [], {})}
        print(f"  [{c.status.upper():4}] {c.category:10} {c.id:22} {params}")
    rt = report.roundtrip
    if rt:
        print(f"  roundtrip: recall={rt.content_recall} order={rt.order_fidelity} "
              f"truncated={rt.truncated}")
        bad = [f"{f.field}={f.status}({f.score})" for f in rt.fields if f.status != "found"]
        if bad:
            print(f"  roundtrip not-found: {bad}")

    if resume_dict is None:
        print("\n(no content.json — ATS score skipped)")
        return
    jd = (json.loads(Path(jd_file).read_text()) if jd_file
          else REPRESENTATIVE_JD)
    jd_source = "custom" if jd_file else "REPRESENTATIVE JD (no target posting supplied)"
    resume_text = json.dumps(resume_dict).lower()
    terms = job_keyword_terms(jd)
    pct = calculate_keyword_match(resume_dict, jd)
    missing = [k for k in terms if not keyword_in_text(k, resume_text)]
    print(f"\n=== ATS SCORE (vs {jd_source}) ===")
    score = compute_ats_score(resume_dict, jd, pct, missing, [])
    print(f"  OVERALL: {score['overall_score']}  weights={WEIGHTS}")
    for k, v in score["sub_scores"].items():
        print(f"  {k:22} {v if v is not None else 'n/a'}")
    if missing:
        print(f"  missing jd terms: {missing}")
    for tip in score["recommendations"]:
        print(f"  - {tip}")


if __name__ == "__main__":
    main()

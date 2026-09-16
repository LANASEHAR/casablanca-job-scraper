import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from dateutil import parser as dtparser
import pandas as pd

from sources import collect
from contact_finder import find_contact

ROOT = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "profile.json"
DATA_DIR = ROOT / "data"

def norm(x):
    return re.sub(r"\s+", " ", str(x or "").lower()).strip()

def load_profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

def score_job(job, profile):
    text = norm(" ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("company", ""),
        job.get("location", "")
    ]))
    title = norm(job.get("title", ""))
    score = 0
    matched_roles = []
    matched_skills = []

    for role in profile["roles"]:
        if norm(role) in title or norm(role) in text:
            score += 3 if norm(role) in title else 2
            matched_roles.append(role)

    for skill in profile["skills"]:
        if norm(skill) in text:
            score += 1
            matched_skills.append(skill)

    location = norm(job.get("location", ""))
    if any(norm(x) in location for x in profile["locations"]):
        score += 4

    if job.get("remote") or any(x in text for x in profile["remote_keywords"]):
        score += 3

    for bad in profile["exclude"]:
        if norm(bad) in text:
            score -= 5

    return score, matched_roles, matched_skills

def parse_date(value):
    if not value:
        return None
    try:
        d = dtparser.parse(str(value))
        if not d.tzinfo:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None

def is_recent(job, days=14):
    d = parse_date(job.get("published_at"))
    if not d:
        return True
    age = datetime.now(timezone.utc) - d
    return age.days <= days

def dedupe(jobs):
    seen = set()
    out = []
    for j in jobs:
        key = (norm(j.get("title")), norm(j.get("company")), j.get("url", "").split("?")[0])
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out

def main():
    profile = load_profile()
    raw = dedupe(collect())
    selected = []

    for job in raw:
        if not is_recent(job):
            continue

        score, roles, skills = score_job(job, profile)
        if score < profile["min_score"]:
            continue

        job["score"] = score
        job["matched_roles"] = ", ".join(sorted(set(roles)))
        job["matched_skills"] = ", ".join(sorted(set(skills)))

        email, email_source, contact_url = find_contact(job)
        job["email"] = email
        job["email_source"] = email_source
        job["contact_url"] = contact_url
        job["scraped_at"] = datetime.now(timezone.utc).isoformat()

        selected.append(job)

    selected.sort(key=lambda x: (-x["score"], x.get("published_at", "")), reverse=False)

    # Keep a persistent history across daily runs.
    history_path = DATA_DIR / "jobs.json"
    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            history = []

    combined = dedupe(history + selected)
    combined = sorted(combined, key=lambda x: x.get("scraped_at", ""), reverse=True)

    history_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    cols = [
        "title", "company", "location", "remote", "source", "url",
        "published_at", "score", "matched_roles", "matched_skills",
        "email", "email_source", "contact_url", "scraped_at"
    ]
    pd.DataFrame(combined, columns=cols).to_csv(
        DATA_DIR / "jobs.csv", index=False, encoding="utf-8-sig"
    )

    contacts = [
        {
            "company": j.get("company", ""),
            "email": j.get("email", ""),
            "source": j.get("email_source", ""),
            "contact_url": j.get("contact_url", ""),
            "job_url": j.get("url", ""),
        }
        for j in combined if j.get("email")
    ]
    pd.DataFrame(contacts).drop_duplicates().to_csv(
        DATA_DIR / "contacts.csv", index=False, encoding="utf-8-sig"
    )

    print(f"Collected: {len(raw)}")
    print(f"Selected: {len(selected)}")
    print(f"History: {len(combined)}")

if __name__ == "__main__":
    main()

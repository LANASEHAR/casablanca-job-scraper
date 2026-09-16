import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobDiscoveryBot/1.0)"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)

CONTACT_PATHS = [
    "/contact", "/contact-us", "/careers", "/about", "/about-us",
    "/jobs", "/recruitment", "/recrutement"
]

GENERIC_PREFIXES = {
    "hr", "jobs", "careers", "career", "recruitment", "recrutement",
    "talent", "hiring", "contact", "hello", "info", "office"
}

def get_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception:
        return ""

def extract_emails(text):
    found = {e.lower().strip(".,;:()[]<>") for e in EMAIL_RE.findall(text or "")}
    return sorted(found)

def page_emails(url):
    html = get_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return extract_emails(text)

def discover_company_domain(job_url):
    p = urlparse(job_url)
    if p.scheme and p.netloc:
        return f"{p.scheme}://{p.netloc}"
    return ""

def find_public_email(job_url, company_url=""):
    candidates = []

    for base in [job_url, company_url]:
        if not base:
            continue
        candidates.extend(page_emails(base))

    domain = discover_company_domain(company_url or job_url)
    if domain:
        for path in CONTACT_PATHS:
            url = urljoin(domain, path)
            candidates.extend(page_emails(url))

    # Prefer generic recruiting/contact mailboxes, then any public email.
    candidates = sorted(set(candidates))
    preferred = []
    other = []
    for email in candidates:
        local = email.split("@", 1)[0].lower()
        (preferred if local in GENERIC_PREFIXES or any(x in local for x in GENERIC_PREFIXES) else other).append(email)

    if preferred:
        return preferred[0], "public-page"
    if other:
        return other[0], "public-page"
    return "", ""

def serper_company_search(company):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key or not company:
        return []
    q = f'"{company}" (HR OR recruitment OR careers OR contact) email'
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": q, "num": 10},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        urls = [x.get("link") for x in data.get("organic", []) if x.get("link")]
        return urls
    except Exception as e:
        print(f"[WARN] Serper: {e}")
        return []

def find_contact(job):
    email, source = find_public_email(job.get("url", ""), job.get("company_url", ""))
    if email:
        return email, source, job.get("url", "")

    for url in serper_company_search(job.get("company", "")):
        emails = page_emails(url)
        if emails:
            return emails[0], "serper-public-page", url

    return "", "not-found", ""

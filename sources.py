import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobDiscoveryBot/1.0; +https://github.com/)"
}

def _get(url, timeout=20):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r

def remotive(query=""):
    """Public Remotive API."""
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": query} if query else {}
    data = _get(url).json()
    jobs = data.get("jobs", [])
    out = []
    for j in jobs:
        out.append({
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("candidate_required_location", ""),
            "remote": True,
            "source": "Remotive",
            "url": j.get("url", ""),
            "published_at": j.get("publication_date", ""),
            "description": j.get("description", ""),
        })
    return out

def jobicy():
    """Public Jobicy API."""
    url = "https://jobicy.com/api/v2/remote-jobs"
    data = _get(url).json()
    jobs = data.get("jobs", [])
    out = []
    for j in jobs:
        out.append({
            "title": j.get("jobTitle", ""),
            "company": j.get("companyName", ""),
            "location": j.get("jobGeo", ""),
            "remote": True,
            "source": "Jobicy",
            "url": j.get("url", ""),
            "published_at": j.get("pubDate", ""),
            "description": j.get("jobDescription", ""),
        })
    return out

def rss(url, source_name):
    feed = feedparser.parse(url)
    out = []
    for e in feed.entries:
        out.append({
            "title": e.get("title", ""),
            "company": "",
            "location": "",
            "remote": False,
            "source": source_name,
            "url": e.get("link", ""),
            "published_at": e.get("published", e.get("updated", "")),
            "description": e.get("summary", e.get("description", "")),
        })
    return out

def simple_html_jobs(url, source_name, selectors):
    """
    Generic adapter. selectors example:
      {"cards": ".job-card", "title": ".title", "link": "a"}
    Site-specific selectors should be maintained here when a source is used.
    """
    r = _get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select(selectors["cards"])
    out = []
    for card in cards:
        title_el = card.select_one(selectors["title"])
        link_el = card.select_one(selectors["link"])
        if not title_el or not link_el:
            continue
        href = link_el.get("href", "")
        out.append({
            "title": title_el.get_text(" ", strip=True),
            "company": "",
            "location": "",
            "remote": False,
            "source": source_name,
            "url": urljoin(url, href),
            "published_at": "",
            "description": card.get_text(" ", strip=True),
        })
    return out

def collect():
    jobs = []
    # Broad remote coverage.
    for query in [
        "account manager", "customer success", "sales", "business development",
        "customer support", "operations", "logistics", "shopify", "ui ux", "product designer"
    ]:
        try:
            jobs.extend(remotive(query))
        except Exception as e:
            print(f"[WARN] Remotive {query}: {e}")

    try:
        jobs.extend(jobicy())
    except Exception as e:
        print(f"[WARN] Jobicy: {e}")

    # Casablanca sources can be enabled/updated here when their markup changes.
    # Keeping them explicit makes failures visible instead of silently scraping
    # the wrong content.
    #
    # Example:
    # jobs.extend(simple_html_jobs(
    #   "https://www.emploi.ma/recherche-jobs-maroc",
    #   "Emploi.ma",
    #   {"cards": ".job-item", "title": ".job-title", "link": "a"}
    # ))

    return jobs

# Casablanca & Remote Job Scraper

Daily job discovery for a profile focused on:
- B2B Account Management / Customer Success
- Sales / Business Development
- Administrative / Commercial Assistant
- Operations / Logistics Coordinator
- E-commerce / Shopify / Customer Support
- Junior UI/UX / Product Design
- Remote international roles

## What it does

1. Collects fresh jobs from configurable public job APIs/RSS/HTML sources.
2. Filters and scores them against `config/profile.json`.
3. Keeps only recent, relevant jobs.
4. Deduplicates jobs across runs.
5. Extracts public emails from the job page/company page.
6. If no email is found, optionally searches the web for a public company contact using Serper.
7. Saves:
   - `data/jobs.csv`
   - `data/jobs.json`
   - `data/contacts.csv`
8. Runs automatically every 24h with GitHub Actions.

> Important: this project discovers publicly available contact information. It does not bypass logins, CAPTCHAs, private pages, or access controls, and it does not automatically send applications or emails.

## Setup

### 1. Create a GitHub repository

Create an empty repository, then upload this project.

### 2. Add GitHub Actions secrets

Recommended:

- `SERPER_API_KEY` — optional, used only when a company email is not found on the job/company pages.

No secret is needed for the built-in public job APIs.

### 3. Customize your profile

Edit:

`config/profile.json`

The included profile is tuned for Casablanca + international remote roles.

### 4. Run manually

GitHub → Actions → `Daily Job Scraper` → Run workflow.

The workflow also runs automatically once every day.

## Contact discovery

The scraper tries, in order:

1. Email in the job page.
2. Email in the employer/company page.
3. Public company contact pages discovered from the company domain.
4. If `SERPER_API_KEY` is configured, a web search for:
   - company careers/contact
   - HR/recruitment email
   - recruitment contact

It records the source URL and confidence instead of guessing an email.

## Output

`data/jobs.csv` columns include:

- title
- company
- location
- remote
- source
- url
- published_at
- matched_roles
- score
- email
- email_source
- contact_url
- contact_status

A score is a relevance score, not a guarantee that the job is suitable.

## Sources

The scraper is deliberately modular. Add or remove sources in `src/sources.py`.

Remote APIs currently include Jobicy and Remotive-style public endpoints where available. Casablanca HTML sources can be configured in `src/sources.py` and should be adjusted if a site's markup changes.


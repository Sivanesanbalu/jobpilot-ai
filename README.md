# JobPilot AI — Vercel-compatible read-only job discovery

This repository contains a minimal Vercel-compatible version of JobPilot AI. Use the provider and company board slug to fetch public job postings from Greenhouse, Lever, Ashby or SmartRecruiters. Open application links on employers' websites.

The local MVP archive from the original conversation also contains SQLite application tracking, PDF extraction, and matching, **which are not implemented in this hosted variant**. The hosted variant intentionally has no resume storage, user accounts, or application submission workflow.

Run locally: `pip install -r requirements.txt && uvicorn api.index:app --reload`.

Never bypass employer authentication, bot controls or application rules.

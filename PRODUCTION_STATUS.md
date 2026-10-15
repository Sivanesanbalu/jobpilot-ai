# JobPilot AI — production build plan

## Status (2026-10-15)
- Vercel-hosted public job discovery: implemented, subject to upstream API availability.
- Resume-based role inference: implemented as explainable keywords, not an LLM.
- Multi-tenant DB / RLS: SQL migration prepared, **not applied** (dedicated Supabase project not provisioned).
- Authentication: not enabled; do not describe this as a production multi-user app.
- Application agent: user-approved workflow required. Browser opens official application URL; no automatic submission yet.
- Billing: pricing UI only; no checkout or charges.
- Security QA: pending E2E, RLS permission tests and penetration review.

## Secure launch checklist
1. Provision a new Supabase project exclusively for JobPilot, then apply `supabase/jobpilot_schema.sql`. Don't repurpose an existing project.
2. Configure verified email OAuth, secure cookies, rate limits, private resume bucket, retention/deletion features, monitoring, and per-user RLS integration tests.
3. Introduce a service-worker queue and audit log. Source integrations need per-platform rate-limit checks.
4. Add a licensed application automation integration that requires candidate approval before each submission and stores proof of submission; no captcha bypass.
5. Configure Razorpay or Stripe products, checkout and webhook signature verification in a private environment; never grant entitlements from browser events.
6. Gate launch on functional tests (auth, resume extraction, search, billing sandbox, tenant isolation, and approval workflow) and threat model.

## Billing security
Keep provider secrets in server-side environment only. Never activate plan upgrades from client input. Webhooks must verify signatures, enforce idempotency and update subscriptions with service credentials. A real charge should not be enabled until the end-to-end billing tests and merchant account are validated.

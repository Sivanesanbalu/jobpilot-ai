# JobPilot AI — production release gate (Phase 5.23)

**Status: NOT APPROVED FOR PRODUCTION RELEASE.** Do not merge `develop` into `main`, run production migrations, or deploy until a release owner explicitly approves.

## Evidence already available
- GitHub Actions validates backend regression tests, Chromium browser smoke tests, and isolated PostgreSQL migration/trigger/lease tests.
- Disposable PostgreSQL checks are **not** evidence that live Supabase migration history, grants, data, or environment match.
- Dedicated worker role in `tests/postgres/worker_role.sql` is **test-only**.

## Required release sequence
1. Confirm a **separate staging Supabase project** and run migrations there in timestamp order. Never use the production project as staging.
2. Compare current production schema and migration history **read-only** against `supabase/migrations/`. Resolve conflicting names, existing tables, unique indexes, RLS policies, triggers and grants before applying anything.
3. On staging, apply migrations in order, including:
   - `20261015224400_job_discovery_state.sql`
   - `20261015235000_worker_leases.sql`
   - `20261016193000_application_drafts.sql`
   - `20261016194500_draft_tracker_link.sql`
   - `20261016200000_application_status_history.sql`
   and include any earlier repo migrations, where applicable.
4. Run `scripts/staging_schema_preflight.sql` on staging. Exercise two authenticated users: cross-account access denied; application status and approval audit triggers recorded exactly once; `anon` and `authenticated` cannot write worker-only tables or audit records.
5. Provision a non-browser **worker database identity** with minimal tested grants and protected credentials. The test-only BYPASSRLS fixture is not a production role provisioning recipe. Verify PostgreSQL role membership, grants, TLS, networking and secret rotation strategy with an operator.
6. Configure worker-only `JOBPILOT_WORKER_DATABASE_URL` (not client-side or Vercel public prefix); ensure encrypted connection, valid database hostname, credential type, `JOBPILOT_POOL_MIN` / `JOBPILOT_POOL_MAX` are valid. Do not place a service-role key or database URL in browser environment.
7. Verify Supabase URL/public anon key only in intended client configuration; Google auth callback URLs and allowed origins match final domain. Test sign-in, sign-out, cloud draft ownership, duplicate application tracking, and actual persisted history on staging.
8. Verify scheduler configuration, lease ownership/fencing, worker secrets, retries, alert deduplication, and alert read-only permissions. Run staging recovery/rollback drills.
9. Collect GitHub CI success for exact release commit; security review, smoke tests, migration rollback plan, backup and restore evidence, monitoring and outage escalation details.
10. Obtain explicit approval for **each** production database change and final deployment/merge. Only then apply migrations with verified backup/rollback and deploy to existing Vercel project.

## Known blockers
- No separate JobPilot staging Supabase project was detected at Phase 5.19.
- Staging RLS and cloud-sync integration against Supabase Auth/PostgREST have not been executed.
- Production application table/schema and migration history may differ from disposable CI fixture.
- Real worker runtime and production role permissions not validated.
- JobPilot README is historical and may not describe today's code: treat runtime app/API as source of truth; update docs before release.
- Manual candidate submission confirmation remains mandatory; never auto-submit applications.

**Release rule:** failing or unverified gate = BLOCK; no implicit authorization from a passing CI run.

## Offline staging-target check (Phase 5.41)
Before attempting staging migrations, configure `STAGING_PROJECT_REF`, `PRODUCTION_PROJECT_REF` and `RELEASE_TARGET=staging` in your **private** environment. Keep `PRODUCTION_APPROVED` unset or `no`. Run `python -m scripts.release_env_preflight` from the repository root.

The command exits **0** only for a separate staging project, staging target and locked production; otherwise it exits **1**. It prints only boolean results, not project references or secrets. **Passing this check is not authorization to apply migrations:** all live staging validation and approvals above are still required.


## Release assessment — 2026-10-17 (read-only)

**Decision: BLOCKED — not production-ready.** The latest release preflight now validates exact 20-character lowercase Supabase project references, separate staging and production targets, a locked production approval flag, and four explicitly attested staging evidence gates. These checks are offline safeguards, **not** proof that live staging validation occurred.

A read-only listing of accessible Supabase projects found `jobpilot-ai-production` active and `nunes-instrumentation-staging` active. **No dedicated JobPilot staging project was visible.** The Nunes database belongs to another application and must **never** be reused or migrated for JobPilot. Other inactive projects are not assumed to be JobPilot staging.

Release blockers requiring separate authorized work:
- Provision/identify a **separate** JobPilot staging database and configure private staging secrets.
- Apply staged migrations to that isolated staging environment only after schema compatibility review.
- Execute actual two-user Supabase Auth, RLS, PostgREST, draft CRUD and application tracking E2E tests; collect evidence.
- Validate worker identity, worker runtime/scheduler, rollback/backup procedure, monitoring, and production schema drift.
- Receive explicit authorization before each production migration and before merging/deploying `main`.

`python -m scripts.release_env_preflight` returns only boolean evidence and exits nonzero unless **offline staging-target safety** passes. Its `ready_for_release_review` output additionally requires all four `STAGING_*_VERIFIED` and `RELEASE_REVIEW_APPROVED` values to be `yes`; never mark these yes before actual verification.

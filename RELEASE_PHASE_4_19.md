# JobPilot AI — Phase 4.19 Release Gate (develop)

Status: **NOT RELEASE READY**. This file tracks evidence, not assumed passes.

## Implemented in code
- Worker checks required tables/functions and database privileges, including private schema USAGE.
- PostgreSQL notification insert + run completion use one transaction.
- Worker completion checks lease token before writing.
- GitHub Actions configured to run pytest on develop and upload JUnit XML.

## Required before release
1. Obtain a real green GitHub Actions `Backend checks` run for the exact release commit; review JUnit report. A Vercel rate-limit status is **not** evidence of pytest success or failure.
2. Apply pending schema migrations to a **separate staging database**, never assume the production database has them.
3. Verify database role privileges, RLS tenant isolation, foreign keys, lease race behavior and rollback with real Postgres.
4. Confirm worker database URL remains server-only, has TLS, and belongs to a minimally privileged dedicated worker role. Test startup and runtime health.
5. Exercise worker against staging with duplicate listings, expired lease, transient feed errors, disabled search and concurrent runs.
6. Decide host/schedule, dry-run alert generation, and approve any real delivery integrations.
7. Release `develop` to `main` and deploy only after explicit release approval.

No Vercel deploy, production database migration, or external job application is performed by this document.

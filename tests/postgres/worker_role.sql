-- Disposable test-only least-privilege worker role.
-- BYPASSRLS enables trusted cross-user discovery; never grant this role to browser users.
create role jobpilot_ci_worker nologin bypassrls;
grant usage on schema public, jobpilot_private to jobpilot_ci_worker;
grant select on public.saved_searches to jobpilot_ci_worker;
grant select, insert, update on public.discovery_runs to jobpilot_ci_worker;
grant select, insert on public.job_notifications to jobpilot_ci_worker;
grant select, insert, update, delete on public.discovery_worker_leases to jobpilot_ci_worker;
grant execute on function jobpilot_private.acquire_discovery_lease(uuid,uuid,integer) to jobpilot_ci_worker;
grant execute on function jobpilot_private.release_discovery_lease(uuid,uuid) to jobpilot_ci_worker;

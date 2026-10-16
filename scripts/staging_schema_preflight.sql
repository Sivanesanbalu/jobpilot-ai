-- Phase 5.17: READ-ONLY staging release preflight.
-- Execute using a database operator in a disposable/staging database AFTER migrations.
-- Do not interpret code-only CI success as staging validation.
do $$
declare
  item text;
  required_tables text[] := array[
    'public.saved_searches','public.discovery_runs','public.job_notifications',
    'public.discovery_worker_leases','public.application_drafts',
    'public.application_approval_events','public.application_status_events'
  ];
begin
  foreach item in array required_tables loop
    if to_regclass(item) is null then
      raise exception 'Missing staged table: %', item;
    end if;
    if not (select c.relrowsecurity from pg_catalog.pg_class c where c.oid=to_regclass(item)) then
      raise exception 'RLS disabled on staged table: %', item;
    end if;
  end loop;
  if to_regprocedure('jobpilot_private.acquire_discovery_lease(uuid,uuid,integer)') is null
     or to_regprocedure('jobpilot_private.release_discovery_lease(uuid,uuid)') is null then
    raise exception 'Worker lease functions missing';
  end if;
  if not exists (select 1 from pg_catalog.pg_trigger
    where tgname='application_draft_review_audit'
    and tgrelid='public.application_drafts'::regclass and not tgisinternal) then
    raise exception 'Draft audit trigger missing';
  end if;
  if not exists (select 1 from pg_catalog.pg_trigger
    where tgname='application_status_audit'
    and tgrelid='public.applications'::regclass and not tgisinternal) then
    raise exception 'Application status trigger missing';
  end if;
  if has_table_privilege('authenticated','public.application_approval_events','INSERT') then
    raise exception 'Authenticated role must not insert approval audit records';
  end if;
  if has_table_privilege('authenticated','public.application_status_events','INSERT') then
    raise exception 'Authenticated role must not insert status audit records';
  end if;
  raise notice 'Staging schema preflight passed (RLS behavior still needs user-isolation integration tests)';
end
$$;

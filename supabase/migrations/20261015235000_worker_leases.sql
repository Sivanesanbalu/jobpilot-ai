-- Phase 4.8: private worker-only transaction-safe lease operations.
-- This migration is staged in develop and must be tested before applying.
create schema if not exists jobpilot_private;
revoke all on schema jobpilot_private from public, anon, authenticated;

create or replace function jobpilot_private.acquire_discovery_lease(
 p_search_id uuid, p_token uuid, p_duration_seconds integer default 300
) returns boolean language plpgsql security invoker set search_path = ''
as $$
begin
 if p_duration_seconds not between 30 and 3600 then
  raise exception 'Invalid lease duration';
 end if;
 insert into public.discovery_worker_leases(saved_search_id,lease_token,expires_at,updated_at)
 values(p_search_id,p_token,clock_timestamp()+make_interval(secs=>p_duration_seconds),clock_timestamp())
 on conflict(saved_search_id) do update
 set lease_token=excluded.lease_token, expires_at=excluded.expires_at,updated_at=excluded.updated_at
 where public.discovery_worker_leases.expires_at < clock_timestamp();
 return found;
end;
$$;

create or replace function jobpilot_private.release_discovery_lease(
 p_search_id uuid,p_token uuid
) returns boolean language plpgsql security invoker set search_path = ''
as $$
begin
 delete from public.discovery_worker_leases
 where saved_search_id=p_search_id and lease_token=p_token;
 return found;
end;
$$;

revoke all on function jobpilot_private.acquire_discovery_lease(uuid,uuid,integer) from public,anon,authenticated;
revoke all on function jobpilot_private.release_discovery_lease(uuid,uuid) from public,anon,authenticated;
-- Execution privileges may be granted only to a dedicated trusted worker role during deployment.

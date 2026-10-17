-- Phase 5.9 staging-only: immutable, owner-scoped status history.
create table if not exists public.application_status_events (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 apply_url text not null,
 previous_status text,
 current_status text not null,
 changed_at timestamptz not null default now()
);
create index if not exists application_status_events_owner_idx
 on public.application_status_events(user_id,changed_at desc);
alter table public.application_status_events enable row level security;
revoke all on public.application_status_events from anon,authenticated;
grant select on public.application_status_events to authenticated;
create policy "application_status_events_read_own" on public.application_status_events
 for select to authenticated using ((select auth.uid()) = user_id);

create or replace function public.log_application_status_change()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
 if tg_op = 'INSERT' or old.status is distinct from new.status then
  insert into public.application_status_events(user_id,apply_url,previous_status,current_status)
  values(new.user_id,new.apply_url,case when tg_op = 'INSERT' then null else old.status end,new.status);
 end if;
 return new;
end;
$$;
revoke all on function public.log_application_status_change() from public,anon,authenticated;
create trigger application_status_audit
 after insert or update of status on public.applications
 for each row execute function public.log_application_status_change();
-- Production application table and permissions are not modified until migration approval.

-- Phase 4.4: apply only after staging validation and explicit release approval.
-- User-scoped search preferences, discovery history and notification inbox.
create table if not exists public.saved_searches (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 query text not null check (char_length(trim(query)) between 2 and 80),
 preferred_location text not null default '',
 remote_only boolean not null default false,
 max_experience integer check (max_experience between 0 and 50),
 is_enabled boolean not null default true,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index if not exists saved_searches_owner_idx on public.saved_searches(user_id, updated_at desc);
alter table public.saved_searches enable row level security;
revoke all on public.saved_searches from anon;
grant select,insert,update,delete on public.saved_searches to authenticated;
create policy "saved_searches_select_own" on public.saved_searches for select to authenticated using ((select auth.uid()) = user_id);
create policy "saved_searches_insert_own" on public.saved_searches for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "saved_searches_update_own" on public.saved_searches for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "saved_searches_delete_own" on public.saved_searches for delete to authenticated using ((select auth.uid()) = user_id);

create table if not exists public.discovery_runs (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 saved_search_id uuid not null,
 started_at timestamptz not null default now(),
 completed_at timestamptz,
 status text not null default 'pending' check (status in ('pending','running','succeeded','failed')),
 discovered_count integer not null default 0 check (discovered_count >= 0),
 error_message text,
 constraint discovery_runs_search_owner_fk foreign key(saved_search_id) references public.saved_searches(id) on delete cascade
);
create index if not exists discovery_runs_owner_idx on public.discovery_runs(user_id, started_at desc);
alter table public.discovery_runs enable row level security;
revoke all on public.discovery_runs from anon;
grant select on public.discovery_runs to authenticated;
-- Writes reserved for a trusted backend worker after ownership checks.
create policy "discovery_runs_select_own" on public.discovery_runs for select to authenticated using ((select auth.uid()) = user_id);

create table if not exists public.job_notifications (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 saved_search_id uuid not null references public.saved_searches(id) on delete cascade,
 job_url text not null check (left(job_url, 8) = 'https://'),
 title text not null default '',
 company text not null default '',
 created_at timestamptz not null default now(),
 read_at timestamptz,
 unique (user_id, saved_search_id, job_url)
);
create index if not exists job_notifications_owner_idx on public.job_notifications(user_id, created_at desc);
alter table public.job_notifications enable row level security;
revoke all on public.job_notifications from anon;
grant select,update on public.job_notifications to authenticated;
-- Inserts reserved for a trusted backend worker. Users can mark only their own alerts read.
create policy "job_notifications_select_own" on public.job_notifications for select to authenticated using ((select auth.uid()) = user_id);
create policy "job_notifications_update_own" on public.job_notifications for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

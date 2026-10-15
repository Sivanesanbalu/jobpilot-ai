-- JobPilot AI - multi-tenant schema (run in dedicated Supabase project)
create extension if not exists pgcrypto;
create table if not exists public.profiles (
 user_id uuid primary key references auth.users(id) on delete cascade,
 full_name text, location text, preferred_roles text[] not null default '{}',
 years_experience numeric(4,1), updated_at timestamptz not null default now()
);
create table if not exists public.resumes (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
 filename text not null, extracted_skills text[] not null default '{}',
 detected_roles jsonb not null default '[]'::jsonb, created_at timestamptz not null default now()
);
create table if not exists public.job_listings (
 id uuid primary key default gen_random_uuid(), provider text not null, provider_job_id text not null,
 company text not null, title text not null, location text, apply_url text not null,
 description text, published_at timestamptz, fetched_at timestamptz not null default now(),
 unique(provider,provider_job_id)
);
create table if not exists public.applications (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
 job_id uuid references public.job_listings(id) on delete set null,
 company text not null, title text not null, apply_url text not null,
 status text not null default 'saved' check(status in ('saved','ready_for_review','submitted','interview','offer','rejected','withdrawn')),
 submitted_at timestamptz, confirmation_ref text, created_at timestamptz not null default now()
);
create table if not exists public.subscription_states (
 user_id uuid primary key references auth.users(id) on delete cascade,
 provider text, provider_customer_id text, provider_subscription_id text,
 plan text not null default 'free' check(plan in ('free','pro','team')),
 status text not null default 'inactive', current_period_end timestamptz,
 updated_at timestamptz not null default now()
);
create unique index if not exists subscription_provider_key on public.subscription_states(provider,provider_subscription_id) where provider_subscription_id is not null;
create table if not exists public.application_approvals (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 application_id uuid not null references public.applications(id) on delete cascade,
 approved_at timestamptz, expires_at timestamptz, created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
alter table public.resumes enable row level security;
alter table public.job_listings enable row level security;
alter table public.applications enable row level security;
alter table public.subscription_states enable row level security;
alter table public.application_approvals enable row level security;
revoke all on public.subscription_states from anon, authenticated;
grant select on public.subscription_states to authenticated;
grant select,insert,update,delete on public.profiles,public.resumes,public.applications,public.application_approvals to authenticated;
grant select on public.job_listings to authenticated;
create policy "profile_select" on public.profiles for select to authenticated using ((select auth.uid())=user_id);
create policy "profile_insert" on public.profiles for insert to authenticated with check ((select auth.uid())=user_id);
create policy "profile_update" on public.profiles for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy "profile_delete" on public.profiles for delete to authenticated using ((select auth.uid())=user_id);
create policy "resume_select" on public.resumes for select to authenticated using ((select auth.uid())=user_id);
create policy "resume_insert" on public.resumes for insert to authenticated with check ((select auth.uid())=user_id);
create policy "resume_update" on public.resumes for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy "resume_delete" on public.resumes for delete to authenticated using ((select auth.uid())=user_id);
create policy "job_read" on public.job_listings for select to authenticated using (true);
create policy "application_select" on public.applications for select to authenticated using ((select auth.uid())=user_id);
create policy "application_insert" on public.applications for insert to authenticated with check ((select auth.uid())=user_id);
create policy "application_update" on public.applications for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy "application_delete" on public.applications for delete to authenticated using ((select auth.uid())=user_id);
create policy "subscription_read" on public.subscription_states for select to authenticated using ((select auth.uid())=user_id);
create policy "approval_select" on public.application_approvals for select to authenticated using ((select auth.uid())=user_id);
create policy "approval_insert" on public.application_approvals for insert to authenticated with check ((select auth.uid())=user_id);
create policy "approval_update" on public.application_approvals for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy "approval_delete" on public.application_approvals for delete to authenticated using ((select auth.uid())=user_id);

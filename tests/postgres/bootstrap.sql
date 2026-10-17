-- Disposable PostgreSQL CI fixture, never run against production.
create role authenticated nologin;
create role anon nologin;
create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$
 select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
$$;
grant usage on schema public to authenticated;
grant usage on schema auth to authenticated;
create table public.applications(
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id),
 apply_url text not null,
 status text not null default 'saved',
 created_at timestamptz default now(),
 unique(user_id,apply_url)
);
insert into auth.users(id) values
 ('00000000-0000-0000-0000-000000000101'),
 ('00000000-0000-0000-0000-000000000102');

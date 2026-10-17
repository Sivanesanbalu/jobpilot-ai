-- Phase 5.5: staging-first migration; do not apply automatically to production.
create table if not exists public.application_drafts (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 job_title text not null check (char_length(job_title) between 1 and 250),
 company text not null check (char_length(company) between 1 and 180),
 draft_text text not null check (char_length(draft_text) between 1 and 10000),
 approval_status text not null default 'draft' check (approval_status in ('draft','reviewed')),
 submission_status text not null default 'NOT_SUBMITTED' check (submission_status = 'NOT_SUBMITTED'),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique (id,user_id)
);
create index if not exists application_drafts_owner_idx on public.application_drafts(user_id,updated_at desc);
alter table public.application_drafts enable row level security;
revoke all on public.application_drafts from anon;
grant select,insert,update,delete on public.application_drafts to authenticated;
create policy "application_drafts_read_own" on public.application_drafts for select to authenticated using ((select auth.uid())=user_id);
create policy "application_drafts_insert_own" on public.application_drafts for insert to authenticated with check ((select auth.uid())=user_id);
create policy "application_drafts_update_own" on public.application_drafts for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy "application_drafts_delete_own" on public.application_drafts for delete to authenticated using ((select auth.uid())=user_id);

create table if not exists public.application_approval_events (
 id uuid primary key default gen_random_uuid(),
 draft_id uuid not null,
 user_id uuid not null references auth.users(id) on delete cascade,
 event_type text not null check (event_type in ('draft_created','review_approved','review_revoked')),
 created_at timestamptz not null default now(),
 constraint application_approval_events_owner_fk foreign key (draft_id,user_id)
 references public.application_drafts(id,user_id) on delete cascade
);
create index if not exists application_approval_events_owner_idx on public.application_approval_events(user_id,created_at desc);
alter table public.application_approval_events enable row level security;
revoke all on public.application_approval_events from anon;
grant select,insert on public.application_approval_events to authenticated;
create policy "approval_events_read_own" on public.application_approval_events for select to authenticated using ((select auth.uid())=user_id);
create policy "approval_events_insert_own" on public.application_approval_events for insert to authenticated with check ((select auth.uid())=user_id);
-- Append only. Browser clients have no UPDATE or DELETE permission.

-- Audit events are written by a database trigger, not by browser-supplied event_type.
revoke insert on public.application_approval_events from authenticated;
create or replace function public.record_application_draft_review()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
 if tg_op = 'INSERT' then
  insert into public.application_approval_events(draft_id,user_id,event_type)
  values(new.id,new.user_id,'draft_created');
 elsif old.approval_status is distinct from new.approval_status then
  insert into public.application_approval_events(draft_id,user_id,event_type)
  values(new.id,new.user_id,
   case when new.approval_status = 'reviewed' then 'review_approved' else 'review_revoked' end);
 end if;
 return new;
end;
$$;
revoke all on function public.record_application_draft_review() from public,anon,authenticated;
create trigger application_draft_review_audit after insert or update of approval_status
on public.application_drafts for each row execute function public.record_application_draft_review();

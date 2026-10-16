-- Phase 5.7: staged extension for draft-to-tracker linking.
alter table public.application_drafts
 add column if not exists apply_url text;
alter table public.application_drafts
 add constraint application_drafts_apply_url_https
 check (apply_url is null or (length(apply_url) <= 2000 and apply_url ~ '^https://[^[:space:]]+$'));
-- Link only to an application owned by the same user.
create unique index if not exists applications_owner_url_unique
 on public.applications(user_id,apply_url);
-- Existing application records remain user-owned under their prior RLS policies.

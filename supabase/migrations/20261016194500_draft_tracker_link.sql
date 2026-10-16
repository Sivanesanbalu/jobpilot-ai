-- Phase 5.7: staged extension for saved draft application links.
-- Link remains optional for previously saved drafts.
alter table public.application_drafts
 add column if not exists apply_url text;
alter table public.application_drafts
 add constraint application_drafts_apply_url_https
 check (apply_url is null or (length(apply_url) <= 2000 and apply_url ~ '^https://[^[:space:]]+$'));
-- Actual submitted status remains part of the separate user-owned applications tracker.

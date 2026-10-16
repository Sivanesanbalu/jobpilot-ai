"""Integration tests run only against the disposable postgres CI service."""
import asyncio
import os
from pathlib import Path
import asyncpg

ROOT=Path(__file__).resolve().parents[2]
A="00000000-0000-0000-0000-000000000101"
B="00000000-0000-0000-0000-000000000102"

async def main():
    dsn=os.environ["JOBPILOT_TEST_DATABASE_URL"]
    admin=await asyncpg.connect(dsn)
    try:
        await admin.execute((ROOT/"tests/postgres/bootstrap.sql").read_text())
        for migration in (
            "20261016193000_application_drafts.sql",
            "20261016194500_draft_tracker_link.sql",
            "20261016200000_application_status_history.sql",
        ):
            await admin.execute((ROOT/"supabase/migrations"/migration).read_text())
        # Verify actual trigger inserts before switching to restricted browser role.
        row=await admin.fetchrow(
            """insert into public.application_drafts(user_id,job_title,company,draft_text)
               values($1,'AI Engineer','Example','Verified skills') returning id""", A)
        draft_id=row["id"]
        assert await admin.fetchval(
            "select count(*) from public.application_approval_events where draft_id=$1 and event_type='draft_created'",
            draft_id)==1
        await admin.execute("update public.application_drafts set approval_status='reviewed' where id=$1",draft_id)
        assert await admin.fetchval(
            "select count(*) from public.application_approval_events where draft_id=$1 and event_type='review_approved'",
            draft_id)==1
        await admin.execute(
            "insert into public.applications(user_id,apply_url,status) values($1,'https://example.com/apply','saved')",A)
        await admin.execute(
            "update public.applications set status='submitted' where user_id=$1",A)
        assert await admin.fetchval(
            "select count(*) from public.application_status_events where user_id=$1",A)==2
        # Exercise RLS with restricted authenticated role under two simulated JWT identities.
        for who,expected in ((A,1),(B,0)):
            async with admin.transaction():
                await admin.execute("set local role authenticated")
                await admin.execute("select set_config('request.jwt.claim.sub',$1,true)",who)
                found=await admin.fetchval("select count(*) from public.application_drafts")
                assert found==expected,(who,found)
                count=await admin.fetchval("select count(*) from public.application_approval_events")
                assert count==(2 if who==A else 0)
                history=await admin.fetchval("select count(*) from public.application_status_events")
                assert history==(2 if who==A else 0)
        # Audit tables cannot be directly written by browser role.
        assert not await admin.fetchval(
            "select has_table_privilege('authenticated','public.application_approval_events','INSERT')")
        assert not await admin.fetchval(
            "select has_table_privilege('authenticated','public.application_status_events','INSERT')")
        print("Isolated PostgreSQL trigger and user-isolation tests passed")
    finally:
        await admin.close()

if __name__=="__main__":
    asyncio.run(main())

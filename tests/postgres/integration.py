"""Integration tests run only against the disposable postgres CI service."""
import asyncio
import os
from pathlib import Path
import asyncpg
from uuid import UUID, uuid4
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from postgres_discovery_repository import PostgresDiscoveryRepository

ROOT=Path(__file__).resolve().parents[2]
A="00000000-0000-0000-0000-000000000101"
B="00000000-0000-0000-0000-000000000102"

async def main():
    dsn=os.environ["JOBPILOT_TEST_DATABASE_URL"]
    admin=await asyncpg.connect(dsn)
    try:
        await admin.execute((ROOT/"tests/postgres/bootstrap.sql").read_text())
        for migration in (
            "20261015224400_job_discovery_state.sql",
            "20261015235000_worker_leases.sql",
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
        # Real database lease contention and fencing tests.
        search=await admin.fetchval(
            "insert into public.saved_searches(user_id,query) values($1,'AI engineer') returning id", A)
        first_token,second_token=uuid4(),uuid4()
        pool=await asyncpg.create_pool(dsn,min_size=2,max_size=2)
        try:
            async def race(token):
                async with pool.acquire() as conn:
                    return await conn.fetchval(
                        "select jobpilot_private.acquire_discovery_lease($1,$2,300)",
                        search,token)
            results=await asyncio.gather(race(first_token),race(second_token))
            assert sorted(results)==[False,True],results
            winner=first_token if results[0] else second_token
            loser=second_token if results[0] else first_token
            assert not await admin.fetchval(
                "select jobpilot_private.release_discovery_lease($1,$2)",search,loser)
            assert await admin.fetchval(
                "select jobpilot_private.release_discovery_lease($1,$2)",search,winner)
            assert await admin.fetchval(
                "select jobpilot_private.acquire_discovery_lease($1,$2,300)",search,loser)
            # An expired lease can be replaced; stale token cannot release new ownership.
            await admin.execute(
                "update public.discovery_worker_leases set expires_at=now()-interval '1 second' where saved_search_id=$1",search)
            assert await admin.fetchval(
                "select jobpilot_private.acquire_discovery_lease($1,$2,300)",search,winner)
            assert not await admin.fetchval(
                "select jobpilot_private.release_discovery_lease($1,$2)",search,loser)
            assert await admin.fetchval(
                "select jobpilot_private.release_discovery_lease($1,$2)",search,winner)
            # Database uniqueness must suppress duplicate job notifications.
            await admin.execute(
                "insert into public.job_notifications(user_id,saved_search_id,job_url,title) values($1,$2,$3,'AI Engineer') on conflict do nothing",
                A,search,"https://example.com/jobs/one")
            await admin.execute(
                "insert into public.job_notifications(user_id,saved_search_id,job_url,title) values($1,$2,$3,'AI Engineer') on conflict do nothing",
                A,search,"https://example.com/jobs/one")
            assert await admin.fetchval(
                "select count(*) from public.job_notifications where saved_search_id=$1",search)==1
            repository=PostgresDiscoveryRepository(pool)
            token=uuid4()
            assert await repository.acquire_lease(search,token,300)
            record=await repository.get_search(search)
            run=await repository.start_run(record)
            jobs=[{"job_url":"https://example.com/jobs/two","title":"Engineer","company":"Example"}]
            assert await repository.complete_run(run,jobs,token)==1
            assert await admin.fetchval(
                "select status from public.discovery_runs where id=$1",run)=="succeeded"
            assert await repository.release_lease(search,token)
            assert await repository.acquire_lease(search,token,300)
            duplicate=await repository.start_run(record)
            assert await repository.complete_run(duplicate,jobs,token)==0
            assert await repository.release_lease(search,token)
            # Failed inserts must roll back both notifications and successful run status.
            assert await repository.acquire_lease(search,token,300)
            rollback_run=await repository.start_run(record)
            try:
                await repository.complete_run(rollback_run,[
                    {"job_url":"https://example.com/jobs/rollback","title":"Engineer"},
                    {"job_url":"http://unsafe.example/jobs/bad","title":"Bad"}],token)
                raise AssertionError("Invalid notification URL unexpectedly committed")
            except asyncpg.CheckViolationError:
                pass
            assert await admin.fetchval(
                "select status from public.discovery_runs where id=$1",rollback_run)=="running"
            assert await admin.fetchval(
                "select count(*) from public.job_notifications where job_url=$1",
                "https://example.com/jobs/rollback")==0
            await repository.release_lease(search,token)
            # Completing with no valid lease cannot change the run or write alerts.
            stale=await repository.start_run(record)
            try:
                await repository.complete_run(stale,[{"job_url":"https://example.com/jobs/stale"}],token)
                raise AssertionError("Stale lease unexpectedly finalized the run")
            except RuntimeError as exc:
                assert "lease" in str(exc).lower()
            assert await admin.fetchval(
                "select status from public.discovery_runs where id=$1",stale)=="running"
        finally:
            await pool.close()
        print("Isolated PostgreSQL triggers, worker leases, and user-isolation tests passed")
    finally:
        await admin.close()

if __name__=="__main__":
    asyncio.run(main())

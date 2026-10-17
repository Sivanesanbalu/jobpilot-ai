"""PostgreSQL repository for a trusted, separately hosted JobPilot worker.

Pass an asyncpg pool created server-side using a secret DATABASE_URL.
Never expose the database URL or this repository in browser code.
"""
from uuid import UUID

class PostgresDiscoveryRepository:
    def __init__(self, pool):
        self.pool = pool

    async def acquire_lease(self, search_id, token, seconds):
        if not 30 <= seconds <= 3600:
            raise ValueError("Invalid lease duration")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """select jobpilot_private.acquire_discovery_lease($1,$2,$3)""",
                UUID(str(search_id)), UUID(str(token)), seconds)

    async def release_lease(self, search_id, token):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """select jobpilot_private.release_discovery_lease($1,$2)""",
                UUID(str(search_id)), UUID(str(token)))

    async def get_search(self, search_id):
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """select id,user_id,query,is_enabled from public.saved_searches where id=$1""",
                UUID(str(search_id)))
            return dict(record) if record else None

    async def start_run(self, search):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """insert into public.discovery_runs(user_id,saved_search_id,status)
                   values($1,$2,'running') returning id""",
                search["user_id"], search["id"])

    async def complete_run(self, run_id, jobs, lease_token):
        """Notification inserts and successful run completion commit together."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                run = await conn.fetchrow(
                    """select user_id,saved_search_id from public.discovery_runs
                       where id=$1 and status='running' for update""", run_id)
                if run is None:
                    raise ValueError("Run not found or already finalized")
                locked = await conn.fetchval(
                    """select 1 from public.discovery_worker_leases
                       where saved_search_id=$1 and lease_token=$2
                         and expires_at > clock_timestamp() for update""",
                    run["saved_search_id"], UUID(str(lease_token)))
                if not locked:
                    raise RuntimeError("Worker lease expired or was superseded")
                count = 0
                for job in jobs:
                    changed = await conn.fetchval(
                        """insert into public.job_notifications
                           (user_id,saved_search_id,job_url,title,company)
                           values($1,$2,$3,$4,$5)
                           on conflict(user_id,saved_search_id,job_url) do nothing
                           returning id""",
                        run["user_id"], run["saved_search_id"], job["job_url"],
                        job.get("title", ""), job.get("company", ""))
                    count += int(changed is not None)
                await conn.execute(
                    """update public.discovery_runs
                       set status='succeeded', completed_at=now(), discovered_count=$2
                       where id=$1""", run_id, count)
                return count

    async def fail_run(self, run_id, error):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """update public.discovery_runs
                   set status='failed', completed_at=now(), error_message=$2
                   where id=$1 and status='running'""", run_id, str(error)[:500])

"""Secure lifecycle for the separately hosted JobPilot discovery worker.

This module never starts a worker or opens a connection at import time.
"""
import os
from dataclasses import dataclass
from urllib.parse import urlsplit
from postgres_discovery_repository import PostgresDiscoveryRepository

@dataclass(frozen=True)
class WorkerSettings:
    database_url: str
    pool_min: int = 1
    pool_max: int = 5

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        url = env.get("JOBPILOT_WORKER_DATABASE_URL", "")
        parsed = urlsplit(url)
        if parsed.scheme not in ("postgresql", "postgres") or not parsed.hostname:
            raise ValueError("Valid PostgreSQL worker database URL required")
        if parsed.hostname in ("localhost", "127.0.0.1") and env.get("JOBPILOT_ALLOW_LOCAL_DB") != "1":
            raise ValueError("Local database requires explicit development opt-in")
        from urllib.parse import parse_qs
        sslmodes = parse_qs(parsed.query).get("sslmode", [])
        if any(mode.lower() in ("disable", "allow", "prefer") for mode in sslmodes):
            raise ValueError("Worker requires TLS; insecure sslmode is not allowed")
        if parsed.username is None or parsed.password is None:
            raise ValueError("Worker database URL requires credentials")
        minimum = int(env.get("JOBPILOT_POOL_MIN", "1"))
        maximum = int(env.get("JOBPILOT_POOL_MAX", "5"))
        if not (1 <= minimum <= maximum <= 20):
            raise ValueError("Worker pool limits must satisfy 1 <= min <= max <= 20")
        return cls(url, minimum, maximum)

class WorkerRuntime:
    def __init__(self, settings, pool_factory=None):
        self.settings = settings
        self.pool_factory = pool_factory
        self.pool = None

    async def start(self):
        if self.pool is not None:
            return self
        if self.pool_factory is None:
            import asyncpg
            self.pool_factory = asyncpg.create_pool
        self.pool = await self.pool_factory(
            dsn=self.settings.database_url,
            min_size=self.settings.pool_min,
            max_size=self.settings.pool_max,
            command_timeout=30,
            ssl="require",
        )
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("select 1")
                required = await conn.fetchrow(
                    """select
                       to_regclass('public.saved_searches') is not null as searches,
                       to_regclass('public.discovery_runs') is not null as runs,
                       to_regclass('public.job_notifications') is not null as notifications,
                       to_regclass('public.discovery_worker_leases') is not null as leases,
                       to_regprocedure('jobpilot_private.acquire_discovery_lease(uuid,uuid,integer)') is not null as acquire,
                       to_regprocedure('jobpilot_private.release_discovery_lease(uuid,uuid)') is not null as release"""
                )
                if not required or not all(required.values()):
                    raise RuntimeError("Worker migrations are missing; refusing startup")
                access = await conn.fetchrow(
                    """select
                       has_table_privilege(current_user,'public.saved_searches','SELECT') as searches,
                       (has_table_privilege(current_user,'public.discovery_runs','INSERT') and has_table_privilege(current_user,'public.discovery_runs','UPDATE')) as runs,
                       has_table_privilege(current_user,'public.job_notifications','INSERT') as notifications,
                       (has_table_privilege(current_user,'public.discovery_worker_leases','INSERT') and has_table_privilege(current_user,'public.discovery_worker_leases','UPDATE') and has_table_privilege(current_user,'public.discovery_worker_leases','DELETE') and has_table_privilege(current_user,'public.discovery_worker_leases','SELECT')) as leases,
                       has_function_privilege(current_user,'jobpilot_private.acquire_discovery_lease(uuid,uuid,integer)','EXECUTE') as acquire,
                       has_function_privilege(current_user,'jobpilot_private.release_discovery_lease(uuid,uuid)','EXECUTE') as release,
                       has_schema_privilege(current_user,'jobpilot_private','USAGE') as private_schema"""
                )
                if not access or not all(access.values()):
                    raise RuntimeError("Worker database permissions are insufficient; refusing startup")
        except Exception:
            await self.pool.close()
            self.pool = None
            raise
        return self

    def repository(self):
        if self.pool is None:
            raise RuntimeError("Worker is not started")
        return PostgresDiscoveryRepository(self.pool)

    async def health(self):
        if self.pool is None:
            return {"ok": False, "database": "disconnected"}
        try:
            async with self.pool.acquire() as conn:
                ok = await conn.fetchval("select 1")
            return {"ok": ok == 1, "database": "connected" if ok == 1 else "unhealthy"}
        except Exception:
            return {"ok": False, "database": "unavailable"}

    async def close(self):
        if self.pool is not None:
            pool = self.pool
            self.pool = None
            await pool.close()

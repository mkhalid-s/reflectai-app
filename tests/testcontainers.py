#!/usr/bin/env python3
"""
Testcontainers Infrastructure for ReflectAI Testing

Provides containerized test environments for:
- PostgreSQL with TimescaleDB
- Redis with Redis Stack modules
- NATS messaging
- Local development environment

Features:
- Automatic container lifecycle management
- Health checks and readiness detection
- Data isolation between tests
- Performance monitoring
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pytest_asyncio

try:
    from testcontainers.generic import GenericContainer
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    print("Warning: testcontainers not available. Install with: pip install testcontainers")


@dataclass
class ContainerConfig:
    """Configuration for test containers."""

    postgres_image: str = "timescale/timescaledb:latest-pg15"
    redis_image: str = "redis/redis-stack:latest"
    nats_image: str = "nats:2.10-alpine"

    postgres_port: int = 5432
    redis_port: int = 6379
    nats_port: int = 4222

    postgres_user: str = "testuser"
    postgres_password: str = "testpass"
    postgres_db: str = "testdb"

    # Container lifecycle settings
    container_timeout: int = 300  # 5 minutes
    health_check_timeout: int = 60  # 1 minute
    startup_timeout: int = 30  # 30 seconds


@dataclass
class TestEnvironment:
    """Running test environment configuration."""

    postgres_container: Any | None = None
    redis_container: Any | None = None
    nats_container: Any | None = None

    postgres_url: str = ""
    redis_url: str = ""
    nats_url: str = ""

    start_time: datetime = field(default_factory=datetime.now)


class TestContainerManager:
    """Manages test containers for isolated testing."""

    def __init__(self, config: ContainerConfig = None):
        self.config = config or ContainerConfig()
        self.environments: dict[str, TestEnvironment] = {}
        self._available = TESTCONTAINERS_AVAILABLE

    def is_available(self) -> bool:
        """Check if testcontainers is available."""
        return self._available

    @asynccontextmanager
    async def create_postgres_container(self) -> AsyncGenerator[TestEnvironment, None]:
        """Create a PostgreSQL container with TimescaleDB."""
        if not self._available:
            raise RuntimeError("testcontainers not available")

        env = TestEnvironment()

        try:
            # Create and start PostgreSQL container
            container = PostgresContainer(
                image=self.config.postgres_image,
                username=self.config.postgres_user,
                password=self.config.postgres_password,
                dbname=self.config.postgres_db,
                driver=None,  # Use async driver
            )

            container = container.with_exposed_ports(self.config.postgres_port)
            env.postgres_container = container

            # Start container
            container.start()

            # Get connection details
            host = container.get_container_host_ip()
            port = container.get_exposed_port(self.config.postgres_port)
            env.postgres_url = f"postgresql+asyncpg://{self.config.postgres_user}:{self.config.postgres_password}@{host}:{port}/{self.config.postgres_db}"

            # Wait for database to be ready
            await self._wait_for_postgres(host, port)

            yield env

        finally:
            # Cleanup
            if env.postgres_container:
                env.postgres_container.stop()

    @asynccontextmanager
    async def create_redis_container(self) -> AsyncGenerator[TestEnvironment, None]:
        """Create a Redis container with Redis Stack modules."""
        if not self._available:
            raise RuntimeError("testcontainers not available")

        env = TestEnvironment()

        try:
            # Create and start Redis container
            container = RedisContainer(image=self.config.redis_image)
            container = container.with_exposed_ports(self.config.redis_port)
            env.redis_container = container

            # Start container
            container.start()

            # Get connection details
            host = container.get_container_host_ip()
            port = container.get_exposed_port(self.config.redis_port)
            env.redis_url = f"redis://{host}:{port}/0"

            # Wait for Redis to be ready
            await self._wait_for_redis(host, port)

            yield env

        finally:
            # Cleanup
            if env.redis_container:
                env.redis_container.stop()

    @asynccontextmanager
    async def create_nats_container(self) -> AsyncGenerator[TestEnvironment, None]:
        """Create a NATS container."""
        if not self._available:
            raise RuntimeError("testcontainers not available")

        env = TestEnvironment()

        try:
            # Create and start NATS container
            container = GenericContainer(self.config.nats_image)
            container = container.with_exposed_ports(self.config.nats_port)
            container = container.with_command(["-js"])  # Enable JetStream
            env.nats_container = container

            # Start container
            container.start()

            # Get connection details
            host = container.get_container_host_ip()
            port = container.get_exposed_port(self.config.nats_port)
            env.nats_url = f"nats://{host}:{port}"

            # Wait for NATS to be ready
            await self._wait_for_nats(host, port)

            yield env

        finally:
            # Cleanup
            if env.nats_container:
                env.nats_container.stop()

    @asynccontextmanager
    async def create_full_environment(self) -> AsyncGenerator[TestEnvironment, None]:
        """Create a complete test environment with all services."""
        if not self._available:
            raise RuntimeError("testcontainers not available")

        env = TestEnvironment()

        try:
            # Start all containers concurrently
            postgres_container = PostgresContainer(
                image=self.config.postgres_image,
                username=self.config.postgres_user,
                password=self.config.postgres_password,
                dbname=self.config.postgres_db,
            ).with_exposed_ports(self.config.postgres_port)

            redis_container = RedisContainer(image=self.config.redis_image).with_exposed_ports(
                self.config.redis_port
            )

            nats_container = GenericContainer(self.config.nats_image)
            nats_container = nats_container.with_exposed_ports(self.config.nats_port)
            nats_container = nats_container.with_command(["-js"])

            # Start containers
            env.postgres_container = postgres_container
            env.redis_container = redis_container
            env.nats_container = nats_container

            postgres_container.start()
            redis_container.start()
            nats_container.start()

            # Get connection details
            env.postgres_url = f"postgresql+asyncpg://{self.config.postgres_user}:{self.config.postgres_password}@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(self.config.postgres_port)}/{self.config.postgres_db}"
            env.redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(self.config.redis_port)}/0"
            env.nats_url = f"nats://{nats_container.get_container_host_ip()}:{nats_container.get_exposed_port(self.config.nats_port)}"

            # Wait for all services to be ready
            await asyncio.gather(
                self._wait_for_postgres(
                    postgres_container.get_container_host_ip(),
                    postgres_container.get_exposed_port(self.config.postgres_port),
                ),
                self._wait_for_redis(
                    redis_container.get_container_host_ip(),
                    redis_container.get_exposed_port(self.config.redis_port),
                ),
                self._wait_for_nats(
                    nats_container.get_container_host_ip(),
                    nats_container.get_exposed_port(self.config.nats_port),
                ),
            )

            yield env

        finally:
            # Cleanup all containers
            for container in [env.postgres_container, env.redis_container, env.nats_container]:
                if container:
                    container.stop()

    async def _wait_for_postgres(self, host: str, port: int, timeout: int = 30):
        """Wait for PostgreSQL to be ready."""
        import asyncpg

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = await asyncpg.connect(
                    f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}@{host}:{port}/{self.config.postgres_db}"
                )
                await conn.close()
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise TimeoutError(f"PostgreSQL not ready after {timeout} seconds")

    async def _wait_for_redis(self, host: str, port: int, timeout: int = 30):
        """Wait for Redis to be ready."""
        import redis.asyncio as redis

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                client = redis.Redis(host=host, port=port, decode_responses=True)
                await client.ping()
                await client.close()
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise TimeoutError(f"Redis not ready after {timeout} seconds")

    async def _wait_for_nats(self, host: str, port: int, timeout: int = 30):
        """Wait for NATS to be ready."""
        import nats

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                nc = await nats.connect(f"nats://{host}:{port}")
                await nc.close()
                return
            except Exception:
                await asyncio.sleep(0.5)

        raise TimeoutError(f"NATS not ready after {timeout} seconds")

    def get_environment_info(self, env: TestEnvironment) -> dict[str, Any]:
        """Get information about a test environment."""
        return {
            "postgres_url": env.postgres_url,
            "redis_url": env.redis_url,
            "nats_url": env.nats_url,
            "start_time": env.start_time.isoformat(),
            "uptime_seconds": (datetime.now() - env.start_time).total_seconds(),
        }


# Global instance for easy access
container_manager = TestContainerManager()


# Pytest fixtures
@pytest_asyncio.fixture(scope="session")
async def postgres_container():
    """Session-scoped PostgreSQL container for testing."""
    async with container_manager.create_postgres_container() as env:
        yield env


@pytest_asyncio.fixture(scope="session")
async def redis_container():
    """Session-scoped Redis container for testing."""
    async with container_manager.create_redis_container() as env:
        yield env


@pytest_asyncio.fixture(scope="session")
async def nats_container():
    """Session-scoped NATS container for testing."""
    async with container_manager.create_nats_container() as env:
        yield env


@pytest_asyncio.fixture(scope="session")
async def full_test_environment():
    """Session-scoped full test environment with all services."""
    async with container_manager.create_full_environment() as env:
        yield env


def get_container_manager() -> TestContainerManager:
    """Get the global container manager instance."""
    return container_manager


def is_testcontainers_available() -> bool:
    """Check if testcontainers is available."""
    return TESTCONTAINERS_AVAILABLE


# Utility functions for testing
async def create_test_database_session(postgres_url: str):
    """Create a test database session."""
    import asyncpg

    try:
        conn = await asyncpg.connect(postgres_url)
        yield conn
    finally:
        await conn.close()


async def create_test_redis_client(redis_url: str):
    """Create a test Redis client."""
    import redis.asyncio as redis_client

    try:
        client = redis_client.from_url(redis_url)
        yield client
    finally:
        await client.close()


async def create_test_nats_client(nats_url: str):
    """Create a test NATS client."""
    try:
        import nats

        nc = await nats.connect(nats_url)
        yield nc
    except ImportError as e:
        raise RuntimeError("nats-py not installed") from e
    except Exception as e:
        raise RuntimeError(f"Failed to connect to NATS: {e}") from e

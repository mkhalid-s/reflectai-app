"""
Performance Benchmarking Suite for ReflectAI Platform

Comprehensive performance testing framework for measuring:
- API endpoint response times
- Database query performance
- LLM gateway throughput
- Cache hit rates
- Concurrent request handling
"""

import asyncio
import json
import random
import statistics
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import aiohttp
import asyncpg
import redis.asyncio as redis

from src.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Performance benchmark result"""

    test_name: str
    duration_ms: float
    requests_per_second: float
    min_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    successful_requests: int
    failed_requests: int
    timestamp: datetime


class PerformanceBenchmark:
    """Base class for performance benchmarks"""

    def __init__(self, name: str, config: dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.results: list[float] = []
        self.errors: list[Exception] = []

    async def setup(self):
        """Setup benchmark environment"""
        pass

    async def teardown(self):
        """Cleanup benchmark environment"""
        pass

    async def run_single_test(self) -> float:
        """Run a single test iteration. Override in subclasses."""
        raise NotImplementedError

    async def run(self, iterations: int = 100, concurrent: int = 1) -> BenchmarkResult:
        """Run the benchmark with specified iterations and concurrency"""

        await self.setup()

        try:
            start_time = time.time()

            if concurrent > 1:
                # Run concurrent tests
                tasks = []
                for _ in range(iterations):
                    tasks.append(self._timed_test())
                    if len(tasks) >= concurrent:
                        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                        self._process_results(batch_results)
                        tasks = []

                # Process remaining tasks
                if tasks:
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    self._process_results(batch_results)
            else:
                # Run sequential tests
                for _ in range(iterations):
                    try:
                        latency = await self._timed_test()
                        self.results.append(latency)
                    except Exception as e:
                        self.errors.append(e)

            total_duration = time.time() - start_time

            return self._calculate_results(total_duration, iterations)

        finally:
            await self.teardown()

    async def _timed_test(self) -> float:
        """Run a single timed test"""
        start = time.perf_counter()
        await self.run_single_test()
        return (time.perf_counter() - start) * 1000  # Convert to ms

    def _process_results(self, batch_results: list):
        """Process batch results"""
        for result in batch_results:
            if isinstance(result, Exception):
                self.errors.append(result)
            else:
                self.results.append(result)

    def _calculate_results(self, total_duration: float, iterations: int) -> BenchmarkResult:
        """Calculate benchmark statistics"""

        if not self.results:
            # All tests failed
            return BenchmarkResult(
                test_name=self.name,
                duration_ms=total_duration * 1000,
                requests_per_second=0,
                min_latency_ms=0,
                max_latency_ms=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                error_rate=1.0,
                successful_requests=0,
                failed_requests=len(self.errors),
                timestamp=datetime.now(UTC),
            )

        sorted_results = sorted(self.results)

        return BenchmarkResult(
            test_name=self.name,
            duration_ms=total_duration * 1000,
            requests_per_second=len(self.results) / total_duration,
            min_latency_ms=min(self.results),
            max_latency_ms=max(self.results),
            avg_latency_ms=statistics.mean(self.results),
            p50_latency_ms=self._percentile(sorted_results, 0.50),
            p95_latency_ms=self._percentile(sorted_results, 0.95),
            p99_latency_ms=self._percentile(sorted_results, 0.99),
            error_rate=len(self.errors) / iterations,
            successful_requests=len(self.results),
            failed_requests=len(self.errors),
            timestamp=datetime.now(UTC),
        )

    @staticmethod
    def _percentile(sorted_list: list[float], percentile: float) -> float:
        """Calculate percentile from sorted list"""
        index = int(len(sorted_list) * percentile)
        return sorted_list[min(index, len(sorted_list) - 1)]


class APIEndpointBenchmark(PerformanceBenchmark):
    """Benchmark for API endpoints"""

    def __init__(self, endpoint: str, method: str = "GET", payload: dict = None):
        super().__init__(f"API_{method}_{endpoint}")
        self.endpoint = endpoint
        self.method = method
        self.payload = payload
        self.session: aiohttp.ClientSession = None
        self.base_url = "http://localhost:8000"

    async def setup(self):
        """Create HTTP session"""
        self.session = aiohttp.ClientSession()

    async def teardown(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    async def run_single_test(self) -> float:
        """Make single API request"""
        url = f"{self.base_url}{self.endpoint}"

        if self.method == "GET":
            async with self.session.get(url) as response:
                await response.text()
                response.raise_for_status()
        elif self.method == "POST":
            async with self.session.post(url, json=self.payload) as response:
                await response.text()
                response.raise_for_status()


class DatabaseQueryBenchmark(PerformanceBenchmark):
    """Benchmark for database queries"""

    def __init__(self, query: str, params: tuple = None):
        super().__init__(f"DB_Query_{hash(query) % 10000}")
        self.query = query
        self.params = params
        self.pool: asyncpg.Pool = None

    async def setup(self):
        """Create database connection pool"""
        self.pool = await asyncpg.create_pool(
            "postgresql://test_user:test_pass@localhost:5432/test_db", min_size=5, max_size=20
        )

    async def teardown(self):
        """Close database pool"""
        if self.pool:
            await self.pool.close()

    async def run_single_test(self) -> float:
        """Execute single query"""
        async with self.pool.acquire() as conn:
            if self.params:
                await conn.fetch(self.query, *self.params)
            else:
                await conn.fetch(self.query)


class CacheBenchmark(PerformanceBenchmark):
    """Benchmark for cache operations"""

    def __init__(self, operation: str = "get"):
        super().__init__(f"Cache_{operation}")
        self.operation = operation
        self.redis_client: redis.Redis = None

    async def setup(self):
        """Connect to Redis"""
        self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Pre-populate cache for read tests
        if self.operation == "get":
            for i in range(1000):
                await self.redis_client.set(f"bench_key_{i}", f"value_{i}")

    async def teardown(self):
        """Cleanup Redis"""
        if self.redis_client:
            # Clean up test keys
            keys = await self.redis_client.keys("bench_key_*")
            if keys:
                await self.redis_client.delete(*keys)
            await self.redis_client.close()

    async def run_single_test(self) -> float:
        """Execute cache operation"""
        key = f"bench_key_{random.randint(0, 999)}"

        if self.operation == "get":
            await self.redis_client.get(key)
        elif self.operation == "set":
            await self.redis_client.set(key, f"value_{uuid.uuid4()}")
        elif self.operation == "delete":
            await self.redis_client.delete(key)


class LLMGatewayBenchmark(PerformanceBenchmark):
    """Benchmark for LLM Gateway"""

    def __init__(self, model_tier: str = "standard"):
        super().__init__(f"LLM_{model_tier}")
        self.model_tier = model_tier
        self.session: aiohttp.ClientSession = None

    async def setup(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession()

    async def teardown(self):
        """Cleanup session"""
        if self.session:
            await self.session.close()

    async def run_single_test(self) -> float:
        """Make LLM request"""
        payload = {
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "model_tier": self.model_tier,
            "max_tokens": 10,
            "cache_strategy": "aggressive",
        }

        async with self.session.post(
            "http://localhost:8000/api/v1/llm/generate", json=payload
        ) as response:
            await response.json()
            response.raise_for_status()


class ConcurrentUsersBenchmark(PerformanceBenchmark):
    """Benchmark for concurrent user simulation"""

    def __init__(self, num_users: int = 10):
        super().__init__(f"Concurrent_{num_users}_users")
        self.num_users = num_users

    async def run_single_test(self) -> float:
        """Simulate concurrent users"""

        async def user_session(user_id: int):
            """Simulate single user session"""
            session = aiohttp.ClientSession()

            try:
                # User logs in
                await session.post(
                    "http://localhost:8000/api/v1/users",
                    json={"user_id": f"bench_user_{user_id}", "name": f"User {user_id}"},
                )

                # User performs various actions
                for _ in range(5):
                    # Get activities
                    await session.get(
                        f"http://localhost:8000/api/v1/users/bench_user_{user_id}/activities"
                    )

                    # Create activity
                    await session.post(
                        "http://localhost:8000/api/v1/activities",
                        json={
                            "user_id": f"bench_user_{user_id}",
                            "activity_type": "test",
                            "content": "Benchmark activity",
                        },
                    )

                    # Small delay
                    await asyncio.sleep(0.1)

            finally:
                await session.close()

        # Run user sessions concurrently
        tasks = [user_session(i) for i in range(self.num_users)]
        await asyncio.gather(*tasks, return_exceptions=True)


class BenchmarkSuite:
    """Complete benchmark suite runner"""

    def __init__(self):
        self.benchmarks: list[PerformanceBenchmark] = []
        self.results: list[BenchmarkResult] = []

    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add benchmark to suite"""
        self.benchmarks.append(benchmark)

    async def run_all(self, iterations: int = 100, concurrent: int = 1):
        """Run all benchmarks"""

        logger.info(f"Starting benchmark suite with {len(self.benchmarks)} tests")

        for benchmark in self.benchmarks:
            logger.info(f"Running benchmark: {benchmark.name}")

            try:
                result = await benchmark.run(iterations, concurrent)
                self.results.append(result)

                logger.info(
                    f"Completed {benchmark.name}: "
                    f"RPS={result.requests_per_second:.2f}, "
                    f"P95={result.p95_latency_ms:.2f}ms"
                )

            except Exception as e:
                logger.error(f"Benchmark {benchmark.name} failed: {e}")

    def generate_report(self) -> dict[str, Any]:
        """Generate performance report"""

        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": {
                "total_benchmarks": len(self.results),
                "passed": len([r for r in self.results if r.error_rate < 0.01]),
                "failed": len([r for r in self.results if r.error_rate >= 0.01]),
            },
            "benchmarks": [asdict(r) for r in self.results],
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> list[str]:
        """Generate performance recommendations"""

        recommendations = []

        for result in self.results:
            if result.p95_latency_ms > 1000:
                recommendations.append(
                    f"{result.test_name}: P95 latency > 1s, consider optimization"
                )

            if result.error_rate > 0.01:
                recommendations.append(
                    f"{result.test_name}: Error rate {result.error_rate:.1%}, investigate failures"
                )

            if result.requests_per_second < 10:
                recommendations.append(
                    f"{result.test_name}: Low throughput ({result.requests_per_second:.1f} RPS)"
                )

        return recommendations

    def save_report(self, filename: str = "benchmark_report.json"):
        """Save benchmark report to file"""
        report = self.generate_report()

        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Benchmark report saved to {filename}")


async def run_standard_benchmarks():
    """Run standard benchmark suite"""

    suite = BenchmarkSuite()

    # API Endpoint benchmarks
    suite.add_benchmark(APIEndpointBenchmark("/health"))
    suite.add_benchmark(
        APIEndpointBenchmark(
            "/api/v1/users", "POST", {"user_id": "bench_user", "name": "Benchmark User"}
        )
    )

    # Database benchmarks
    suite.add_benchmark(DatabaseQueryBenchmark("SELECT 1"))
    suite.add_benchmark(
        DatabaseQueryBenchmark("SELECT * FROM users WHERE user_id = $1", ("test_user",))
    )

    # Cache benchmarks
    suite.add_benchmark(CacheBenchmark("get"))
    suite.add_benchmark(CacheBenchmark("set"))

    # LLM Gateway benchmarks
    suite.add_benchmark(LLMGatewayBenchmark("economy"))
    suite.add_benchmark(LLMGatewayBenchmark("standard"))

    # Concurrent users benchmark
    suite.add_benchmark(ConcurrentUsersBenchmark(10))
    suite.add_benchmark(ConcurrentUsersBenchmark(50))

    # Run all benchmarks
    await suite.run_all(iterations=100, concurrent=10)

    # Generate and save report
    suite.save_report()

    return suite


if __name__ == "__main__":
    # Run benchmarks
    asyncio.run(run_standard_benchmarks())

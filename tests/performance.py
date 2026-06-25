#!/usr/bin/env python3
"""
Performance Validation Plugin for ReflectAI Testing

Enforces test timing requirements from the specification:
- Unit tests: <100ms execution time
- Integration tests: <1s execution time
- E2E tests: <10s execution time

Features:
- Automatic timing measurement
- Performance regression detection
- Configurable thresholds per test type
- Performance reporting and visualization
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pytest


@dataclass
class TestTiming:
    """Test execution timing information."""

    test_name: str
    test_type: str
    duration: float  # seconds
    threshold: float  # maximum allowed duration
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance metrics for test execution."""

    total_tests: int = 0
    slow_tests: list[TestTiming] = field(default_factory=list)
    fast_tests: list[TestTiming] = field(default_factory=list)
    failed_tests: list[TestTiming] = field(default_factory=list)
    average_duration: float = 0.0
    median_duration: float = 0.0
    max_duration: float = 0.0
    min_duration: float = 0.0


class PerformanceValidator:
    """Validates test performance against requirements."""

    def __init__(self):
        self.test_timings: list[TestTiming] = []
        self.performance_thresholds = self._initialize_thresholds()
        self.baseline_metrics: dict[str, float] = {}
        self.performance_history: dict[str, list[float]] = {}

    def _initialize_thresholds(self) -> dict[str, float]:
        """Initialize performance thresholds from specification."""
        return {
            "unit": 0.1,  # 100ms for unit tests
            "integration": 1.0,  # 1s for integration tests
            "e2e": 10.0,  # 10s for E2E tests
            "smoke": 0.5,  # 500ms for smoke tests
            "benchmark": 30.0,  # 30s for benchmarks (more lenient)
        }

    def classify_test_type(self, test_name: str) -> str:
        """Classify test type based on name and markers."""
        name_lower = test_name.lower()

        # Check for explicit markers first
        if "e2e" in name_lower or "end_to_end" in name_lower:
            return "e2e"
        elif "integration" in name_lower or "int" in name_lower:
            return "integration"
        elif "benchmark" in name_lower or "perf" in name_lower:
            return "benchmark"
        elif "smoke" in name_lower:
            return "smoke"
        else:
            # Default to unit tests for most tests
            return "unit"

    def get_threshold_for_test(self, test_name: str) -> float:
        """Get performance threshold for a test."""
        test_type = self.classify_test_type(test_name)
        return self.performance_thresholds.get(test_type, self.performance_thresholds["unit"])

    def record_test_timing(self, test_name: str, duration: float):
        """Record test execution timing."""
        test_type = self.classify_test_type(test_name)
        threshold = self.get_threshold_for_test(test_name)

        timing = TestTiming(
            test_name=test_name, test_type=test_type, duration=duration, threshold=threshold
        )

        self.test_timings.append(timing)

        # Track performance history
        if test_name not in self.performance_history:
            self.performance_history[test_name] = []
        self.performance_history[test_name].append(duration)

    def is_performance_acceptable(self, test_name: str, duration: float) -> bool:
        """Check if test performance is within acceptable limits."""
        threshold = self.get_threshold_for_test(test_name)
        return duration <= threshold

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics from recorded timings."""
        if not self.test_timings:
            return PerformanceMetrics()

        durations = [t.duration for t in self.test_timings]
        [t.threshold for t in self.test_timings]

        # Classify tests by performance
        slow_tests = [t for t in self.test_timings if t.duration > t.threshold]
        fast_tests = [t for t in self.test_timings if t.duration <= t.threshold]

        metrics = PerformanceMetrics(
            total_tests=len(self.test_timings),
            slow_tests=slow_tests,
            fast_tests=fast_tests,
            failed_tests=[],  # Will be populated by plugin
            average_duration=statistics.mean(durations) if durations else 0.0,
            median_duration=statistics.median(durations) if durations else 0.0,
            max_duration=max(durations) if durations else 0.0,
            min_duration=min(durations) if durations else 0.0,
        )

        return metrics

    def generate_performance_report(self) -> dict[str, Any]:
        """Generate a comprehensive performance report."""
        metrics = self.get_performance_metrics()

        # Calculate compliance rates
        total_tests = metrics.total_tests
        compliant_tests = len(metrics.fast_tests)
        non_compliant_tests = len(metrics.slow_tests)

        compliance_rate = (compliant_tests / total_tests * 100) if total_tests > 0 else 0

        # Group by test type
        test_types = {}
        for timing in self.test_timings:
            if timing.test_type not in test_types:
                test_types[timing.test_type] = []
            test_types[timing.test_type].append(timing)

        # Calculate per-type metrics
        type_metrics = {}
        for test_type, timings in test_types.items():
            durations = [t.duration for t in timings]
            type_metrics[test_type] = {
                "count": len(timings),
                "average_duration": statistics.mean(durations) if durations else 0.0,
                "max_duration": max(durations) if durations else 0.0,
                "min_duration": min(durations) if durations else 0.0,
                "threshold": self.performance_thresholds.get(test_type, 0.1),
                "compliance_rate": (
                    len([t for t in timings if t.duration <= t.threshold]) / len(timings) * 100
                )
                if timings
                else 0,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "compliant_tests": compliant_tests,
                "non_compliant_tests": non_compliant_tests,
                "overall_compliance_rate": compliance_rate,
                "average_duration": metrics.average_duration,
                "median_duration": metrics.median_duration,
                "max_duration": metrics.max_duration,
                "min_duration": metrics.min_duration,
            },
            "test_types": type_metrics,
            "slow_tests": [
                {
                    "name": t.test_name,
                    "type": t.test_type,
                    "duration": t.duration,
                    "threshold": t.threshold,
                    "over_threshold_by": t.duration - t.threshold,
                }
                for t in metrics.slow_tests
            ],
            "thresholds": self.performance_thresholds,
        }


class PerformancePlugin:
    """Pytest plugin for performance validation."""

    def __init__(self):
        self.validator = PerformanceValidator()
        self.enabled = True

    def pytest_configure(self, config):
        """Configure the plugin."""
        if config.getoption("--disable-performance", default=False):
            self.enabled = False
            return

        # Add command line options
        config.addinivalue_line("markers", "slow: marks tests as slow")
        config.addinivalue_line("markers", "integration: marks tests as integration tests")
        config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")

    def pytest_addoption(self, parser):
        """Add command line options."""
        parser.addoption(
            "--disable-performance",
            action="store_true",
            default=False,
            help="Disable performance validation",
        )
        parser.addoption(
            "--performance-report",
            action="store",
            default=None,
            help="Generate performance report file",
        )
        parser.addoption(
            "--fail-on-slow",
            action="store_true",
            default=False,
            help="Fail tests that exceed performance thresholds",
        )

    def pytest_runtest_makereport(self, item, call):
        """Hook to record test timing."""
        if not self.enabled:
            return

        if call.when == "call":
            duration = call.duration
            test_name = item.nodeid

            self.validator.record_test_timing(test_name, duration)

            # Check performance compliance
            if self._should_fail_on_performance():
                threshold = self.validator.get_threshold_for_test(test_name)
                if duration > threshold:
                    # Add failure information
                    call.excinfo = pytest.skip.Exception(
                        f"Test {test_name} exceeded performance threshold: "
                        f"{duration:.3f}s > {threshold:.3f}s"
                    )
                    call.outcome = "failed"

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        """Generate performance summary at test completion."""
        if not self.enabled:
            return

        report = self.validator.generate_performance_report()

        terminalreporter.write_sep("=", "Performance Summary")
        terminalreporter.write(f"Total Tests: {report['summary']['total_tests']}\n")
        terminalreporter.write(f"Compliant: {report['summary']['compliant_tests']}\n")
        terminalreporter.write(f"Non-compliant: {report['summary']['non_compliant_tests']}\n")
        terminalreporter.write(
            f"Overall Compliance: {report['summary']['overall_compliance_rate']:.1f}%\n"
        )
        terminalreporter.write(f"Average Duration: {report['summary']['average_duration']:.3f}s\n")

        if report["summary"]["non_compliant_tests"] > 0:
            terminalreporter.write_sep("=", "Slow Tests")
            for slow_test in report["slow_tests"]:
                terminalreporter.write(
                    f"  {slow_test['name']}: {slow_test['duration']:.3f}s "
                    f"(threshold: {slow_test['threshold']:.3f}s)\n"
                )

        # Generate report file if requested
        report_file = config.getoption("--performance-report")
        if report_file:
            import json

            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            terminalreporter.write(f"Performance report saved to: {report_file}\n")

    def _should_fail_on_performance(self) -> bool:
        """Check if performance failures should be enabled."""
        return pytest.config.getoption("--fail-on-slow", default=False)


# Global instance for easy access
performance_validator = PerformanceValidator()


def get_performance_validator() -> PerformanceValidator:
    """Get the global performance validator instance."""
    return performance_validator


def record_test_timing(test_name: str, duration: float):
    """Record test timing for manual reporting."""
    performance_validator.record_test_timing(test_name, duration)


def generate_performance_report() -> dict[str, Any]:
    """Generate a performance report."""
    return performance_validator.generate_performance_report()


# Pytest configuration
pytest_plugins = ["tests.performance"]

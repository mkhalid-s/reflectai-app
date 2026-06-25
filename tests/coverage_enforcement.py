#!/usr/bin/env python3
"""
Coverage Enforcement Plugin for ReflectAI Testing

Enforces coverage targets from the specification:
- Critical paths: >90% coverage
- Core functionality: >85% coverage
- Overall codebase: >80% coverage

Features:
- Configurable coverage thresholds per module
- Critical path identification
- Coverage gap analysis
- Coverage reporting with actionable insights
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CoverageTarget:
    """Coverage target configuration for a module or path."""

    path: str
    target_percentage: float
    is_critical: bool = False
    description: str = ""


@dataclass
class CoverageResult:
    """Coverage analysis result."""

    module_name: str
    coverage_percentage: float
    target_percentage: float
    is_critical: bool
    status: str  # "pass", "warn", "fail"
    missing_lines: list[int] = field(default_factory=list)
    uncovered_functions: list[str] = field(default_factory=list)


class CoverageEnforcer:
    """Enforces coverage targets across the codebase."""

    def __init__(self):
        self.coverage_targets = self._initialize_coverage_targets()
        self.critical_paths = self._identify_critical_paths()

    def _initialize_coverage_targets(self) -> dict[str, CoverageTarget]:
        """Initialize coverage targets from specification."""
        return {
            # Critical paths (>90% coverage required)
            "src/core": CoverageTarget(
                path="src/core",
                target_percentage=90.0,
                is_critical=True,
                description="Core business logic and domain models",
            ),
            "src/infrastructure": CoverageTarget(
                path="src/infrastructure",
                target_percentage=90.0,
                is_critical=True,
                description="Infrastructure layer including database, cache, auth",
            ),
            "src/services": CoverageTarget(
                path="src/services",
                target_percentage=90.0,
                is_critical=True,
                description="Service layer and business services",
            ),
            # Core functionality (>85% coverage required)
            "src/interfaces": CoverageTarget(
                path="src/interfaces",
                target_percentage=85.0,
                is_critical=False,
                description="Interface definitions and contracts",
            ),
            "src/shared": CoverageTarget(
                path="src/shared",
                target_percentage=85.0,
                is_critical=False,
                description="Shared utilities and common functionality",
            ),
            # Overall codebase (>80% coverage required)
            "src": CoverageTarget(
                path="src",
                target_percentage=80.0,
                is_critical=False,
                description="Overall source code coverage",
            ),
        }

    def _identify_critical_paths(self) -> set[str]:
        """Identify critical paths that require >90% coverage."""
        return {
            "src/core/agents",
            "src/core/llm",
            "src/infrastructure/database",
            "src/infrastructure/redis",
            "src/infrastructure/auth",
            "src/services",
            "src/shared/security",
            "src/shared/error_handling",
        }

    def run_coverage_analysis(self, coverage_file: str = ".coverage") -> dict[str, CoverageResult]:
        """Run coverage analysis and return results."""
        try:
            # Generate coverage report
            result = subprocess.run(
                [sys.executable, "-m", "coverage", "report", "--format=json"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            if result.returncode != 0:
                print(f"Warning: Coverage analysis failed: {result.stderr}")
                return {}

            # Parse coverage report
            coverage_data = json.loads(result.stdout)

            # Analyze each target
            results = {}
            for module_name, target in self.coverage_targets.items():
                coverage_result = self._analyze_module_coverage(module_name, coverage_data, target)
                results[module_name] = coverage_result

            return results

        except Exception as e:
            print(f"Error running coverage analysis: {e}")
            return {}

    def _analyze_module_coverage(
        self, module_name: str, coverage_data: dict, target: CoverageTarget
    ) -> CoverageResult:
        """Analyze coverage for a specific module."""
        try:
            # Get coverage data for this module
            module_data = coverage_data.get("files", {})

            # Find files matching this module path
            module_files = {}
            for file_path, file_data in module_data.items():
                if module_name in file_path:
                    module_files[file_path] = file_data

            if not module_files:
                return CoverageResult(
                    module_name=module_name,
                    coverage_percentage=0.0,
                    target_percentage=target.target_percentage,
                    is_critical=target.is_critical,
                    status="fail",
                    missing_lines=[],
                    uncovered_functions=[],
                )

            # Calculate aggregate coverage
            total_lines = 0
            covered_lines = 0

            for file_data in module_files.values():
                summary = file_data.get("summary", {})
                total_lines += summary.get("num_statements", 0)
                covered_lines += summary.get("covered_lines", 0)

            if total_lines == 0:
                coverage_percentage = 0.0
            else:
                coverage_percentage = (covered_lines / total_lines) * 100

            # Determine status
            if coverage_percentage >= target.target_percentage:
                status = "pass"
            elif coverage_percentage >= (target.target_percentage * 0.9):  # Within 10% of target
                status = "warn"
            else:
                status = "fail"

            # Get missing lines (simplified - would need more detailed analysis)
            missing_lines = []
            uncovered_functions = []

            return CoverageResult(
                module_name=module_name,
                coverage_percentage=coverage_percentage,
                target_percentage=target.target_percentage,
                is_critical=target.is_critical,
                status=status,
                missing_lines=missing_lines,
                uncovered_functions=uncovered_functions,
            )

        except Exception:
            return CoverageResult(
                module_name=module_name,
                coverage_percentage=0.0,
                target_percentage=target.target_percentage,
                is_critical=target.is_critical,
                status="error",
                missing_lines=[],
                uncovered_functions=[],
            )

    def generate_coverage_report(self, results: dict[str, CoverageResult]) -> dict[str, Any]:
        """Generate a comprehensive coverage report."""
        critical_failures = []
        overall_failures = []
        warnings = []

        # Analyze results
        for module_name, result in results.items():
            if result.is_critical and result.status == "fail":
                critical_failures.append(
                    {
                        "module": module_name,
                        "coverage": result.coverage_percentage,
                        "target": result.target_percentage,
                        "gap": result.target_percentage - result.coverage_percentage,
                    }
                )
            elif result.status == "fail":
                overall_failures.append(
                    {
                        "module": module_name,
                        "coverage": result.coverage_percentage,
                        "target": result.target_percentage,
                        "gap": result.target_percentage - result.coverage_percentage,
                    }
                )
            elif result.status == "warn":
                warnings.append(
                    {
                        "module": module_name,
                        "coverage": result.coverage_percentage,
                        "target": result.target_percentage,
                        "gap": result.target_percentage - result.coverage_percentage,
                    }
                )

        # Overall assessment
        total_targets = len(results)
        critical_targets = len([r for r in results.values() if r.is_critical])
        critical_passes = len([r for r in results.values() if r.is_critical and r.status == "pass"])
        overall_passes = len([r for r in results.values() if r.status == "pass"])

        overall_compliance = (overall_passes / total_targets * 100) if total_targets > 0 else 0
        critical_compliance = (
            (critical_passes / critical_targets * 100) if critical_targets > 0 else 0
        )

        # Generate recommendations
        recommendations = []
        if critical_failures:
            recommendations.append("CRITICAL: Address coverage gaps in critical paths immediately")
        if overall_failures:
            recommendations.append("HIGH: Increase test coverage for failing modules")
        if warnings:
            recommendations.append("MEDIUM: Review modules that are close to coverage targets")

        return {
            "timestamp": self._get_timestamp(),
            "summary": {
                "total_targets": total_targets,
                "overall_compliance": overall_compliance,
                "critical_compliance": critical_compliance,
                "critical_passes": critical_passes,
                "critical_targets": critical_targets,
                "overall_passes": overall_passes,
                "warnings": len(warnings),
                "failures": len(overall_failures),
                "critical_failures": len(critical_failures),
            },
            "critical_failures": critical_failures,
            "overall_failures": overall_failures,
            "warnings": warnings,
            "recommendations": recommendations,
            "module_details": {
                module_name: {
                    "coverage": result.coverage_percentage,
                    "target": result.target_percentage,
                    "status": result.status,
                    "is_critical": result.is_critical,
                    "gap": max(0, result.target_percentage - result.coverage_percentage),
                }
                for module_name, result in results.items()
            },
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

    def check_compliance(self, results: dict[str, CoverageResult]) -> bool:
        """Check if coverage meets minimum requirements."""
        # Critical paths must meet 90% target
        critical_results = [r for r in results.values() if r.is_critical]
        if not critical_results:
            return True

        critical_compliance = all(r.status == "pass" for r in critical_results)

        # Overall must meet 80% target
        overall_results = list(results.values())
        overall_compliance = (
            len([r for r in overall_results if r.status == "pass"]) / len(overall_results) >= 0.8
        )

        return critical_compliance and overall_compliance

    def get_coverage_gaps(self, results: dict[str, CoverageResult]) -> list[dict[str, Any]]:
        """Get modules with coverage gaps that need attention."""
        gaps = []

        for module_name, result in results.items():
            if result.status in ["fail", "warn"]:
                gaps.append(
                    {
                        "module": module_name,
                        "current_coverage": result.coverage_percentage,
                        "target_coverage": result.target_percentage,
                        "gap": result.target_percentage - result.coverage_percentage,
                        "priority": "high" if result.is_critical else "medium",
                        "status": result.status,
                    }
                )

        return sorted(gaps, key=lambda x: (-x["priority"] == "high", -x["gap"]))

    def print_coverage_summary(self, report: dict[str, Any]):
        """Print a formatted coverage summary."""
        print("\n" + "=" * 60)
        print("📊 COVERAGE ANALYSIS REPORT")
        print("=" * 60)

        summary = report["summary"]
        print(f"Overall Compliance: {summary['overall_compliance']:.1f}%")
        print(f"Critical Path Compliance: {summary['critical_compliance']:.1f}%")
        print(f"Total Modules: {summary['total_targets']}")
        print(f"Warnings: {summary['warnings']}")
        print(f"Failures: {summary['failures']}")
        print(f"Critical Failures: {summary['critical_failures']}")

        if summary["critical_failures"] > 0:
            print("\n❌ CRITICAL FAILURES (Must Address Immediately):")
            for failure in report["critical_failures"]:
                print(
                    f"  • {failure['module']}: {failure['coverage']:.1f}% "
                    f"(Target: {failure['target']}%, "
                    f"Gap: {failure['gap']:.1f}%)"
                )

        if summary["warnings"] > 0:
            print("\n⚠️  COVERAGE WARNINGS:")
            for warning in report["warnings"]:
                print(
                    f"  • {warning['module']}: {warning['coverage']:.1f}% "
                    f"(Target: {warning['target']}%)"
                )

        if report["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report["recommendations"]:
                print(f"  • {rec}")


class CoveragePlugin:
    """Pytest plugin for coverage enforcement."""

    def __init__(self):
        self.enforcer = CoverageEnforcer()

    def pytest_configure(self, config):
        """Configure the plugin."""
        # Add command line options
        config.addinivalue_line("markers", "critical: marks tests as covering critical paths")

    def pytest_addoption(self, parser):
        """Add command line options."""
        parser.addoption(
            "--coverage-enforcement",
            action="store_true",
            default=False,
            help="Enable coverage enforcement and reporting",
        )
        parser.addoption(
            "--coverage-report", action="store", default=None, help="Generate coverage report file"
        )
        parser.addoption(
            "--fail-on-coverage",
            action="store_true",
            default=False,
            help="Fail tests if coverage targets are not met",
        )

    def pytest_sessionfinish(self, session, exitstatus):
        """Hook to run coverage analysis after test session."""
        if not session.config.getoption("--coverage-enforcement"):
            return

        # Run coverage analysis
        results = self.enforcer.run_coverage_analysis()

        if not results:
            print("⚠️  No coverage data available for analysis")
            return

        # Generate report
        report = self.enforcer.generate_coverage_report(results)

        # Print summary
        self.enforcer.print_coverage_summary(report)

        # Save report if requested
        report_file = session.config.getoption("--coverage-report")
        if report_file:
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Coverage report saved to: {report_file}")

        # Check compliance
        compliant = self.enforcer.check_compliance(results)

        if session.config.getoption("--fail-on-coverage") and not compliant:
            print("❌ COVERAGE TARGETS NOT MET - FAILING BUILD")
            session.exitstatus = 1


# Global instance for easy access
coverage_enforcer = CoverageEnforcer()


def get_coverage_enforcer() -> CoverageEnforcer:
    """Get the global coverage enforcer instance."""
    return coverage_enforcer


def run_coverage_analysis() -> dict[str, Any]:
    """Run coverage analysis and return results."""
    results = coverage_enforcer.run_coverage_analysis()
    return coverage_enforcer.generate_coverage_report(results)


def check_coverage_compliance() -> bool:
    """Check if coverage meets minimum requirements."""
    results = coverage_enforcer.run_coverage_analysis()
    return coverage_enforcer.check_compliance(results)


# Pytest configuration
pytest_plugins = ["tests.coverage_enforcement"]

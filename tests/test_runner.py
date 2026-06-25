#!/usr/bin/env python3
"""
ReflectAI Test Runner

Comprehensive test runner for all phases of the ReflectAI implementation.
Provides organized test execution with reporting and phase-specific targeting.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class TestRunner:
    """Comprehensive test runner for ReflectAI"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.root_dir = self.test_dir.parent

    def run_all_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run all tests across all phases"""
        print("🚀 Running ReflectAI Comprehensive Test Suite")
        print("=" * 60)

        start_time = time.time()
        results = {}

        # Run tests by category
        test_categories = [
            ("unit", "Unit Tests"),
            ("integration", "Integration Tests"),
            ("e2e", "End-to-End Tests"),
        ]

        for category, description in test_categories:
            print(f"\n📋 Running {description}")
            print("-" * 40)

            result = self._run_pytest(markers=[category], verbose=verbose)
            results[category] = result

            if not result["success"]:
                print(f"❌ {description} failed!")
                if not verbose:
                    break
            else:
                print(f"✅ {description} passed!")

        # Run phase-specific tests
        print("\n📊 Running Phase-Specific Tests")
        print("-" * 40)

        phase_results = {}
        for phase in range(1, 6):
            phase_result = self.run_phase_tests(phase, verbose=verbose)
            phase_results[f"phase{phase}"] = phase_result

            if not phase_result["success"]:
                print(f"❌ Phase {phase} tests failed!")
                if not verbose:
                    break
            else:
                print(f"✅ Phase {phase} tests passed!")

        results["phases"] = phase_results

        # Performance tests
        print("\n⚡ Running Performance Tests")
        print("-" * 40)

        perf_result = self._run_pytest(markers=["performance"], verbose=verbose)
        results["performance"] = perf_result

        # Generate summary report
        end_time = time.time()
        total_time = end_time - start_time

        self._print_summary_report(results, total_time)

        return results

    def run_phase_tests(self, phase: int, verbose: bool = True) -> dict[str, Any]:
        """Run tests for a specific phase"""
        if not 1 <= phase <= 5:
            raise ValueError("Phase must be between 1 and 5")

        print(f"🔍 Running Phase {phase} Tests")

        # Map phases to their focus areas
        phase_descriptions = {
            1: "Security-First Foundation",
            2: "AI Agent Foundation",
            3: "Enhanced AI & Integrations",
            4: "Production Infrastructure",
            5: "Tool Framework & Business Logic",
        }

        print(f"📝 Focus: {phase_descriptions[phase]}")

        return self._run_pytest(markers=[f"phase{phase}"], verbose=verbose)

    def run_unit_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run only unit tests"""
        print("🧪 Running Unit Tests Only")
        return self._run_pytest(markers=["unit"], verbose=verbose)

    def run_integration_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run only integration tests"""
        print("🔗 Running Integration Tests Only")
        return self._run_pytest(markers=["integration"], verbose=verbose)

    def run_e2e_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run only end-to-end tests"""
        print("🎯 Running End-to-End Tests Only")
        return self._run_pytest(markers=["e2e"], verbose=verbose)

    def run_performance_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run only performance tests"""
        print("⚡ Running Performance Tests Only")
        return self._run_pytest(markers=["performance", "slow"], verbose=verbose)

    def run_security_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run only security-focused tests"""
        print("🔒 Running Security Tests Only")
        return self._run_pytest(markers=["security"], verbose=verbose)

    def run_smoke_tests(self, verbose: bool = True) -> dict[str, Any]:
        """Run smoke tests for quick validation"""
        print("💨 Running Smoke Tests (Quick Validation)")

        # Run a subset of critical tests from each phase
        smoke_test_patterns = [
            "tests/unit/phase1/test_configuration.py::TestConfiguration::test_app_config_creation",
            "tests/unit/phase2/test_agents.py::TestBaseAgent::test_base_agent_creation",
            "tests/unit/phase5/test_business_logic.py::TestCompetencyCalculationEngine::test_engine_initialization",
            "tests/integration/system/test_full_system_integration.py::TestFullSystemIntegration::test_configuration_integration",
        ]

        return self._run_pytest(test_paths=smoke_test_patterns, verbose=verbose)

    def _run_pytest(
        self,
        markers: list[str] | None = None,
        test_paths: list[str] | None = None,
        verbose: bool = True,
        additional_args: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run pytest with specified parameters"""

        cmd = ["python", "-m", "pytest"]

        # Add test paths or default to test directory
        if test_paths:
            cmd.extend(test_paths)
        else:
            cmd.append(str(self.test_dir))

        # Add markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # Add verbosity
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        # Add additional arguments
        if additional_args:
            cmd.extend(additional_args)

        # Add JSON report for parsing
        cmd.extend(["--tb=short", "--no-header"])

        try:
            # Change to project root directory
            result = subprocess.run(
                cmd,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Test execution timed out (10 minutes)",
                "command": " ".join(cmd),
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Test execution failed: {str(e)}",
                "command": " ".join(cmd),
            }

    def _print_summary_report(self, results: dict[str, Any], total_time: float):
        """Print comprehensive test summary report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY REPORT")
        print("=" * 60)

        # Overall status
        all_success = True
        total_categories = 0
        passed_categories = 0

        # Check main categories
        main_categories = ["unit", "integration", "e2e", "performance"]
        for category in main_categories:
            if category in results:
                total_categories += 1
                if results[category]["success"]:
                    passed_categories += 1
                else:
                    all_success = False

        # Check phase results
        if "phases" in results:
            for _phase_key, phase_result in results["phases"].items():
                total_categories += 1
                if phase_result["success"]:
                    passed_categories += 1
                else:
                    all_success = False

        # Print status summary
        status_emoji = "✅" if all_success else "❌"
        print(f"\n{status_emoji} Overall Status: {'PASSED' if all_success else 'FAILED'}")
        print(
            f"📈 Success Rate: {passed_categories}/{total_categories} ({(passed_categories / total_categories) * 100:.1f}%)"
        )
        print(f"⏱️  Total Time: {total_time:.2f} seconds")

        # Category breakdown
        print("\n📋 Category Results:")
        print("-" * 30)

        for category in ["unit", "integration", "e2e", "performance"]:
            if category in results:
                status = "✅ PASS" if results[category]["success"] else "❌ FAIL"
                print(f"  {category.title():<15}: {status}")

        # Phase breakdown
        print("\n🚀 Phase Results:")
        print("-" * 30)

        if "phases" in results:
            phase_names = {
                "phase1": "Security Foundation",
                "phase2": "AI Agent System",
                "phase3": "Enhanced AI & LLM",
                "phase4": "Infrastructure",
                "phase5": "Business Logic",
            }

            for phase_key, phase_result in results["phases"].items():
                phase_name = phase_names.get(phase_key, phase_key)
                status = "✅ PASS" if phase_result["success"] else "❌ FAIL"
                print(f"  {phase_name:<18}: {status}")

        # Failure details
        if not all_success:
            print("\n❌ Failure Details:")
            print("-" * 30)

            for category, result in results.items():
                if category == "phases":
                    for phase_key, phase_result in result.items():
                        if not phase_result["success"]:
                            print(
                                f"  {phase_key}: {phase_result.get('stderr', 'Unknown error')[:100]}..."
                            )
                elif not result["success"]:
                    print(f"  {category}: {result.get('stderr', 'Unknown error')[:100]}...")

        print("\n" + "=" * 60)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="ReflectAI Comprehensive Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                    # Run all tests
  python test_runner.py --phase 1          # Run Phase 1 tests only
  python test_runner.py --unit             # Run unit tests only
  python test_runner.py --integration      # Run integration tests only
  python test_runner.py --e2e              # Run e2e tests only
  python test_runner.py --performance      # Run performance tests only
  python test_runner.py --security         # Run security tests only
  python test_runner.py --smoke            # Run smoke tests only
  python test_runner.py --quiet            # Run with minimal output
        """,
    )

    parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3, 4, 5], help="Run tests for specific phase (1-5)"
    )

    parser.add_argument("--unit", action="store_true", help="Run unit tests only")

    parser.add_argument("--integration", action="store_true", help="Run integration tests only")

    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")

    parser.add_argument("--performance", action="store_true", help="Run performance tests only")

    parser.add_argument("--security", action="store_true", help="Run security tests only")

    parser.add_argument(
        "--smoke", action="store_true", help="Run smoke tests only (quick validation)"
    )

    parser.add_argument("--quiet", action="store_true", help="Run with minimal output")

    parser.add_argument(
        "--timeout", type=int, default=600, help="Test timeout in seconds (default: 600)"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = TestRunner()
    verbose = not args.quiet

    # Determine which tests to run
    results = None

    try:
        if args.phase:
            results = runner.run_phase_tests(args.phase, verbose=verbose)
        elif args.unit:
            results = runner.run_unit_tests(verbose=verbose)
        elif args.integration:
            results = runner.run_integration_tests(verbose=verbose)
        elif args.e2e:
            results = runner.run_e2e_tests(verbose=verbose)
        elif args.performance:
            results = runner.run_performance_tests(verbose=verbose)
        elif args.security:
            results = runner.run_security_tests(verbose=verbose)
        elif args.smoke:
            results = runner.run_smoke_tests(verbose=verbose)
        else:
            # Run all tests
            results = runner.run_all_tests(verbose=verbose)

        # Determine exit code
        if isinstance(results, dict):
            if "success" in results:
                exit_code = 0 if results["success"] else 1
            else:
                # Multiple test categories
                exit_code = (
                    0
                    if all(
                        result.get("success", False)
                        for result in results.values()
                        if isinstance(result, dict)
                    )
                    else 1
                )
        else:
            exit_code = 1

        print(f"\n🎯 Test execution completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test execution failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

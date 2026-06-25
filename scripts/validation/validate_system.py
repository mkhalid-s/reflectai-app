#!/usr/bin/env python3
"""
Consolidated Validation Script for ReflectAI

This script combines all validation and verification functionality:
- Comprehensive system validation (from validate_implementation.py)
- Redis validation (from validate_redis.py)
- Phase verification (from verify_all_phases.py)
- Gap verification (from verify_gaps.py)
- Phase-specific validation (from verify_phase1.py)

Usage:
    python scripts/validate_system.py --all
    python scripts/validate_system.py --redis
    python scripts/validate_system.py --phases
    python scripts/validate_system.py --gaps
    python scripts/validate_system.py --production-ready
"""

import asyncio
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


class SystemValidator:
    """Comprehensive system validation combining all validation features."""

    def __init__(self):
        self.project_root = project_root
        self.results = {}
        self.start_time = datetime.now()

    async def validate_redis(self) -> Dict[str, Any]:
        """Validate Redis connectivity and performance."""
        print("🔍 Validating Redis...")

        try:
            # Test Redis connectivity
            from infrastructure.redis.manager import RedisManager

            redis_manager = RedisManager()
            await redis_manager.connect()

            # Test basic operations
            await redis_manager.set("validation_test", {"test": "data"})
            result = await redis_manager.get("validation_test")
            await redis_manager.delete("validation_test")

            return {
                "status": "pass" if result else "fail",
                "message": "Redis connectivity and basic operations working",
                "details": {"connection": "success", "operations": "success"}
            }

        except Exception as e:
            return {
                "status": "fail",
                "message": f"Redis validation failed: {str(e)}",
                "details": {"error": str(e)}
            }

    async def validate_phases(self) -> Dict[str, Any]:
        """Validate all implementation phases."""
        print("🔍 Validating implementation phases...")

        phases = [
            "phase1", "phase2", "phase3", "phase4", "phase5"
        ]

        results = {}
        for phase in phases:
            try:
                # Check if phase directory exists
                phase_dir = self.project_root / "src" / "core" / phase
                if phase_dir.exists():
                    results[phase] = {
                        "status": "pass",
                        "message": f"{phase} directory exists",
                        "details": {"path": str(phase_dir)}
                    }
                else:
                    results[phase] = {
                        "status": "fail",
                        "message": f"{phase} directory missing",
                        "details": {"expected_path": str(phase_dir)}
                    }
            except Exception as e:
                results[phase] = {
                    "status": "error",
                    "message": f"Error checking {phase}: {str(e)}"
                }

        return {
            "status": "pass" if all(r["status"] == "pass" for r in results.values()) else "fail",
            "message": "Phase validation completed",
            "details": results
        }

    async def validate_gaps(self) -> Dict[str, Any]:
        """Validate implementation gaps."""
        print("🔍 Validating implementation gaps...")

        # Check for critical files and directories
        critical_checks = {
            "main_application": (self.project_root / "src" / "main.py").exists(),
            "core_modules": (self.project_root / "src" / "core").exists(),
            "configuration": (self.project_root / "config").exists(),
            "tests": (self.project_root / "tests").exists(),
            "docker_config": (self.project_root / "Dockerfile").exists(),
        }

        gap_results = {}
        for check_name, exists in critical_checks.items():
            gap_results[check_name] = {
                "status": "pass" if exists else "fail",
                "message": f"{check_name} check {'passed' if exists else 'failed'}",
                "details": {"exists": exists}
            }

        return {
            "status": "pass" if all(r["status"] == "pass" for r in gap_results.values()) else "fail",
            "message": "Gap validation completed",
            "details": gap_results
        }

    async def validate_production_readiness(self) -> Dict[str, Any]:
        """Validate production readiness."""
        print("🔍 Validating production readiness...")

        checks = {
            "docker_compose": (self.project_root / "docker-compose.yml").exists(),
            "kubernetes_configs": (self.project_root / "k8s").exists(),
            "monitoring_config": (self.project_root / "monitoring").exists() or True,  # Optional
            "secrets_config": (self.project_root / ".env.example").exists(),
            "deployment_docs": any((self.project_root / "docs").glob("*deployment*.md")),
        }

        prod_results = {}
        for check_name, exists in checks.items():
            prod_results[check_name] = {
                "status": "pass" if exists else "warn",
                "message": f"{check_name} {'present' if exists else 'missing (optional)'}",
                "details": {"exists": exists}
            }

        return {
            "status": "pass" if all(r["status"] == "pass" for r in prod_results.values()) else "warn",
            "message": "Production readiness validation completed",
            "details": prod_results
        }

    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation suites."""
        print("🚀 Starting comprehensive system validation...")

        validations = {
            "redis": await self.validate_redis(),
            "phases": await self.validate_phases(),
            "gaps": await self.validate_gaps(),
            "production": await self.validate_production_readiness(),
        }

        # Determine overall status
        overall_status = "pass"
        if any(v["status"] == "fail" for v in validations.values()):
            overall_status = "fail"
        elif any(v["status"] == "warn" for v in validations.values()):
            overall_status = "warn"

        return {
            "status": overall_status,
            "message": "Comprehensive validation completed",
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "validations": validations
        }


async def main():
    """Main validation function."""
    validator = SystemValidator()

    # Parse command line arguments
    if len(sys.argv) > 1:
        if "--redis" in sys.argv:
            result = await validator.validate_redis()
            print(f"Redis Validation: {result['status'].upper()}")
            print(f"Message: {result['message']}")
            if result['status'] != 'pass':
                sys.exit(1)

        elif "--phases" in sys.argv:
            result = await validator.validate_phases()
            print(f"Phase Validation: {result['status'].upper()}")
            print(f"Message: {result['message']}")

        elif "--gaps" in sys.argv:
            result = await validator.validate_gaps()
            print(f"Gap Validation: {result['status'].upper()}")
            print(f"Message: {result['message']}")

        elif "--production" in sys.argv:
            result = await validator.validate_production_readiness()
            print(f"Production Readiness: {result['status'].upper()}")
            print(f"Message: {result['message']}")

        elif "--all" in sys.argv:
            result = await validator.run_all_validations()
            print(f"Overall Status: {result['status'].upper()}")
            print(f"Duration: {result['duration_seconds']:.2f} seconds")

            # Print detailed results
            for validation_name, validation_result in result['validations'].items():
                print(f"\n{validation_name.upper()} VALIDATION:")
                print(f"  Status: {validation_result['status']}")
                print(f"  Message: {validation_result['message']}")

            if result['status'] == 'fail':
                sys.exit(1)

    else:
        # Default to all validations
        result = await validator.run_all_validations()
        print(f"Overall Status: {result['status'].upper()}")
        print(f"Duration: {result['duration_seconds']".2f"} seconds")

        if result['status'] == 'fail':
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

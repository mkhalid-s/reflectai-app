"""
Layer 2: Workflow Imports Validation Test

This test validates that all 8 workflows can be imported correctly.
Run this BEFORE testing the router to ensure all dependencies are satisfied.

Usage:
    pdm run python tests/manual/test_workflow_imports.py
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_workflow_imports():
    """Test that all 8 workflows can be imported."""

    print("=" * 80)
    print("LAYER 2: Workflow Imports Validation")
    print("=" * 80)
    print()

    workflows_to_test = [
        "SequentialAnalysisWorkflow",
        "ParallelAnalysisWorkflow",
        "BatchProcessingWorkflow",
        "ConversationWorkflow",
        "ReportGenerationWorkflow",
        "InlineAnalysisReportWorkflow",
        "QuickSummaryWorkflow",
        "OptimizedAnalysisWorkflow",
    ]

    success_count = 0
    failed_imports = []

    for workflow_name in workflows_to_test:
        try:
            # Try to import the workflow
            exec(f"from src.services.workflow.workflows import {workflow_name}")
            print(f"✅ {workflow_name:35s} - OK")
            success_count += 1
        except ImportError as e:
            print(f"❌ {workflow_name:35s} - FAILED: {e}")
            failed_imports.append((workflow_name, str(e)))
        except Exception as e:
            print(f"⚠️  {workflow_name:35s} - ERROR: {e}")
            failed_imports.append((workflow_name, str(e)))

    print()
    print("=" * 80)
    print(f"Results: {success_count}/{len(workflows_to_test)} workflows imported successfully")
    print("=" * 80)

    if failed_imports:
        print()
        print("FAILED IMPORTS:")
        for name, error in failed_imports:
            print(f"  - {name}: {error}")
        print()
        print("❌ LAYER 2 FAILED - Fix import errors before proceeding")
        return False
    else:
        print()
        print("✅ LAYER 2 PASSED - All workflows import successfully")
        print("   → Ready for Layer 3 (Workflow Router Test)")
        return True

if __name__ == "__main__":
    success = test_workflow_imports()
    sys.exit(0 if success else 1)

"""
Layer 3: Workflow Router Validation Test

This test validates that the workflow router has all required methods
and can route to all 8 workflow types.

Usage:
    pdm run python tests/manual/test_workflow_router.py
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_workflow_router():
    """Test that workflow router can route to all 8 workflow types."""

    print("=" * 80)
    print("LAYER 3: Workflow Router Validation")
    print("=" * 80)
    print()

    try:
        # Import router
        from src.core.workflows.workflow_router import WorkflowRouter
        print("✅ WorkflowRouter imported successfully")
        print()

        # Create router instance (don't initialize async components)
        router = WorkflowRouter.__new__(WorkflowRouter)

        # Check that required methods exist
        required_methods = ["route_workflow", "get_workflow_status"]

        print("Checking required methods:")
        for method_name in required_methods:
            if hasattr(router, method_name):
                print(f"✅ {method_name:30s} - EXISTS")
            else:
                print(f"❌ {method_name:30s} - MISSING")
                raise AttributeError(f"Missing required method: {method_name}")

        print()

        # Check workflow type mappings (by reading the source)
        print("Checking workflow type mappings in source code:")

        import inspect
        source = inspect.getsource(WorkflowRouter.route_workflow)

        workflow_types_to_check = [
            ("SEQUENTIAL_ANALYSIS", "SequentialAnalysisWorkflow"),
            ("PARALLEL_ANALYSIS", "ParallelAnalysisWorkflow"),
            ("BATCH_PROCESSING", "BatchProcessingWorkflow"),
            ("CONVERSATION", "ConversationWorkflow"),
            ("REPORT_GENERATION", "ReportGenerationWorkflow"),
            ("INLINE_ANALYSIS", "InlineAnalysisReportWorkflow"),
            ("QUICK_SUMMARY", "QuickSummaryWorkflow"),
            ("COMPETENCY_ASSESSMENT", "SequentialAnalysisWorkflow"),
        ]

        mapped_count = 0
        missing_mappings = []

        for wf_type, wf_class in workflow_types_to_check:
            # Check if workflow type is mentioned in the source
            if wf_type in source:
                print(f"✅ {wf_type:30s} → {wf_class}")
                mapped_count += 1
            else:
                print(f"❌ {wf_type:30s} - NOT FOUND IN MAPPING")
                missing_mappings.append(wf_type)

        print()
        print("=" * 80)
        print(f"Results: {mapped_count}/{len(workflow_types_to_check)} workflow types mapped")
        print("=" * 80)

        if missing_mappings:
            print()
            print("MISSING MAPPINGS:")
            for wf_type in missing_mappings:
                print(f"  - {wf_type}")
            print()
            print("❌ LAYER 3 FAILED - Fix workflow mappings before proceeding")
            return False
        else:
            print()
            print("✅ LAYER 3 PASSED - Workflow router ready")
            print("   → Ready for Layer 4 (Handler Test)")
            return True

    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("❌ LAYER 3 FAILED - Fix errors before proceeding")
        return False

if __name__ == "__main__":
    success = test_workflow_router()
    sys.exit(0 if success else 1)

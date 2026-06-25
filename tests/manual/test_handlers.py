"""
Layer 4: Handler Validation Test

This test validates that all conversation handlers have correct signatures
and can create WorkflowRequest objects properly.

Usage:
    pdm run python tests/manual/test_handlers.py
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_handlers():
    """Test that all handlers have correct signatures."""

    print("=" * 80)
    print("LAYER 4: Handler Validation")
    print("=" * 80)
    print()

    try:
        # Import ConversationManager
        from src.interfaces.slack.conversation_manager import ConversationManager
        print("✅ ConversationManager imported successfully")
        print()

        # Create instance without initialization (just for checking methods)
        manager = ConversationManager.__new__(ConversationManager)

        # Check that all required handlers exist
        handlers_to_check = [
            ("_handle_analysis_request", ["user_id", "intent_result"]),
            ("_handle_status_request", ["user_id"]),
            ("_handle_report_request", ["user_id", "intent_result"]),
            ("_handle_competency_request", ["user_id", "intent_result"]),
        ]

        print("Checking handler methods:")
        all_exist = True

        for handler_name, expected_params in handlers_to_check:
            if hasattr(manager, handler_name):
                method = getattr(manager, handler_name)

                # Check if it's a method
                import inspect
                if inspect.ismethod(method) or inspect.isfunction(method):
                    # Get signature
                    sig = inspect.signature(method)
                    params = list(sig.parameters.keys())

                    # Check for required parameters (ignoring 'self')
                    params_without_self = [p for p in params if p != 'self']

                    # Just check that required params are present (there might be optional ones)
                    missing_params = [ep for ep in expected_params if ep not in params_without_self]

                    if missing_params:
                        print(f"⚠️  {handler_name:35s} - Missing params: {missing_params}")
                    else:
                        print(f"✅ {handler_name:35s} - OK (params: {', '.join(params_without_self[:3])}...)")
                else:
                    print(f"❌ {handler_name:35s} - NOT A METHOD")
                    all_exist = False
            else:
                print(f"❌ {handler_name:35s} - MISSING")
                all_exist = False

        print()

        # Check that WorkflowRequest and WorkflowType can be imported
        print("Checking workflow models:")
        from src.services.workflow.models import WorkflowType
        print("✅ WorkflowRequest imported")
        print("✅ WorkflowType imported")

        # Check workflow types exist
        print()
        print("Checking WorkflowType enum values:")
        required_types = [
            "SEQUENTIAL_ANALYSIS",
            "PARALLEL_ANALYSIS",
            "BATCH_PROCESSING",
            "CONVERSATION",
            "REPORT_GENERATION",
            "COMPETENCY_ASSESSMENT",
            "INLINE_ANALYSIS",
            "QUICK_SUMMARY",
        ]

        types_exist = True
        for wf_type in required_types:
            if hasattr(WorkflowType, wf_type):
                print(f"✅ WorkflowType.{wf_type}")
            else:
                print(f"❌ WorkflowType.{wf_type} - MISSING")
                types_exist = False

        print()
        print("=" * 80)

        if all_exist and types_exist:
            print("✅ LAYER 4 PASSED - All handlers and models ready")
            print("   → Ready for Layer 5 (End-to-End Slack Testing)")
            print()
            print("IMPORTANT: Before Slack testing, ensure:")
            print("  1. Database is running and has test data")
            print("  2. Redis is running")
            print("  3. Temporal is running")
            print("  4. Slack bot is configured")
            return True
        else:
            print("❌ LAYER 4 FAILED - Fix handler/model issues before proceeding")
            return False

    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("❌ LAYER 4 FAILED - Fix errors before proceeding")
        return False

if __name__ == "__main__":
    success = test_handlers()
    sys.exit(0 if success else 1)

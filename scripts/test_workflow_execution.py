#!/usr/bin/env python3
"""
REAL Test: Actually Execute a Workflow

This is NOT a validation test. This ACTUALLY runs a workflow end-to-end.
"""

import asyncio
import sys
import uuid
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_real_workflow():
    """Actually execute a workflow and see if it works"""
    from src.core.workflows.workflow_router import WorkflowRouter
    from src.services.workflow.models import WorkflowRequest, WorkflowType

    print("=" * 80)
    print("REAL WORKFLOW EXECUTION TEST")
    print("=" * 80)
    print()

    print("🔄 Creating WorkflowRouter...")
    router = WorkflowRouter()
    await router.initialize()
    print("✅ WorkflowRouter initialized")
    print()

    print("🔄 Creating test workflow request (INLINE_ANALYSIS)...")
    print("   This tests Journey 4: Inline Analysis")
    print("   Content: 'I implemented OAuth2 authentication for microservices'")
    print()

    workflow_request = WorkflowRequest(
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        user_id="11111111-1111-1111-1111-111111111111",  # Alice from test data
        team_id="T123TEAM",
        correlation_id=f"test-{uuid.uuid4()}",
        input_data={
            "inline_content": "I implemented OAuth2 authentication for microservices",
            "content_metadata": {
                "extraction_method": "test",
                "confidence": 1.0,
                "source": "direct_test"
            },
            "output_format": "json",
            "include_gap_analysis": True,
        },
    )

    print("🔄 Routing workflow to Temporal...")
    try:
        result = await router.route_workflow(workflow_request, user_id=workflow_request.user_id)
        print("✅ Workflow started!")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Decision: {result.decision}")
        print(f"   Message: {result.message}")
        print()

        print("🔄 Checking workflow status (will poll for 30 seconds)...")
        for i in range(15):  # Poll for 30 seconds (15 x 2 sec)
            await asyncio.sleep(2)
            status_dict = await router.get_workflow_status(result.workflow_id)

            status_value = status_dict.get("status", "UNKNOWN") if status_dict else "UNKNOWN"
            print(f"   [{i*2:2d}s] Status: {status_value}")

            if status_dict and status_value in ["COMPLETED", "FAILED", "CANCELLED"]:
                print()
                if status_value == "COMPLETED":
                    print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
                    print()
                    print("Result:")
                    print(f"{status_dict.get('result')}")
                    return True
                else:
                    print(f"❌ WORKFLOW FAILED: {status_value}")
                    if status_dict.get("error"):
                        print(f"   Error: {status_dict.get('error')}")
                    return False

        print()
        print("⏱️  Workflow still running after 30 seconds")
        print("   This might be normal for complex workflows")
        print("   Check Temporal UI: http://localhost:8088")
        return None

    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_real_workflow())

    print()
    print("=" * 80)
    if result is True:
        print("✅ TEST PASSED - Workflow executed successfully")
        sys.exit(0)
    elif result is False:
        print("❌ TEST FAILED - Workflow encountered errors")
        sys.exit(1)
    else:
        print("⏱️  TEST TIMEOUT - Check Temporal UI for results")
        sys.exit(2)

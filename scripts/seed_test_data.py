#!/usr/bin/env python3
"""
Seed Test Data for ReflectAI Database

Creates minimal test data for testing the 5 journeys:
- 2 test users
- 15-20 activities per user
- Sample competencies

Usage:
    pdm run python scripts/seed_test_data.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def seed_database():
    """Seed test data into database"""
    import asyncpg

    print("=" * 80)
    print("ReflectAI Test Data Seeding")
    print("=" * 80)
    print()

    try:
        # Connect to database
        print("🔄 Connecting to database...")
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="reflectai",
            user="reflectai",
            password="devpassword"
        )
        print("✅ Connected to database")
        print()

        # Clear existing test data
        print("🔄 Clearing existing test data...")
        await conn.execute("TRUNCATE users CASCADE")
        print("✅ Existing data cleared")
        print()

        # Create test users
        print("🔄 Creating test users...")

        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()

        await conn.execute("""
            INSERT INTO users (
                id, slack_user_id, email, display_name, real_name, team_id,
                timezone, is_active, created_at, updated_at
            ) VALUES
                ($1, 'U123TEST01', 'alice@example.com', 'Alice', 'Alice Smith', 'T123TEAM', 'UTC', true, now(), now()),
                ($2, 'U123TEST02', 'bob@example.com', 'Bob', 'Bob Johnson', 'T123TEAM', 'UTC', true, now(), now())
        """, user1_id, user2_id)

        print(f"✅ Created 2 test users:")
        print(f"   - Alice (user_id: {user1_id})")
        print(f"   - Bob   (user_id: {user2_id})")
        print()

        # Create activities for Alice
        print("🔄 Creating activities for Alice...")

        activity_templates = [
            ("Implemented OAuth2 authentication for microservices", "code_development"),
            ("Reviewed PR #123 - Database migration improvements", "code_review"),
            ("Fixed production bug in payment processing", "bug_fix"),
            ("Led technical design discussion for new API", "technical_leadership"),
            ("Mentored junior developer on REST API best practices", "mentoring"),
            ("Deployed v2.5.0 to production", "deployment"),
            ("Wrote documentation for authentication service", "documentation"),
            ("Participated in architecture review meeting", "collaboration"),
            ("Optimized database queries reducing latency by 40%", "performance_optimization"),
            ("Created CI/CD pipeline for automated testing", "devops"),
            ("Conducted security audit of payment system", "security"),
            ("Presented technical demo to stakeholders", "communication"),
            ("Refactored legacy code to improve maintainability", "refactoring"),
            ("Debugged complex race condition in async code", "problem_solving"),
            ("Implemented Redis caching layer", "code_development"),
            ("Updated API documentation with OpenAPI spec", "documentation"),
            ("Helped team member resolve Docker issues", "collaboration"),
            ("Analyzed performance metrics and created report", "analysis"),
            ("Fixed critical security vulnerability", "security"),
            ("Designed database schema for new feature", "technical_design"),
        ]

        activities_inserted = 0
        for i, (content, activity_type) in enumerate(activity_templates):
            # Spread activities over last 30 days
            days_ago = 30 - (i * 1.5)
            timestamp = datetime.utcnow() - timedelta(days=days_ago)

            activity_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO activities (
                    id, user_id, content, activity_type, source, classification,
                    metrics, processing_status, confidence_score, competency_areas,
                    timestamp, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, 'slack', $5, $6, 'complete', 0.85, $7, $8, $8, $8
                )
            """,
                activity_id,
                user1_id,
                content,
                activity_type,
                '{}',  # classification
                '{"complexity": "medium"}',  # metrics
                ['technical_skill', 'problem_solving'],  # competency_areas
                timestamp
            )
            activities_inserted += 1

        print(f"✅ Created {activities_inserted} activities for Alice")
        print()

        # Create activities for Bob
        print("🔄 Creating activities for Bob...")

        bob_activities = activity_templates[:10]  # First 10 activities for Bob
        activities_inserted = 0

        for i, (content, activity_type) in enumerate(bob_activities):
            days_ago = 20 - (i * 2)
            timestamp = datetime.utcnow() - timedelta(days=days_ago)

            activity_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO activities (
                    id, user_id, content, activity_type, source, classification,
                    metrics, processing_status, confidence_score, competency_areas,
                    timestamp, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, 'slack', $5, $6, 'complete', 0.80, $7, $8, $8, $8
                )
            """,
                activity_id,
                user2_id,
                content,
                activity_type,
                '{}',
                '{"complexity": "medium"}',
                ['technical_skill'],
                timestamp
            )
            activities_inserted += 1

        print(f"✅ Created {activities_inserted} activities for Bob")
        print()

        # Create competencies for Alice
        print("🔄 Creating competencies for Alice...")

        competencies = [
            ("python_programming", "Python Programming", Decimal("3.75")),
            ("system_design", "System Design", Decimal("3.50")),
            ("api_development", "API Development", Decimal("4.00")),
            ("security", "Security", Decimal("3.25")),
            ("leadership", "Technical Leadership", Decimal("2.75")),
        ]

        for competency_id, competency_name, current_level in competencies:
            comp_uuid = uuid.uuid4()
            await conn.execute("""
                INSERT INTO competencies (
                    id, user_id, competency_id, competency_name, current_level,
                    target_level, evidence_count, trend_direction, trend_strength,
                    last_calculated_at, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, 5, 'improving', 0.7, now(), now(), now()
                )
            """,
                comp_uuid,
                user1_id,
                competency_id,
                competency_name,
                current_level,
                Decimal("4.50")  # target_level
            )

        print(f"✅ Created {len(competencies)} competencies for Alice")
        print()

        # Close connection
        await conn.close()

        print("=" * 80)
        print("✅ Test data seeded successfully!")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - Users: 2 (Alice, Bob)")
        print(f"  - Activities: 30 total (20 for Alice, 10 for Bob)")
        print(f"  - Competencies: 5 for Alice")
        print()
        print("Next steps:")
        print("  1. Start Temporal: docker-compose up -d temporal")
        print("  2. Start application: ./rai run app")
        print("  3. Test journeys in Slack")
        print()

        return True

    except Exception as e:
        print()
        print(f"❌ Error seeding data: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(seed_database())
    sys.exit(0 if success else 1)

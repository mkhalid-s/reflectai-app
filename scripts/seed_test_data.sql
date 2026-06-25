-- ReflectAI Test Data Seed
-- Creates minimal test data for testing the 5 journeys

-- Clear existing test data
TRUNCATE users CASCADE;

-- Create test users
INSERT INTO users (
    id, slack_user_id, email, display_name, real_name, team_id,
    timezone, is_active, created_at, updated_at
) VALUES
    ('11111111-1111-1111-1111-111111111111', 'U123TEST01', 'alice@example.com', 'Alice', 'Alice Smith', 'T123TEAM', 'UTC', true, now(), now()),
    ('22222222-2222-2222-2222-222222222222', 'U123TEST02', 'bob@example.com', 'Bob', 'Bob Johnson', 'T123TEAM', 'UTC', true, now(), now());

-- Create activities for Alice (last 30 days)
INSERT INTO activities (
    id, user_id, content, activity_type, source, classification,
    metrics, processing_status, confidence_score, competency_areas,
    timestamp, created_at, updated_at
) VALUES
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Implemented OAuth2 authentication for microservices', 'code_development', 'slack', '{}', '{"complexity": "high"}', 'complete', 0.90, ARRAY['technical_skill', 'security'], now() - interval '2 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Reviewed PR #123 - Database migration improvements', 'code_review', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.85, ARRAY['technical_skill', 'collaboration'], now() - interval '4 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Fixed production bug in payment processing', 'bug_fix', 'slack', '{}', '{"complexity": "high"}', 'complete', 0.88, ARRAY['problem_solving', 'debugging'], now() - interval '5 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Led technical design discussion for new API', 'technical_leadership', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.85, ARRAY['leadership', 'communication'], now() - interval '7 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Mentored junior developer on REST API best practices', 'mentoring', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.80, ARRAY['leadership', 'mentoring'], now() - interval '9 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Deployed v2.5.0 to production', 'deployment', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.85, ARRAY['devops', 'technical_skill'], now() - interval '11 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Wrote documentation for authentication service', 'documentation', 'slack', '{}', '{"complexity": "low"}', 'complete', 0.75, ARRAY['communication', 'documentation'], now() - interval '13 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Participated in architecture review meeting', 'collaboration', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.80, ARRAY['collaboration', 'architecture'], now() - interval '15 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Optimized database queries reducing latency by 40%', 'performance_optimization', 'slack', '{}', '{"complexity": "high"}', 'complete', 0.90, ARRAY['performance', 'database'], now() - interval '17 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Created CI/CD pipeline for automated testing', 'devops', 'slack', '{}', '{"complexity": "high"}', 'complete', 0.88, ARRAY['devops', 'automation'], now() - interval '19 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Conducted security audit of payment system', 'security', 'slack', '{}', '{"complexity": "high"}', 'complete', 0.92, ARRAY['security', 'compliance'], now() - interval '21 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Presented technical demo to stakeholders', 'communication', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.85, ARRAY['communication', 'presentation'], now() - interval '23 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Refactored legacy code to improve maintainability', 'refactoring', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.82, ARRAY['code_quality', 'refactoring'], now() - interval '25 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Debugged complex race condition in async code', 'problem_solving', 'slack', '{}', '{"complexity": "high"}', 'complete', 0.90, ARRAY['debugging', 'async_programming'], now() - interval '27 days', now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'Implemented Redis caching layer', 'code_development', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.85, ARRAY['caching', 'performance'], now() - interval '29 days', now(), now());

-- Create activities for Bob (last 20 days)
INSERT INTO activities (
    id, user_id, content, activity_type, source, classification,
    metrics, processing_status, confidence_score, competency_areas,
    timestamp, created_at, updated_at
) VALUES
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'Fixed bug in user authentication flow', 'bug_fix', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.80, ARRAY['debugging', 'security'], now() - interval '2 days', now(), now()),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'Updated API documentation', 'documentation', 'slack', '{}', '{"complexity": "low"}', 'complete', 0.75, ARRAY['documentation'], now() - interval '5 days', now(), now()),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'Implemented new dashboard feature', 'code_development', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.82, ARRAY['frontend', 'ui_development'], now() - interval '8 days', now(), now()),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'Reviewed code for pull request #456', 'code_review', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.80, ARRAY['code_review', 'collaboration'], now() - interval '11 days', now(), now()),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'Added unit tests for payment module', 'testing', 'slack', '{}', '{"complexity": "medium"}', 'complete', 0.78, ARRAY['testing', 'quality_assurance'], now() - interval '14 days', now(), now());

-- Create competencies for Alice
INSERT INTO competencies (
    id, user_id, competency_id, competency_name, current_level,
    target_level, evidence_count, trend_direction, trend_strength,
    last_calculated_at, created_at, updated_at
) VALUES
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'python_programming', 'Python Programming', 3.75, 4.50, 8, 'improving', 0.7, now(), now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'system_design', 'System Design', 3.50, 4.50, 6, 'improving', 0.6, now(), now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'api_development', 'API Development', 4.00, 4.50, 9, 'stable', 0.5, now(), now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'security', 'Security', 3.25, 4.00, 5, 'improving', 0.65, now(), now(), now()),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'leadership', 'Technical Leadership', 2.75, 3.50, 4, 'improving', 0.55, now(), now(), now());

-- Create competencies for Bob
INSERT INTO competencies (
    id, user_id, competency_id, competency_name, current_level,
    target_level, evidence_count, trend_direction, trend_strength,
    last_calculated_at, created_at, updated_at
) VALUES
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'frontend_development', 'Frontend Development', 3.00, 4.00, 5, 'improving', 0.6, now(), now(), now()),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', 'testing', 'Testing & QA', 2.50, 3.50, 3, 'stable', 0.4, now(), now(), now());

-- Verify data
SELECT 'Test data seeded successfully!' AS status;
SELECT 'Users:' AS category, COUNT(*) AS count FROM users;
SELECT 'Activities:' AS category, COUNT(*) AS count FROM activities;
SELECT 'Competencies:' AS category, COUNT(*) AS count FROM competencies;

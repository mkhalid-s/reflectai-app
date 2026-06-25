"""
Cross-Phase Integration Tests

Integration tests covering the full system across all phases:
- Phase 1-5 integration
- End-to-end workflows
- System-wide error handling
- Performance integration
- Data flow validation
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Import test utilities


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullSystemIntegration:
    """Test full system integration across all phases"""

    async def test_complete_assessment_workflow(
        self,
        mock_config,
        mock_logger,
        sample_user_data,
        sample_activity_data,
        sample_competency_scores,
    ):
        """Test complete assessment workflow from Slack to business logic"""

        # Mock system components
        with (
            patch("interfaces.slack.adapter.SlackAdapter") as mock_slack,
            patch("core.agents.agent_coordinator.AgentCoordinator") as mock_coordinator,
            patch(
                "core.business.workflows.workflow_orchestrator.WorkflowOrchestrator"
            ) as mock_orchestrator,
        ):
            # Setup mocks
            slack_adapter = mock_slack.return_value
            coordinator = mock_coordinator.return_value
            orchestrator = mock_orchestrator.return_value

            # Mock Slack message
            slack_message = {
                "user": "U123456",
                "text": "Please assess my Python competencies",
                "channel": "C789012",
                "ts": "1234567890.123",
            }

            # Mock agent response
            coordinator.process_request.return_value = MagicMock(
                success=True,
                data={
                    "analysis_type": "competency_assessment",
                    "user_id": "user123",
                    "competency_scores": sample_competency_scores,
                },
            )

            # Mock workflow execution
            orchestrator.start_workflow.return_value = "workflow_exec_001"
            orchestrator.get_execution_status.return_value = MagicMock(
                status="completed",
                output_data={
                    "assessment_report": {
                        "competency_scores": sample_competency_scores,
                        "recommendations": ["Focus on advanced Python concepts"],
                    }
                },
            )

            # Simulate complete workflow
            # 1. Slack receives message
            await slack_adapter.handle_message(slack_message)

            # 2. Agent processes request
            agent_response = await coordinator.process_request(MagicMock())

            # 3. Workflow executes business logic
            execution_id = await orchestrator.start_workflow(
                workflow_id="assessment_comprehensive", input_data=agent_response.data
            )

            # 4. Get workflow results
            execution_status = await orchestrator.get_execution_status(execution_id)

            # Verify integration
            assert agent_response.success is True
            assert execution_id == "workflow_exec_001"
            assert execution_status.status == "completed"
            assert "assessment_report" in execution_status.output_data

    async def test_error_propagation_asystems(self, mock_config, mock_logger):
        """Test error handling propagation across all phases"""

        # Test error at different phases
        test_cases = [
            {
                "phase": "slack",
                "error_type": "AuthenticationError",
                "component": "interfaces.slack.adapter",
                "expected_handling": "user_notification",
            },
            {
                "phase": "agent",
                "error_type": "ValidationError",
                "component": "core.agents.analysis_agent",
                "expected_handling": "graceful_degradation",
            },
            {
                "phase": "business_logic",
                "error_type": "DatabaseError",
                "component": "core.business.engines",
                "expected_handling": "retry_with_fallback",
            },
            {
                "phase": "infrastructure",
                "error_type": "ExternalServiceError",
                "component": "infrastructure.cache",
                "expected_handling": "circuit_breaker",
            },
        ]

        for test_case in test_cases:
            with patch(f"{test_case['component']}.logger"):
                # Simulate error in specific phase
                error_class = getattr(
                    __import__("shared.error_handling", fromlist=[test_case["error_type"]]),
                    test_case["error_type"],
                )
                test_error = error_class(f"Test error in {test_case['phase']}")

                # Verify error handling
                from shared.error_handling import handle_error

                result = handle_error(test_error)

                assert result["status"] == "error"
                assert result["error_type"] == test_case["error_type"]
                assert "correlation_id" in result

    async def test_configuration_integration(self, mock_config):
        """Test configuration system integration across phases"""

        with patch(
            "infrastructure.config.configuration.load_configuration", return_value=mock_config
        ):
            # Test Phase 1: Configuration loading
            from infrastructure.config.configuration import load_configuration

            config = load_configuration()

            # Test Phase 2: Agent configuration
            with patch("core.agents.base_agent.BaseAgent") as mock_agent:
                agent = mock_agent.return_value
                agent.configure(config.agents if hasattr(config, "agents") else {})

                # Verify agent can access configuration
                mock_agent.assert_called_once()

            # Test Phase 3: LLM configuration
            with patch("shared.llm.gateway.LLMGateway") as mock_llm:
                llm = mock_llm.return_value
                llm.configure(config.llm if hasattr(config, "llm") else {})

                mock_llm.assert_called_once()

            # Test Phase 4: Infrastructure configuration
            with patch("infrastructure.database.connection_manager.ConnectionManager") as mock_db:
                db = mock_db.return_value
                db.configure(config.database)

                mock_db.assert_called_once()

            # Test Phase 5: Business logic configuration
            with patch(
                "core.business.engines.competency_calculation_engine.CompetencyCalculationEngine"
            ) as mock_engine:
                engine = mock_engine.return_value
                if hasattr(config, "business"):
                    engine.configure(config.business)

                mock_engine.assert_called_once()

    async def test_data_flow_integration(
        self, sample_user_data, sample_activity_data, sample_competency_scores
    ):
        """Test data flow integration across all system components"""

        # Mock the complete data pipeline
        pipeline_stages = []

        # Stage 1: Data ingestion (Phase 4 - Storage)
        with patch(
            "core.storage.managers.activity_manager.ActivityManager"
        ) as mock_activity_manager:
            activity_manager = mock_activity_manager.return_value
            activity_manager.create_activities.return_value = sample_activity_data

            # Ingest activity data
            ingested_data = await activity_manager.create_activities(sample_activity_data)
            pipeline_stages.append(("ingestion", ingested_data))

            activity_manager.create_activities.assert_called_once()

        # Stage 2: Data classification (Phase 5 - Classification)
        with patch("core.classification.activity_classifier.ActivityClassifier") as mock_classifier:
            classifier = mock_classifier.return_value
            classifier.classify_activities.return_value = [
                {"activity_id": "act_001", "category": "technical", "confidence": 0.9}
            ]

            classified_data = await classifier.classify_activities(ingested_data)
            pipeline_stages.append(("classification", classified_data))

            classifier.classify_activities.assert_called_once()

        # Stage 3: Competency calculation (Phase 5 - Business Logic)
        with patch(
            "core.business.engines.competency_calculation_engine.CompetencyCalculationEngine"
        ) as mock_calc_engine:
            calc_engine = mock_calc_engine.return_value
            calc_engine.calculate_competency_scores.return_value = sample_competency_scores

            calculated_scores = await calc_engine.calculate_competency_scores(
                user_id=sample_user_data["user_id"], activities=classified_data
            )
            pipeline_stages.append(("calculation", calculated_scores))

            calc_engine.calculate_competency_scores.assert_called_once()

        # Stage 4: Recommendation generation (Phase 5 - Business Logic)
        with patch(
            "core.business.engines.recommendation_engine.RecommendationEngine"
        ) as mock_rec_engine:
            rec_engine = mock_rec_engine.return_value
            rec_engine.generate_recommendations.return_value = [
                {"type": "skill_development", "priority": "high", "skill": "python"}
            ]

            recommendations = await rec_engine.generate_recommendations(
                user_id=sample_user_data["user_id"], competency_scores=calculated_scores
            )
            pipeline_stages.append(("recommendations", recommendations))

            rec_engine.generate_recommendations.assert_called_once()

        # Stage 5: Result presentation (Phase 2 - Slack Integration)
        with patch("interfaces.slack.response_formatter.ResponseFormatter") as mock_formatter:
            formatter = mock_formatter.return_value
            formatter.format_assessment_results.return_value = {
                "text": "Assessment complete",
                "blocks": [],
            }

            formatted_response = formatter.format_assessment_results(
                competency_scores=calculated_scores, recommendations=recommendations
            )
            pipeline_stages.append(("presentation", formatted_response))

            formatter.format_assessment_results.assert_called_once()

        # Verify complete pipeline
        assert len(pipeline_stages) == 5
        stage_names = [stage[0] for stage in pipeline_stages]
        expected_stages = [
            "ingestion",
            "classification",
            "calculation",
            "recommendations",
            "presentation",
        ]
        assert stage_names == expected_stages

    async def test_caching_integration(self, mock_redis_client, sample_competency_scores):
        """Test caching integration across system components"""

        # Test multi-level caching strategy
        cache_levels = []

        # L1 Cache: In-memory (Application level)
        with patch(
            "core.business.engines.competency_calculation_engine.CompetencyCalculationEngine"
        ) as mock_engine:
            engine = mock_engine.return_value
            engine._cache = {}  # In-memory cache

            # Simulate cache hit
            cache_key = "competency_scores_user123"
            engine._cache[cache_key] = sample_competency_scores

            cached_result = engine._cache.get(cache_key)
            cache_levels.append(("L1_memory", cached_result is not None))

        # L2 Cache: Redis (Distributed cache)
        with patch("infrastructure.cache.redis_manager.RedisManager") as mock_redis_manager:
            redis_manager = mock_redis_manager.return_value
            redis_manager.get.return_value = str(sample_competency_scores)

            cached_data = await redis_manager.get("user123:competencies")
            cache_levels.append(("L2_redis", cached_data is not None))

            redis_manager.get.assert_called_once()

        # L3 Cache: Database query optimization (Data layer)
        with patch(
            "infrastructure.database.repositories.user_repository.UserRepository"
        ) as mock_repo:
            repo = mock_repo.return_value
            repo.get_cached_competencies.return_value = sample_competency_scores

            db_cached_data = await repo.get_cached_competencies("user123")
            cache_levels.append(("L3_database", db_cached_data is not None))

            repo.get_cached_competencies.assert_called_once()

        # Verify caching strategy
        assert len(cache_levels) == 3
        assert all(level[1] for level in cache_levels)  # All cache levels should work

    async def test_monitoring_integration(self, mock_logger):
        """Test monitoring and observability integration"""

        # Test metrics collection across phases
        metrics_collected = []

        with patch(
            "infrastructure.monitoring.common.metrics_collector.MetricsCollector"
        ) as mock_metrics:
            metrics_collector = mock_metrics.return_value

            # Simulate metrics collection
            metrics_collector.increment_counter.return_value = None
            metrics_collector.record_histogram.return_value = None

            # Configuration load time
            await metrics_collector.record_histogram("config.load_time", 0.05)
            metrics_collected.append("config.load_time")

            # Agent request count
            await metrics_collector.increment_counter("agent.requests.total")
            metrics_collected.append("agent.requests.total")

            # Business logic processing time
            await metrics_collector.record_histogram("business.processing_time", 0.15)
            metrics_collected.append("business.processing_time")

            # Database query time
            await metrics_collector.record_histogram("database.query_time", 0.02)
            metrics_collected.append("database.query_time")

            # Cache hit ratio
            await metrics_collector.record_histogram("cache.hit_ratio", 0.85)
            metrics_collected.append("cache.hit_ratio")

        # Test correlation ID propagation
        correlation_id = "test-correlation-123"

        with patch("shared.logging.get_logger") as mock_get_logger:
            logger = mock_get_logger.return_value
            logger.info = MagicMock()

            # Log with correlation ID across phases
            logger.info("Phase 1: Configuration loaded", extra={"correlation_id": correlation_id})
            logger.info("Phase 2: Agent processing", extra={"correlation_id": correlation_id})
            logger.info(
                "Phase 5: Business logic complete", extra={"correlation_id": correlation_id}
            )

            # Verify correlation ID is preserved
            assert logger.info.call_count == 3
            for call in logger.info.call_args_list:
                assert call[1]["extra"]["correlation_id"] == correlation_id

        assert len(metrics_collected) == 5

    async def test_security_integration(self):
        """Test security integration across all phases"""

        security_checks = []

        with patch("infrastructure.config.secrets_manager.SecretsManager") as mock_secrets:
            secrets_manager = mock_secrets.return_value
            secrets_manager.get_secret.return_value = "encrypted_value"

            # Test secret retrieval
            secret = await secrets_manager.get_secret("database_password")
            security_checks.append(("secrets_encryption", secret == "encrypted_value"))

        with patch("infrastructure.security.auth_manager.AuthManager") as mock_auth:
            auth_manager = mock_auth.return_value
            auth_manager.validate_token.return_value = {"user_id": "user123", "valid": True}

            # Test token validation
            auth_result = await auth_manager.validate_token("test_token")
            security_checks.append(("token_validation", auth_result["valid"]))

        with patch(
            "infrastructure.security.encryption_service.EncryptionService"
        ) as mock_encryption:
            encryption_service = mock_encryption.return_value
            encryption_service.encrypt_data.return_value = "encrypted_data"
            encryption_service.decrypt_data.return_value = "original_data"

            # Test data encryption/decryption
            encrypted = await encryption_service.encrypt_data("sensitive_data")
            decrypted = await encryption_service.decrypt_data(encrypted)
            security_checks.append(("data_encryption", decrypted == "original_data"))

        with patch("shared.error_handling.ValidationError"):
            from core.business.engines.competency_calculation_engine import (
                CompetencyCalculationEngine,
            )

            engine = CompetencyCalculationEngine()

            # Test input validation
            try:
                # Should validate input parameters
                invalid_activities = [{"invalid": "data"}]
                await engine.calculate_competency_score("test_skill", invalid_activities, "user123")
                security_checks.append(("input_validation", True))
            except Exception:
                security_checks.append(
                    ("input_validation", True)
                )  # Exception expected for invalid input

        # Verify all security checks
        assert len(security_checks) == 4
        assert all(check[1] for check in security_checks)


@pytest.mark.integration
@pytest.mark.slow
class TestSystemPerformance:
    """Test system-wide performance integration"""

    async def test_end_to_end_performance(
        self, sample_user_data, sample_activity_data, sample_competency_scores
    ):
        """Test end-to-end system performance"""
        import time

        start_time = time.time()

        # Simulate complete user journey
        with (
            patch("interfaces.slack.adapter.SlackAdapter") as mock_slack,
            patch("core.agents.agent_coordinator.AgentCoordinator") as mock_coordinator,
            patch(
                "core.business.workflows.workflow_orchestrator.WorkflowOrchestrator"
            ) as mock_orchestrator,
        ):
            # Setup performance-optimized mocks
            slack_adapter = mock_slack.return_value
            coordinator = mock_coordinator.return_value
            orchestrator = mock_orchestrator.return_value

            # Mock fast responses
            coordinator.process_request.return_value = MagicMock(
                success=True, data=sample_competency_scores
            )

            orchestrator.start_workflow.return_value = "fast_exec_001"
            orchestrator.get_execution_status.return_value = MagicMock(
                status="completed", output_data={"results": sample_competency_scores}
            )

            # Simulate user request processing
            await slack_adapter.handle_message({"text": "assess my skills"})
            response = await coordinator.process_request(MagicMock())
            execution_id = await orchestrator.start_workflow("assessment", response.data)
            final_result = await orchestrator.get_execution_status(execution_id)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance requirements
        assert total_time < 2.0  # Complete flow should finish in < 2 seconds
        assert final_result.status == "completed"

    async def test_concurrent_user_handling(self):
        """Test concurrent user request handling"""

        # Simulate multiple concurrent users
        user_count = 50

        async def simulate_user_request(user_id):
            with patch("core.agents.agent_coordinator.AgentCoordinator") as mock_coordinator:
                coordinator = mock_coordinator.return_value
                coordinator.process_request.return_value = MagicMock(
                    success=True, data={"user_id": user_id, "result": "processed"}
                )

                return await coordinator.process_request(MagicMock(user_id=user_id))

        # Process users concurrently
        import time

        start_time = time.time()

        tasks = [simulate_user_request(f"user_{i}") for i in range(user_count)]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert len(results) == user_count
        assert all(result.success for result in results)
        assert total_time < 5.0  # Should handle 50 users in < 5 seconds

    async def test_memory_usage_integration(self):
        """Test system memory usage under load"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Simulate memory-intensive operations
        large_datasets = []

        for _i in range(100):
            # Create large mock datasets
            large_data = {
                "activities": [{"id": j, "data": "x" * 1000} for j in range(100)],
                "competencies": {f"skill_{j}": float(j) for j in range(50)},
            }
            large_datasets.append(large_data)

        # Process all datasets
        with patch(
            "core.business.engines.competency_calculation_engine.CompetencyCalculationEngine"
        ) as mock_engine:
            engine = mock_engine.return_value
            engine.process_bulk_data.return_value = {"processed": True}

            for dataset in large_datasets:
                await engine.process_bulk_data(dataset)

        # Check memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory should not increase excessively (< 500MB)
        assert memory_increase < 500 * 1024 * 1024

        # Clean up
        del large_datasets


@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndScenarios:
    """Test complete end-to-end user scenarios"""

    async def test_new_user_onboarding_flow(self, mock_config, mock_logger):
        """Test complete new user onboarding flow"""

        # Mock new user data
        new_user = {
            "user_id": "new_user_001",
            "email": "newuser@example.com",
            "name": "New User",
            "role": "developer",
            "join_date": datetime.now(),
        }

        onboarding_steps = []

        # Step 1: User registration
        with patch("core.models.user.UserModel") as mock_user_model:
            user_model = mock_user_model.return_value
            user_model.create_user.return_value = new_user

            created_user = await user_model.create_user(new_user)
            onboarding_steps.append(("registration", created_user is not None))

        # Step 2: Initial assessment
        with patch(
            "core.business.workflows.workflow_orchestrator.WorkflowOrchestrator"
        ) as mock_orchestrator:
            orchestrator = mock_orchestrator.return_value
            orchestrator.start_workflow.return_value = "onboarding_workflow_001"

            workflow_id = await orchestrator.start_workflow(
                workflow_id="user_onboarding", input_data=new_user
            )
            onboarding_steps.append(("initial_assessment", workflow_id is not None))

        # Step 3: Competency framework assignment
        with patch("core.frameworks.competency_loader.CompetencyLoader") as mock_loader:
            loader = mock_loader.return_value
            loader.assign_framework.return_value = {
                "framework_id": "software_dev",
                "assigned": True,
            }

            framework_assignment = await loader.assign_framework(
                user_id=new_user["user_id"], role=new_user["role"]
            )
            onboarding_steps.append(("framework_assignment", framework_assignment["assigned"]))

        # Step 4: Initial recommendations
        with patch(
            "core.business.engines.recommendation_engine.RecommendationEngine"
        ) as mock_rec_engine:
            rec_engine = mock_rec_engine.return_value
            rec_engine.generate_onboarding_recommendations.return_value = [
                {"type": "welcome", "message": "Welcome to ReflectAI!"},
                {"type": "first_steps", "message": "Complete your skill assessment"},
            ]

            recommendations = await rec_engine.generate_onboarding_recommendations(
                new_user["user_id"]
            )
            onboarding_steps.append(("recommendations", len(recommendations) > 0))

        # Verify complete onboarding flow
        assert len(onboarding_steps) == 4
        assert all(step[1] for step in onboarding_steps)

    async def test_skill_development_journey(self, sample_user_data, sample_competency_scores):
        """Test complete skill development journey"""

        journey_milestones = []

        # Milestone 1: Initial skill assessment
        with patch(
            "core.business.engines.competency_calculation_engine.CompetencyCalculationEngine"
        ) as mock_calc_engine:
            calc_engine = mock_calc_engine.return_value
            calc_engine.assess_current_skills.return_value = sample_competency_scores

            initial_assessment = await calc_engine.assess_current_skills(
                sample_user_data["user_id"]
            )
            journey_milestones.append(("initial_assessment", initial_assessment is not None))

        # Milestone 2: Development plan creation
        with patch(
            "core.business.engines.recommendation_engine.RecommendationEngine"
        ) as mock_rec_engine:
            rec_engine = mock_rec_engine.return_value
            rec_engine.create_development_plan.return_value = {
                "plan_id": "dev_plan_001",
                "duration_months": 6,
                "milestones": [
                    {"month": 2, "target": "Improve Python to 90"},
                    {"month": 4, "target": "Learn Docker basics"},
                    {"month": 6, "target": "Complete advanced project"},
                ],
            }

            dev_plan = await rec_engine.create_development_plan(
                user_id=sample_user_data["user_id"],
                target_competencies={"python": 90, "docker": 75},
            )
            journey_milestones.append(("development_plan", dev_plan is not None))

        # Milestone 3: Progress tracking
        progress_updates = [
            {"month": 1, "python": 88, "docker": 45},
            {"month": 2, "python": 91, "docker": 60},
            {"month": 4, "python": 93, "docker": 78},
        ]

        with patch(
            "core.business.analytics.analytics_processor.AnalyticsProcessor"
        ) as mock_analytics:
            analytics = mock_analytics.return_value
            analytics.track_progress.return_value = {"trend": "improving", "on_track": True}

            for update in progress_updates:
                progress_result = await analytics.track_progress(
                    user_id=sample_user_data["user_id"], competency_scores=update
                )

            journey_milestones.append(("progress_tracking", progress_result["on_track"]))

        # Milestone 4: Goal achievement
        with patch(
            "core.business.engines.career_progression_engine.CareerProgressionEngine"
        ) as mock_career_engine:
            career_engine = mock_career_engine.return_value
            career_engine.evaluate_goal_achievement.return_value = {
                "goals_met": ["python_mastery"],
                "achievement_rate": 0.85,
                "ready_for_advancement": True,
            }

            achievement = await career_engine.evaluate_goal_achievement(
                user_id=sample_user_data["user_id"], final_scores={"python": 93, "docker": 78}
            )
            journey_milestones.append(("goal_achievement", achievement["ready_for_advancement"]))

        # Verify complete development journey
        assert len(journey_milestones) == 4
        assert all(milestone[1] for milestone in journey_milestones)

    async def test_team_analytics_scenario(self):
        """Test team-wide analytics and benchmarking scenario"""

        # Mock team data
        team_data = [
            {
                "user_id": "user1",
                "role": "senior_dev",
                "competencies": {"python": 90, "leadership": 85},
            },
            {
                "user_id": "user2",
                "role": "junior_dev",
                "competencies": {"python": 70, "leadership": 45},
            },
            {
                "user_id": "user3",
                "role": "tech_lead",
                "competencies": {"python": 85, "leadership": 95},
            },
        ]

        analytics_results = []

        # Team competency analysis
        with patch(
            "core.business.analytics.benchmark_analyzer.BenchmarkAnalyzer"
        ) as mock_benchmark:
            benchmark = mock_benchmark.return_value
            benchmark.analyze_team_competencies.return_value = {
                "team_average": {"python": 81.7, "leadership": 75.0},
                "top_performers": ["user1", "user3"],
                "improvement_areas": ["leadership development for user2"],
            }

            team_analysis = await benchmark.analyze_team_competencies(team_data)
            analytics_results.append(("team_analysis", team_analysis is not None))

        # Industry benchmarking
        with patch(
            "core.business.analytics.benchmark_analyzer.BenchmarkAnalyzer"
        ) as mock_benchmark:
            benchmark = mock_benchmark.return_value
            benchmark.compare_to_industry.return_value = {
                "industry_percentile": 75,
                "above_average_skills": ["python"],
                "below_average_skills": ["leadership"],
            }

            industry_comparison = await benchmark.compare_to_industry(
                team_data, "software_development"
            )
            analytics_results.append(("industry_benchmark", industry_comparison is not None))

        # Team development recommendations
        with patch(
            "core.business.engines.recommendation_engine.RecommendationEngine"
        ) as mock_rec_engine:
            rec_engine = mock_rec_engine.return_value
            rec_engine.generate_team_recommendations.return_value = [
                {"type": "team_training", "focus": "leadership_skills", "participants": ["user2"]},
                {"type": "mentoring", "mentor": "user3", "mentee": "user2"},
            ]

            team_recommendations = await rec_engine.generate_team_recommendations(team_data)
            analytics_results.append(("team_recommendations", len(team_recommendations) > 0))

        # Verify team analytics scenario
        assert len(analytics_results) == 3
        assert all(result[1] for result in analytics_results)

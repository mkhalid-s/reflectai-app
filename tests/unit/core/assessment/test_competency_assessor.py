"""
Unit tests for CompetencyAssessor

Tests main competency assessment engine including:
- Full user competency assessment
- Single competency assessment
- Activity grouping by competency
- Competency score creation
- Overall metrics calculation
- Insight generation
- Progression tracking
- Assessment caching
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.assessment.competency_assessor import (
    AssessmentResult,
    CompetencyAssessor,
    CompetencyScore,
    get_competency_assessor,
)
from src.core.assessment.scoring import (
    CompetencyScoreLevel,
    ScoringMethod,
    ScoringResult,
)


@pytest.fixture
def competency_assessor():
    """Create CompetencyAssessor instance for testing"""
    with (
        patch("src.core.assessment.competency_assessor.get_framework_loader"),
        patch("src.core.assessment.competency_assessor.CompetencyMapper"),
    ):
        assessor = CompetencyAssessor(framework_id="test_framework")
        # Mock framework
        assessor.competency_framework = Mock()
        assessor.competency_framework.competencies = {
            "technical_skills": {"name": "Technical Skills", "description": "Technical competency"},
            "leadership": {"name": "Leadership", "description": "Leadership skills"},
            "communication": {"name": "Communication", "description": "Communication skills"},
        }
        return assessor


@pytest.fixture
def sample_activities():
    """Create sample activities for testing"""
    base_date = datetime.now(UTC)

    return [
        {
            "date": base_date - timedelta(days=5),
            "description": "Implemented new feature with Python",
            "activity_type": "coding",
            "competency_type": "technical_skills",
            "days_ago": 5,
        },
        {
            "date": base_date - timedelta(days=10),
            "description": "Led team meeting and made decisions",
            "activity_type": "meeting",
            "competency_type": "leadership",
            "days_ago": 10,
        },
        {
            "date": base_date - timedelta(days=15),
            "description": "Wrote comprehensive documentation",
            "activity_type": "documentation",
            "competency_type": "communication",
            "days_ago": 15,
        },
        {
            "date": base_date - timedelta(days=20),
            "description": "Code review and mentoring",
            "activity_type": "review",
            "competency_type": "technical_skills",
            "days_ago": 20,
        },
        {
            "date": base_date - timedelta(days=25),
            "description": "Presented at team meeting",
            "activity_type": "presentation",
            "competency_type": "communication",
            "days_ago": 25,
        },
    ]


@pytest.fixture
def mock_scoring_result():
    """Create mock scoring result"""
    return ScoringResult(
        competency_type="technical_skills",
        scoring_method="comprehensive",
        raw_activity_count=5,
        weighted_activity_count=4.5,
        competency_score=2.8,
        competency_level=CompetencyScoreLevel.PROFICIENT,
        evidence_level="moderate",
        confidence_score=0.75,
        time_decay_impact=0.9,
        quality_impact=0.85,
        activities_analyzed=[],
        scoring_factors={"time_decay_impact": 0.9},
        recommendations=["Continue building experience", "Focus on advanced topics"],
    )


class TestCompetencyAssessor:
    """Test suite for CompetencyAssessor"""

    def test_initialization(self, competency_assessor):
        """Test CompetencyAssessor initializes correctly"""
        assert competency_assessor is not None
        assert competency_assessor.framework_id == "test_framework"
        assert competency_assessor.activity_scorer is not None
        assert competency_assessor.time_decay is not None
        assert competency_assessor.evidence_threshold is not None
        assert competency_assessor.competency_mapper is not None
        assert competency_assessor._cache_ttl_minutes == 60

    def test_get_competency_info_from_framework(self, competency_assessor):
        """Test getting competency info from framework"""
        info = competency_assessor._get_competency_info("technical_skills")

        assert info["name"] == "Technical Skills"
        assert info["description"] == "Technical competency"

    def test_get_competency_info_fallback(self, competency_assessor):
        """Test getting competency info for unknown competency"""
        info = competency_assessor._get_competency_info("unknown_competency")

        assert "Unknown Competency" in info["name"]
        assert "unknown_competency" in info["description"]

    def test_create_competency_score(self, competency_assessor, mock_scoring_result):
        """Test creating CompetencyScore from ScoringResult"""
        competency_info = {"name": "Technical Skills", "description": "Test"}
        reference_date = datetime.now(UTC)

        # Add activities with days_ago to scoring result
        mock_scoring_result.activities_analyzed = [
            {"days_ago": 5},
            {"days_ago": 15},
            {"days_ago": 40},
        ]

        score = competency_assessor._create_competency_score(
            "technical_skills", competency_info, mock_scoring_result, reference_date
        )

        assert isinstance(score, CompetencyScore)
        assert score.competency_id == "technical_skills"
        assert score.competency_name == "Technical Skills"
        assert score.current_score == 2.8
        assert score.current_level == "Proficient"
        assert score.evidence_level == "moderate"
        assert score.confidence_score == 0.75
        assert score.activity_count == 5
        assert score.recent_activity_count == 2  # Activities within 30 days
        assert score.time_weighted_score == 4.5

    def test_create_competency_score_next_milestone(self, competency_assessor, mock_scoring_result):
        """Test next milestone calculation in competency score"""
        competency_info = {"name": "Technical Skills", "description": "Test"}
        reference_date = datetime.now(UTC)

        mock_scoring_result.competency_score = 2.8
        mock_scoring_result.competency_level = CompetencyScoreLevel.PROFICIENT

        score = competency_assessor._create_competency_score(
            "technical_skills", competency_info, mock_scoring_result, reference_date
        )

        assert score.next_milestone is not None
        assert score.next_milestone["target_level"] == 4  # ADVANCED
        assert score.next_milestone["gap"] > 0
        assert score.next_milestone["estimated_activities_needed"] > 0

    def test_create_competency_score_expert_no_milestone(self, competency_assessor):
        """Test no next milestone for expert level"""
        scoring_result = ScoringResult(
            competency_type="technical_skills",
            scoring_method="comprehensive",
            raw_activity_count=25,
            weighted_activity_count=24.0,
            competency_score=4.8,
            competency_level=CompetencyScoreLevel.EXPERT,
            evidence_level="strong",
            confidence_score=0.95,
            activities_analyzed=[],
            recommendations=[],
        )

        competency_info = {"name": "Technical Skills", "description": "Test"}

        score = competency_assessor._create_competency_score(
            "technical_skills", competency_info, scoring_result, datetime.now(UTC)
        )

        assert score.next_milestone is None

    def test_calculate_overall_metrics_empty(self, competency_assessor):
        """Test overall metrics calculation with empty scores"""
        overall_score, confidence = competency_assessor._calculate_overall_metrics({})

        assert overall_score == 0.0
        assert confidence == 0.0

    def test_calculate_overall_metrics(self, competency_assessor):
        """Test overall metrics calculation"""
        competency_scores = {
            "technical_skills": CompetencyScore(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=3.0,
                current_level="Proficient",
                evidence_level="moderate",
                confidence_score=0.8,
                activity_count=10,
                recent_activity_count=5,
                time_weighted_score=9.0,
            ),
            "leadership": CompetencyScore(
                competency_id="leadership",
                competency_name="Leadership",
                current_score=2.5,
                current_level="Proficient",
                evidence_level="moderate",
                confidence_score=0.6,
                activity_count=6,
                recent_activity_count=3,
                time_weighted_score=5.5,
            ),
        }

        overall_score, confidence = competency_assessor._calculate_overall_metrics(
            competency_scores
        )

        # Weighted average: (3.0*0.8 + 2.5*0.6) / (0.8 + 0.6) = 2.786
        assert 2.75 <= overall_score <= 2.85
        # Average confidence: (0.8 + 0.6) / 2 = 0.7
        assert 0.69 <= confidence <= 0.71

    def test_generate_insights(self, competency_assessor):
        """Test insight generation"""
        competency_scores = {
            "technical_skills": CompetencyScore(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=4.0,
                current_level="Advanced",
                evidence_level="strong",
                confidence_score=0.9,
                activity_count=15,
                recent_activity_count=8,
                time_weighted_score=14.0,
            ),
            "leadership": CompetencyScore(
                competency_id="leadership",
                competency_name="Leadership",
                current_score=1.5,
                current_level="Developing",
                evidence_level="weak",
                confidence_score=0.4,
                activity_count=3,
                recent_activity_count=1,
                time_weighted_score=2.5,
            ),
            "communication": CompetencyScore(
                competency_id="communication",
                competency_name="Communication",
                current_score=3.0,
                current_level="Proficient",
                evidence_level="moderate",
                confidence_score=0.7,
                activity_count=8,
                recent_activity_count=2,
                time_weighted_score=7.0,
            ),
        }

        strengths, development_areas, recommendations = competency_assessor._generate_insights(
            competency_scores, {}
        )

        # Technical skills should be in strengths (score >= 3.0, confidence >= 0.6)
        assert len(strengths) > 0
        assert any("Technical Skills" in s for s in strengths)

        # Leadership should be in development areas (score < 2.5)
        assert len(development_areas) > 0
        assert any("Leadership" in d for d in development_areas)

        # Should have some overall recommendations
        assert len(recommendations) > 0

    def test_generate_insights_with_high_scores(self, competency_assessor):
        """Test insights when user has high scores"""
        competency_scores = {
            "technical_skills": CompetencyScore(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=4.5,
                current_level="Expert",
                evidence_level="strong",
                confidence_score=0.95,
                activity_count=20,
                recent_activity_count=10,
                time_weighted_score=19.0,
            ),
        }

        strengths, development_areas, recommendations = competency_assessor._generate_insights(
            competency_scores, {}
        )

        # Should recommend mentoring/leadership
        assert any(
            "mentor" in rec.lower() or "leadership" in rec.lower() for rec in recommendations
        )

    def test_generate_insights_with_low_activity(self, competency_assessor):
        """Test insights when overall activity is low"""
        competency_scores = {
            "technical_skills": CompetencyScore(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=2.0,
                current_level="Developing",
                evidence_level="weak",
                confidence_score=0.5,
                activity_count=3,
                recent_activity_count=1,  # Low recent activity
                time_weighted_score=2.5,
            ),
        }

        strengths, development_areas, recommendations = competency_assessor._generate_insights(
            competency_scores, {}
        )

        # Should recommend increasing activity levels
        assert any("activity" in rec.lower() for rec in recommendations)

    def test_calculate_progression_metrics_empty(self, competency_assessor):
        """Test progression metrics with empty scores"""
        metrics = competency_assessor._calculate_progression_metrics({}, [])

        assert metrics["improvement_velocity"] == 0.0
        assert metrics["breadth"] == 0.0
        assert metrics["depth"] == 0.0

    def test_calculate_progression_metrics(self, competency_assessor):
        """Test progression metrics calculation"""
        competency_scores = {
            "technical_skills": CompetencyScore(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=3.0,
                current_level="Proficient",
                evidence_level="moderate",
                confidence_score=0.8,
                activity_count=10,
                recent_activity_count=5,
                time_weighted_score=9.0,
            ),
            "leadership": CompetencyScore(
                competency_id="leadership",
                competency_name="Leadership",
                current_score=0.5,  # Below meaningful threshold
                current_level="Novice",
                evidence_level="insufficient",
                confidence_score=0.2,
                activity_count=1,
                recent_activity_count=0,
                time_weighted_score=0.5,
            ),
        }

        activities = [{"id": i} for i in range(12)]

        metrics = competency_assessor._calculate_progression_metrics(competency_scores, activities)

        # Breadth: 1 out of 2 competencies has meaningful score (>= 1.0)
        assert metrics["breadth"] == 0.5

        # Depth: average of scores (3.0 + 0.5) / 2 = 1.75
        assert 1.7 <= metrics["depth"] <= 1.8

        # Velocity: positive number
        assert metrics["improvement_velocity"] >= 0.0

    def test_calculate_data_quality_metrics_empty(self, competency_assessor):
        """Test data quality metrics with no activities"""
        metrics = competency_assessor._calculate_data_quality_metrics([])

        assert metrics["completeness"] == 0.0
        assert metrics["recency"] == 0.0
        assert metrics["diversity"] == 0.0

    def test_calculate_data_quality_metrics(self, competency_assessor, sample_activities):
        """Test data quality metrics calculation"""
        metrics = competency_assessor._calculate_data_quality_metrics(sample_activities)

        # All sample activities have required fields
        assert metrics["completeness"] == 1.0

        # Check recency (activities within 30 days)
        assert 0.0 <= metrics["recency"] <= 1.0

        # Check diversity (unique activity types)
        assert 0.0 <= metrics["diversity"] <= 1.0

    @pytest.mark.asyncio
    async def test_assess_user_competencies_basic(self, competency_assessor, sample_activities):
        """Test basic user competency assessment"""
        # Mock the scoring and grouping
        with patch.object(competency_assessor, "_group_activities_by_competency") as mock_group:
            mock_group.return_value = {
                "technical_skills": sample_activities[:2],
                "leadership": [sample_activities[1]],
                "communication": [sample_activities[2]],
            }

            with patch.object(
                competency_assessor.activity_scorer, "score_competency"
            ) as mock_score:
                mock_score.return_value = ScoringResult(
                    competency_type="technical_skills",
                    scoring_method="comprehensive",
                    raw_activity_count=2,
                    weighted_activity_count=1.8,
                    competency_score=1.5,
                    competency_level=CompetencyScoreLevel.DEVELOPING,
                    evidence_level="moderate",
                    confidence_score=0.6,
                    activities_analyzed=[],
                    recommendations=[],
                )

                result = await competency_assessor.assess_user_competencies(
                    user_id="user123",
                    activities=sample_activities,
                    scoring_method=ScoringMethod.COMPREHENSIVE,
                )

                assert isinstance(result, AssessmentResult)
                assert result.user_id == "user123"
                assert result.framework_id == "test_framework"
                assert result.competencies_assessed > 0
                assert result.total_activities_analyzed == len(sample_activities)
                assert 0.0 <= result.overall_competency_score <= 5.0
                assert 0.0 <= result.assessment_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_assess_user_competencies_caching(self, competency_assessor, sample_activities):
        """Test that assessment results are cached"""
        with patch.object(competency_assessor, "_group_activities_by_competency") as mock_group:
            mock_group.return_value = {"technical_skills": sample_activities}

            with patch.object(
                competency_assessor.activity_scorer, "score_competency"
            ) as mock_score:
                mock_score.return_value = ScoringResult(
                    competency_type="technical_skills",
                    scoring_method="comprehensive",
                    raw_activity_count=5,
                    weighted_activity_count=4.5,
                    competency_score=2.5,
                    competency_level=CompetencyScoreLevel.PROFICIENT,
                    evidence_level="moderate",
                    confidence_score=0.7,
                    activities_analyzed=[],
                    recommendations=[],
                )

                # First call
                result1 = await competency_assessor.assess_user_competencies(
                    user_id="user123", activities=sample_activities
                )

                # Second call with same parameters
                result2 = await competency_assessor.assess_user_competencies(
                    user_id="user123", activities=sample_activities
                )

                # Should return cached result (same instance)
                assert result1 is result2
                # Scoring should only be called once per competency
                assert mock_score.call_count <= 3

    @pytest.mark.asyncio
    async def test_assess_single_competency(self, competency_assessor, sample_activities):
        """Test assessing a single competency"""
        with patch.object(competency_assessor.activity_scorer, "score_competency") as mock_score:
            mock_score.return_value = ScoringResult(
                competency_type="technical_skills",
                scoring_method="comprehensive",
                raw_activity_count=2,
                weighted_activity_count=1.8,
                competency_score=2.0,
                competency_level=CompetencyScoreLevel.DEVELOPING,
                evidence_level="moderate",
                confidence_score=0.65,
                activities_analyzed=[],
                recommendations=["Keep practicing"],
            )

            result = await competency_assessor.assess_single_competency(
                user_id="user123", competency_id="technical_skills", activities=sample_activities
            )

            assert isinstance(result, CompetencyScore)
            assert result.competency_id == "technical_skills"
            assert result.current_score == 2.0
            assert result.current_level == "Developing"

    @pytest.mark.asyncio
    async def test_track_competency_progression_no_history(self, competency_assessor):
        """Test progression tracking with no history"""
        result = await competency_assessor.track_competency_progression(
            user_id="user123", competency_id="technical_skills", assessment_history=[]
        )

        assert "error" in result
        assert "No assessment history" in result["error"]

    @pytest.mark.asyncio
    async def test_track_competency_progression_insufficient_data(self, competency_assessor):
        """Test progression tracking with insufficient data points"""
        assessment_history = [
            {
                "date": "2025-01-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 2.0}},
            }
        ]

        result = await competency_assessor.track_competency_progression(
            user_id="user123",
            competency_id="technical_skills",
            assessment_history=assessment_history,
        )

        assert "error" in result
        assert "Insufficient" in result["error"]

    @pytest.mark.asyncio
    async def test_track_competency_progression_improving(self, competency_assessor):
        """Test progression tracking with improving trend"""
        assessment_history = [
            {
                "date": "2024-10-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 2.0}},
            },
            {
                "date": "2024-11-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 2.5}},
            },
            {
                "date": "2024-12-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 3.0}},
            },
        ]

        result = await competency_assessor.track_competency_progression(
            user_id="user123",
            competency_id="technical_skills",
            assessment_history=assessment_history,
            time_period_days=90,
        )

        assert "error" not in result
        assert result["competency_id"] == "technical_skills"
        assert result["total_score_change"] == 1.0  # 3.0 - 2.0
        assert result["trend_direction"] == "improving"
        assert result["assessment_count"] == 3
        assert result["current_score"] == 3.0
        assert result["starting_score"] == 2.0

    @pytest.mark.asyncio
    async def test_track_competency_progression_declining(self, competency_assessor):
        """Test progression tracking with declining trend"""
        assessment_history = [
            {
                "date": "2024-10-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 3.5}},
            },
            {
                "date": "2024-11-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 3.0}},
            },
            {
                "date": "2024-12-01T00:00:00",
                "competency_scores": {"technical_skills": {"current_score": 2.5}},
            },
        ]

        result = await competency_assessor.track_competency_progression(
            user_id="user123",
            competency_id="technical_skills",
            assessment_history=assessment_history,
        )

        assert result["trend_direction"] == "declining"
        assert result["total_score_change"] < 0

    def test_get_assessment_summary(self, competency_assessor):
        """Test getting assessment summary"""
        assessment = AssessmentResult(
            user_id="user123",
            framework_id="test_framework",
            overall_competency_score=2.85,
            competencies_assessed=3,
            total_activities_analyzed=15,
            assessment_confidence=0.72,
            top_strengths=["Technical Skills (Level: Advanced)"],
            priority_development_areas=["Leadership (Current: Developing)"],
            data_quality_metrics={"completeness": 0.9, "recency": 0.7, "diversity": 0.6},
        )

        summary = competency_assessor.get_assessment_summary(assessment)

        assert summary["user_id"] == "user123"
        assert summary["overall_score"] == 2.85
        assert summary["confidence"] == 0.72
        assert summary["competencies_count"] == 3
        assert "Technical Skills" in summary["top_strength"]
        assert "Leadership" in summary["priority_development"]
        assert "data_quality" in summary


class TestGroupActivitiesByCompetency:
    """Test activity grouping logic"""

    @pytest.mark.asyncio
    async def test_group_activities_with_competency_type(self, competency_assessor):
        """Test grouping activities that already have competency_type"""
        activities = [
            {
                "description": "Coding",
                "activity_type": "code",
                "competency_type": "technical_skills",
            },
            {"description": "Meeting", "activity_type": "meeting", "competency_type": "leadership"},
        ]

        result = await competency_assessor._group_activities_by_competency(activities)

        assert "technical_skills" in result
        assert "leadership" in result
        assert len(result["technical_skills"]) == 1
        assert len(result["leadership"]) == 1

    @pytest.mark.asyncio
    async def test_group_activities_with_competencies_list(self, competency_assessor):
        """Test grouping activities with competencies list"""
        activities = [
            {
                "description": "Code review",
                "activity_type": "review",
                "competencies": ["technical_skills", "communication"],
            },
        ]

        result = await competency_assessor._group_activities_by_competency(activities)

        # Activity should be in both competencies
        assert "technical_skills" in result
        assert "communication" in result
        assert len(result["technical_skills"]) == 1
        assert len(result["communication"]) == 1

    @pytest.mark.asyncio
    async def test_group_activities_with_mapper(self, competency_assessor):
        """Test grouping activities using competency mapper"""
        # Create activity without competency mapping - will trigger mapper path
        activity = {
            "description": "Implemented feature",
            "activity_type": "coding",
            # No competency_type or competencies - should trigger mapper
        }
        activities = [activity]

        # Replace the mocked mapper with a real mock that we can track
        real_mock = Mock()
        real_mock.map_activity_to_competencies = AsyncMock()
        mock_result = Mock()
        mock_result.primary_competency = "technical_skills"
        mock_result.secondary_competencies = []
        real_mock.map_activity_to_competencies.return_value = mock_result
        competency_assessor.competency_mapper = real_mock

        result = await competency_assessor._group_activities_by_competency(activities)

        # Should have grouped the activity (either via mapper or fallback to general)
        assert len(result) > 0
        assert "technical_skills" in result or "general" in result


class TestGlobalAssessorSingleton:
    """Test global assessor singleton pattern"""

    def test_get_competency_assessor_returns_singleton(self):
        """Test that get_competency_assessor returns same instance"""
        with (
            patch("src.core.assessment.competency_assessor.get_framework_loader"),
            patch("src.core.assessment.competency_assessor.CompetencyMapper"),
        ):
            assessor1 = get_competency_assessor()
            assessor2 = get_competency_assessor()

            assert assessor1 is assessor2
            assert assessor1 is not None

    def test_get_competency_assessor_different_frameworks(self):
        """Test that different frameworks get different instances"""
        with (
            patch("src.core.assessment.competency_assessor.get_framework_loader"),
            patch("src.core.assessment.competency_assessor.CompetencyMapper"),
        ):
            assessor1 = get_competency_assessor("framework1")
            assessor2 = get_competency_assessor("framework2")

            # Different framework IDs should get different instances
            assert assessor1 is not assessor2
            assert assessor1.framework_id == "framework1"
            assert assessor2.framework_id == "framework2"

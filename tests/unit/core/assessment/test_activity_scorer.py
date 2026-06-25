"""
Unit tests for ActivityScorer

Tests comprehensive scoring algorithms including:
- Simple count scoring
- Time-weighted scoring
- Quality-weighted scoring
- Comprehensive scoring with all factors
- Score to level conversion
- Recommendation generation
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.core.assessment.scoring.activity_scorer import (
    ActivityScorer,
    CompetencyScoreLevel,
    ScoringMethod,
    ScoringResult,
    get_activity_scorer,
)


@pytest.fixture
def activity_scorer():
    """Create ActivityScorer instance for testing"""
    return ActivityScorer()


@pytest.fixture
def sample_activities():
    """Create sample activities for testing"""
    base_date = datetime.now(UTC)

    return [
        {
            "date": base_date - timedelta(days=5),
            "description": "Implemented new feature",
            "activity_type": "coding",
            "competency_type": "technical_skills",
        },
        {
            "date": base_date - timedelta(days=15),
            "description": "Code review",
            "activity_type": "review",
            "competency_type": "technical_skills",
        },
        {
            "date": base_date - timedelta(days=25),
            "description": "Led team meeting",
            "activity_type": "meeting",
            "competency_type": "leadership",
        },
        {
            "date": base_date - timedelta(days=60),
            "description": "Wrote documentation",
            "activity_type": "documentation",
            "competency_type": "communication",
        },
    ]


@pytest.fixture
def mock_time_decay():
    """Mock time decay calculator"""
    with patch("src.core.assessment.scoring.activity_scorer.get_time_decay_calculator") as mock:
        mock_calculator = Mock()
        mock_calculator.get_time_window_activities.return_value = []
        mock_calculator.calculate_bulk_weighted_values.return_value = []
        mock.return_value = mock_calculator
        yield mock_calculator


@pytest.fixture
def mock_evidence_threshold():
    """Mock evidence threshold calculator"""
    with patch("src.core.assessment.scoring.activity_scorer.get_evidence_threshold") as mock:
        mock_threshold = Mock()
        mock_assessment = Mock()
        mock_assessment.weighted_count = 5.0
        mock_assessment.time_weighted_count = 4.5
        mock_assessment.threshold_level.value = "moderate"
        mock_assessment.confidence_score = 0.7
        mock_assessment.recommendations = ["Keep up good work"]
        mock_threshold.assess_evidence.return_value = mock_assessment
        mock.return_value = mock_threshold
        yield mock_threshold


class TestActivityScorer:
    """Test suite for ActivityScorer"""

    def test_initialization(self, activity_scorer):
        """Test ActivityScorer initializes correctly"""
        assert activity_scorer is not None
        assert activity_scorer.time_decay is not None
        assert activity_scorer.evidence_threshold is not None
        assert "technical_skills" in activity_scorer.scoring_parameters
        assert "leadership" in activity_scorer.scoring_parameters
        assert "general" in activity_scorer.scoring_parameters

    def test_scoring_parameters_structure(self, activity_scorer):
        """Test scoring parameters have required fields"""
        params = activity_scorer.scoring_parameters["technical_skills"]

        assert "max_score" in params
        assert params["max_score"] == 5.0
        assert "count_to_score_ratio" in params
        assert "quality_boost" in params
        assert "recency_bonus" in params
        assert "minimum_activities_for_level" in params

    def test_score_to_level_conversion(self, activity_scorer):
        """Test score to level conversion"""
        assert activity_scorer._score_to_level(0.5) == CompetencyScoreLevel.NOVICE
        assert activity_scorer._score_to_level(1.5) == CompetencyScoreLevel.DEVELOPING
        assert activity_scorer._score_to_level(2.5) == CompetencyScoreLevel.PROFICIENT
        assert activity_scorer._score_to_level(3.5) == CompetencyScoreLevel.ADVANCED
        assert activity_scorer._score_to_level(4.5) == CompetencyScoreLevel.EXPERT

    def test_simple_count_scoring_empty_activities(self, activity_scorer):
        """Test simple count scoring with no activities"""
        result = activity_scorer._simple_count_scoring(
            [],
            "technical_skills",
            {
                "max_score": 5.0,
                "count_to_score_ratio": 0.3,
                "minimum_activities_for_level": {1: 1, 2: 3, 3: 6, 4: 10, 5: 15},
            },
        )

        assert result.raw_activity_count == 0
        assert result.weighted_activity_count == 0.0
        assert result.competency_score == 0.0
        assert result.competency_level == CompetencyScoreLevel.NOVICE
        assert result.confidence_score == 0.0

    def test_simple_count_scoring_with_activities(self, activity_scorer, sample_activities):
        """Test simple count scoring with activities"""
        params = activity_scorer.scoring_parameters["technical_skills"]

        result = activity_scorer._simple_count_scoring(
            sample_activities[:2],  # 2 technical activities
            "technical_skills",
            params,
        )

        assert result.raw_activity_count == 2
        assert result.weighted_activity_count == 2.0
        assert result.competency_score == 2 * params["count_to_score_ratio"]
        assert result.competency_level == CompetencyScoreLevel.NOVICE
        assert result.confidence_score == 0.6
        assert result.scoring_method == ScoringMethod.SIMPLE_COUNT.value

    def test_calculate_recency_factor(self, activity_scorer, sample_activities):
        """Test recency factor calculation"""
        reference_date = datetime.now(UTC)

        recency = activity_scorer._calculate_recency_factor(sample_activities, reference_date)

        # Should have 3 recent activities (within 30 days: 5, 15, 25 days) out of 4 total
        assert 0.0 <= recency <= 1.0
        assert recency == 0.75  # 3/4 activities are recent

    def test_calculate_recency_factor_empty(self, activity_scorer):
        """Test recency factor with no activities"""
        reference_date = datetime.now(UTC)

        recency = activity_scorer._calculate_recency_factor([], reference_date)

        assert recency == 0.0

    def test_create_empty_result(self, activity_scorer):
        """Test creating empty result for competency"""
        result = activity_scorer._create_empty_result("technical_skills")

        assert result.competency_type == "technical_skills"
        assert result.raw_activity_count == 0
        assert result.weighted_activity_count == 0.0
        assert result.competency_score == 0.0
        assert result.competency_level == CompetencyScoreLevel.NOVICE
        assert result.evidence_level == "insufficient"
        assert result.confidence_score == 0.0
        assert len(result.recommendations) > 0

    def test_generate_basic_recommendations(self, activity_scorer):
        """Test basic recommendation generation"""
        # Novice level
        recommendations = activity_scorer._generate_basic_recommendations(
            0.5, CompetencyScoreLevel.NOVICE
        )
        assert "Begin building experience" in recommendations[0]

        # Proficient level
        recommendations = activity_scorer._generate_basic_recommendations(
            2.5, CompetencyScoreLevel.PROFICIENT
        )
        assert "Continue practicing" in recommendations[0]

        # Expert level
        recommendations = activity_scorer._generate_basic_recommendations(
            4.5, CompetencyScoreLevel.EXPERT
        )
        assert "Maintain current" in recommendations[0]

    def test_score_competency_simple_method(self, activity_scorer, sample_activities):
        """Test scoring with SIMPLE_COUNT method"""
        with patch.object(activity_scorer.time_decay, "get_time_window_activities") as mock_filter:
            mock_filter.return_value = sample_activities[:2]

            result = activity_scorer.score_competency(
                sample_activities[:2], "technical_skills", ScoringMethod.SIMPLE_COUNT
            )

            assert result.scoring_method == ScoringMethod.SIMPLE_COUNT.value
            assert result.raw_activity_count == 2
            assert result.competency_score > 0

    def test_score_multiple_competencies(self, activity_scorer, sample_activities):
        """Test scoring multiple competencies at once"""
        competency_activities = {
            "technical_skills": sample_activities[:2],
            "leadership": [sample_activities[2]],
            "communication": [sample_activities[3]],
        }

        with patch.object(activity_scorer.time_decay, "get_time_window_activities") as mock_filter:
            mock_filter.side_effect = lambda acts, *args, **kwargs: acts

            results = activity_scorer.score_multiple_competencies(
                competency_activities, ScoringMethod.SIMPLE_COUNT
            )

            assert len(results) == 3
            assert "technical_skills" in results
            assert "leadership" in results
            assert "communication" in results
            assert all(isinstance(r, ScoringResult) for r in results.values())

    def test_score_multiple_competencies_with_error(self, activity_scorer):
        """Test scoring handles errors gracefully"""
        competency_activities = {
            "invalid_competency": [],  # Empty activity list
        }

        # Empty activities should return zero score
        results = activity_scorer.score_multiple_competencies(
            competency_activities, ScoringMethod.SIMPLE_COUNT
        )

        assert "invalid_competency" in results
        result = results["invalid_competency"]
        assert result.raw_activity_count == 0
        assert result.competency_score == 0.0
        # Should have recommendations for building experience
        assert len(result.recommendations) > 0

    def test_apply_final_adjustments_minimum_activities(self, activity_scorer):
        """Test final adjustments enforce minimum activity requirements"""
        params = activity_scorer.scoring_parameters["technical_skills"]

        # Create result that claims expert level but only has 2 activities
        result = ScoringResult(
            competency_type="technical_skills",
            scoring_method="test",
            raw_activity_count=2,  # Not enough for expert
            weighted_activity_count=2.0,
            competency_score=5.0,  # Expert score
            competency_level=CompetencyScoreLevel.EXPERT,
            evidence_level="strong",
            confidence_score=0.9,
        )

        adjusted = activity_scorer._apply_final_adjustments(result, params, None)

        # Score should be capped due to insufficient activities
        assert adjusted.competency_score < 5.0
        assert adjusted.competency_level.value < CompetencyScoreLevel.EXPERT.value

    def test_apply_final_adjustments_experience_boost(self, activity_scorer):
        """Test experience boost in final adjustments"""
        params = activity_scorer.scoring_parameters["technical_skills"]

        result = ScoringResult(
            competency_type="technical_skills",
            scoring_method="test",
            raw_activity_count=10,
            weighted_activity_count=10.0,
            competency_score=3.0,
            competency_level=CompetencyScoreLevel.PROFICIENT,
            evidence_level="strong",
            confidence_score=0.8,
        )

        user_context = {"experience_years": 5}

        adjusted = activity_scorer._apply_final_adjustments(result, params, user_context)

        # Score should be slightly boosted for experience
        assert adjusted.competency_score > 3.0
        assert "Experience boost" in str(adjusted.scoring_factors.get("final_adjustments", []))

    def test_apply_final_adjustments_role_level(self, activity_scorer):
        """Test role level adjustment (senior roles need more evidence)"""
        params = activity_scorer.scoring_parameters["technical_skills"]

        result = ScoringResult(
            competency_type="technical_skills",
            scoring_method="test",
            raw_activity_count=10,
            weighted_activity_count=10.0,
            competency_score=3.0,
            competency_level=CompetencyScoreLevel.PROFICIENT,
            evidence_level="strong",
            confidence_score=0.8,
        )

        user_context = {"role_level": "senior"}

        adjusted = activity_scorer._apply_final_adjustments(result, params, user_context)

        # Score should be adjusted down for senior role expectations
        assert adjusted.competency_score <= 3.0
        assert "Role level adjustment" in str(adjusted.scoring_factors.get("final_adjustments", []))

    def test_comprehensive_scoring_with_mocks(
        self, activity_scorer, sample_activities, mock_time_decay, mock_evidence_threshold
    ):
        """Test comprehensive scoring with mocked dependencies"""
        # Setup mocks
        mock_time_decay.get_time_window_activities.return_value = sample_activities
        mock_decay_results = [
            Mock(decay_weight=1.0, weighted_value=1.0),
            Mock(decay_weight=0.9, weighted_value=0.9),
            Mock(decay_weight=0.8, weighted_value=0.8),
            Mock(decay_weight=0.7, weighted_value=0.7),
        ]
        mock_time_decay.calculate_bulk_weighted_values.return_value = mock_decay_results

        params = activity_scorer.scoring_parameters["technical_skills"]
        reference_date = datetime.now(UTC)

        result = activity_scorer._comprehensive_scoring(
            sample_activities, "technical_skills", params, reference_date, {}
        )

        assert result.competency_type == "technical_skills"
        assert result.scoring_method == ScoringMethod.COMPREHENSIVE.value
        assert result.raw_activity_count == 4
        assert result.weighted_activity_count > 0
        assert result.time_decay_impact > 0
        assert result.quality_impact > 0
        assert len(result.recommendations) > 0


class TestActivityScorerIntegration:
    """Integration tests for ActivityScorer with real dependencies"""

    def test_score_competency_full_workflow(self, sample_activities):
        """Test complete scoring workflow with real dependencies"""
        scorer = ActivityScorer()

        result = scorer.score_competency(
            sample_activities,
            "technical_skills",
            ScoringMethod.COMPREHENSIVE,
            reference_date=datetime.now(UTC),
        )

        assert result is not None
        assert result.competency_type == "technical_skills"
        assert result.raw_activity_count >= 0
        assert 0.0 <= result.competency_score <= 5.0
        assert result.competency_level in CompetencyScoreLevel
        assert 0.0 <= result.confidence_score <= 1.0

    def test_different_competency_types_have_different_parameters(self):
        """Test that different competency types use appropriate parameters"""
        scorer = ActivityScorer()

        tech_params = scorer.scoring_parameters["technical_skills"]
        leadership_params = scorer.scoring_parameters["leadership"]
        comm_params = scorer.scoring_parameters["communication"]

        # Leadership should need fewer but higher quality activities
        assert leadership_params["count_to_score_ratio"] > tech_params["count_to_score_ratio"]
        assert leadership_params["quality_boost"] > tech_params["quality_boost"]

        # Communication should need more frequent activities
        assert comm_params["count_to_score_ratio"] < tech_params["count_to_score_ratio"]
        assert comm_params["recency_bonus"] > tech_params["recency_bonus"]


class TestGlobalScorerSingleton:
    """Test global scorer singleton pattern"""

    def test_get_activity_scorer_returns_singleton(self):
        """Test that get_activity_scorer returns same instance"""
        scorer1 = get_activity_scorer()
        scorer2 = get_activity_scorer()

        assert scorer1 is scorer2
        assert scorer1 is not None

    def test_get_activity_scorer_initialization(self):
        """Test that global scorer is properly initialized"""
        scorer = get_activity_scorer()

        assert scorer.time_decay is not None
        assert scorer.evidence_threshold is not None
        assert len(scorer.scoring_parameters) > 0

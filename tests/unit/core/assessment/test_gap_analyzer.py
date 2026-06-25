"""
Unit tests for GapAnalyzer

Tests competency gap analysis including:
- Individual gap analysis and severity classification
- Development priority determination
- Skill transferability analysis
- Development roadmap generation
- Role readiness assessment
- Career path recommendations
- Timeline and milestone planning
"""

import pytest

from src.core.assessment.gap_analyzer import (
    DevelopmentPriority,
    DevelopmentRoadmap,
    GapAnalysisResult,
    GapAnalyzer,
    GapSeverity,
    SkillGap,
    SkillTransferability,
    get_gap_analyzer,
)


@pytest.fixture
def gap_analyzer():
    """Create GapAnalyzer instance for testing"""
    return GapAnalyzer()


@pytest.fixture
def sample_current_scores():
    """Sample current competency scores"""
    return {
        "technical_skills": 2.5,
        "leadership": 1.8,
        "communication": 3.0,
        "project_management": 2.0,
    }


@pytest.fixture
def sample_target_requirements():
    """Sample target requirements for senior role"""
    return {
        "technical_skills": 4.0,
        "leadership": 3.5,
        "communication": 3.5,
        "project_management": 3.0,
    }


@pytest.fixture
def sample_user_context():
    """Sample user context"""
    return {
        "user_id": "user123",
        "role": "engineer",
        "experience_years": 3,
        "team_size": 5,
    }


class TestGapSeverityEnum:
    """Test GapSeverity enum"""

    def test_gap_severity_values(self):
        """Test gap severity enum values"""
        assert GapSeverity.CRITICAL.value == "critical"
        assert GapSeverity.MAJOR.value == "major"
        assert GapSeverity.MODERATE.value == "moderate"
        assert GapSeverity.MINOR.value == "minor"
        assert GapSeverity.NONE.value == "none"


class TestDevelopmentPriorityEnum:
    """Test DevelopmentPriority enum"""

    def test_development_priority_values(self):
        """Test development priority enum values"""
        assert DevelopmentPriority.HIGH.value == "high"
        assert DevelopmentPriority.MEDIUM.value == "medium"
        assert DevelopmentPriority.LOW.value == "low"
        assert DevelopmentPriority.OPTIONAL.value == "optional"


class TestSkillGapModel:
    """Test SkillGap model"""

    def test_skill_gap_creation(self):
        """Test creating a skill gap instance"""
        gap = SkillGap(
            competency_id="technical_skills",
            competency_name="Technical Skills",
            current_score=2.0,
            target_score=4.0,
            gap_size=2.0,
            gap_severity=GapSeverity.CRITICAL,
            development_priority=DevelopmentPriority.HIGH,
            estimated_development_time="6-12 months",
            development_difficulty="moderate",
        )

        assert gap.competency_id == "technical_skills"
        assert gap.gap_size == 2.0
        assert gap.gap_severity == GapSeverity.CRITICAL
        assert gap.is_blocking is False  # Default
        assert len(gap.recommended_activities) == 0  # Default empty list


class TestGapAnalyzer:
    """Test suite for GapAnalyzer"""

    def test_initialization(self, gap_analyzer):
        """Test GapAnalyzer initializes correctly"""
        assert gap_analyzer is not None
        assert gap_analyzer.level_calculator is not None
        assert len(gap_analyzer.skill_transfer_matrix) > 0
        assert len(gap_analyzer.development_activities) > 0

    def test_skill_transfer_matrix_structure(self, gap_analyzer):
        """Test skill transfer matrix has correct structure"""
        matrix = gap_analyzer.skill_transfer_matrix

        assert "technical_skills" in matrix
        assert "leadership" in matrix
        assert "communication" in matrix

        # Check transfer scores are valid (0.0-1.0)
        for _source, transfers in matrix.items():
            for _target, score in transfers.items():
                assert 0.0 <= score <= 1.0

    def test_analyze_competency_gaps_basic(
        self, gap_analyzer, sample_current_scores, sample_target_requirements
    ):
        """Test basic competency gap analysis"""
        result = gap_analyzer.analyze_competency_gaps(
            user_id="user123",
            current_scores=sample_current_scores,
            target_requirements=sample_target_requirements,
        )

        assert isinstance(result, GapAnalysisResult)
        assert result.user_id == "user123"
        assert result.roadmap.total_gaps > 0
        assert len(result.roadmap.skill_gaps) > 0
        assert 0.0 <= result.analysis_confidence <= 1.0

    def test_analyze_competency_gaps_identifies_critical_gaps(
        self, gap_analyzer, sample_current_scores, sample_target_requirements
    ):
        """Test that critical gaps are identified correctly"""
        result = gap_analyzer.analyze_competency_gaps(
            user_id="user123",
            current_scores=sample_current_scores,
            target_requirements=sample_target_requirements,
        )

        # Leadership gap is 1.7 (3.5 - 1.8) which should be MAJOR
        # Technical skills gap is 1.5 (4.0 - 2.5) which should be MAJOR
        assert result.roadmap.total_gaps == 4

        # Should have priority gaps (high priority items)
        assert len(result.roadmap.priority_gaps) > 0

    def test_analyze_competency_gaps_with_no_gaps(self, gap_analyzer):
        """Test gap analysis when already meeting all requirements"""
        current_scores = {"technical_skills": 4.5, "leadership": 4.0}
        target_requirements = {"technical_skills": 4.0, "leadership": 3.5}

        result = gap_analyzer.analyze_competency_gaps(
            user_id="user123",
            current_scores=current_scores,
            target_requirements=target_requirements,
        )

        # All gaps should have NONE severity
        for gap in result.roadmap.skill_gaps:
            assert gap.gap_severity == GapSeverity.NONE

    def test_analyze_competency_gaps_with_context(
        self, gap_analyzer, sample_current_scores, sample_target_requirements, sample_user_context
    ):
        """Test gap analysis with user context"""
        result = gap_analyzer.analyze_competency_gaps(
            user_id="user123",
            current_scores=sample_current_scores,
            target_requirements=sample_target_requirements,
            user_context=sample_user_context,
            target_role="senior_engineer",
        )

        assert result.roadmap.target_role == "senior_engineer"
        assert len(result.roadmap.immediate_actions) > 0
        assert len(result.roadmap.short_term_goals) > 0

    def test_analyze_single_gap_critical(self, gap_analyzer):
        """Test analyzing a single critical gap"""
        gap = gap_analyzer._analyze_single_gap(
            competency_id="technical_skills",
            current_score=1.0,
            target_score=4.0,
            user_context={},
            target_role=None,
        )

        assert gap.gap_size == 3.0
        assert gap.gap_severity == GapSeverity.CRITICAL  # >2.0 gap
        assert gap.development_priority == DevelopmentPriority.HIGH
        assert len(gap.recommended_activities) > 0

    def test_analyze_single_gap_major(self, gap_analyzer):
        """Test analyzing a major gap"""
        gap = gap_analyzer._analyze_single_gap(
            competency_id="leadership",
            current_score=2.0,
            target_score=3.5,
            user_context={},
            target_role=None,
        )

        assert gap.gap_size == 1.5
        assert gap.gap_severity == GapSeverity.MAJOR  # 1.0-2.0 gap
        assert len(gap.recommended_activities) > 0

    def test_analyze_single_gap_moderate(self, gap_analyzer):
        """Test analyzing a moderate gap"""
        gap = gap_analyzer._analyze_single_gap(
            competency_id="communication",
            current_score=2.5,
            target_score=3.2,
            user_context={},
            target_role=None,
        )

        assert gap.gap_size == pytest.approx(0.7, rel=1e-9)
        assert gap.gap_severity == GapSeverity.MODERATE  # 0.5-1.0 gap

    def test_analyze_single_gap_minor(self, gap_analyzer):
        """Test analyzing a minor gap"""
        gap = gap_analyzer._analyze_single_gap(
            competency_id="project_management",
            current_score=2.7,
            target_score=3.0,
            user_context={},
            target_role=None,
        )

        assert gap.gap_size == pytest.approx(0.3, rel=1e-9)
        assert gap.gap_severity == GapSeverity.MINOR  # <0.5 gap

    def test_analyze_single_gap_no_gap(self, gap_analyzer):
        """Test analyzing when no gap exists"""
        gap = gap_analyzer._analyze_single_gap(
            competency_id="technical_skills",
            current_score=4.5,
            target_score=4.0,
            user_context={},
            target_role=None,
        )

        assert gap.gap_size == -0.5  # Negative means exceeds requirement
        assert gap.gap_severity == GapSeverity.NONE

    def test_determine_development_priority_critical_foundational(self, gap_analyzer):
        """Test priority determination for critical foundational gap"""
        priority = gap_analyzer._determine_development_priority(
            gap_severity=GapSeverity.CRITICAL,
            competency_id="technical_skills",  # foundational competency
            target_role="senior_engineer",
        )

        assert priority == DevelopmentPriority.HIGH

    def test_determine_development_priority_major_blocking(self, gap_analyzer):
        """Test priority determination for major blocking gap"""
        priority = gap_analyzer._determine_development_priority(
            gap_severity=GapSeverity.MAJOR,
            competency_id="leadership",
            target_role="team_lead",
        )

        assert priority == DevelopmentPriority.HIGH

    def test_determine_development_priority_moderate(self, gap_analyzer):
        """Test priority determination for moderate gap"""
        priority = gap_analyzer._determine_development_priority(
            gap_severity=GapSeverity.MODERATE,
            competency_id="project_management",
            target_role=None,
        )

        assert priority == DevelopmentPriority.MEDIUM

    def test_determine_development_priority_minor(self, gap_analyzer):
        """Test priority determination for minor gap"""
        priority = gap_analyzer._determine_development_priority(
            gap_severity=GapSeverity.MINOR,
            competency_id="project_management",
            target_role=None,
        )

        assert priority == DevelopmentPriority.LOW

    def test_get_transferable_skills(self, gap_analyzer):
        """Test getting transferable skills"""
        transfers = gap_analyzer._get_transferable_skills("technical_skills")

        assert len(transfers) > 0
        assert all(isinstance(t, SkillTransferability) for t in transfers)
        assert all(0.0 <= t.transferability_score <= 1.0 for t in transfers)

    def test_estimate_development_time_critical(self, gap_analyzer):
        """Test development time estimation for critical gap"""
        time_estimate = gap_analyzer._estimate_development_time(
            gap_size=2.5, gap_severity=GapSeverity.CRITICAL, competency_id="technical_skills"
        )

        assert "month" in time_estimate.lower()

    def test_estimate_development_time_minor(self, gap_analyzer):
        """Test development time estimation for minor gap"""
        time_estimate = gap_analyzer._estimate_development_time(
            gap_size=0.3, gap_severity=GapSeverity.MINOR, competency_id="communication"
        )

        assert "week" in time_estimate.lower() or "month" in time_estimate.lower()

    def test_assess_development_difficulty(self, gap_analyzer):
        """Test development difficulty assessment"""
        # Small gap should be easier
        easy_difficulty = gap_analyzer._assess_development_difficulty(
            "technical_skills", gap_size=0.5
        )
        assert easy_difficulty in ["low", "medium"]

        # Large gap should be harder
        hard_difficulty = gap_analyzer._assess_development_difficulty("leadership", gap_size=2.5)
        assert hard_difficulty in ["medium", "high"]

    def test_generate_development_activities(self, gap_analyzer):
        """Test generating development activities"""
        activities = gap_analyzer._generate_development_activities(
            competency_id="technical_skills",
            gap_severity=GapSeverity.MAJOR,
        )

        assert len(activities) > 0
        assert all(isinstance(a, str) for a in activities)

    def test_suggest_learning_resources(self, gap_analyzer):
        """Test suggesting learning resources"""
        resources = gap_analyzer._suggest_learning_resources(
            competency_id="leadership", gap_severity=GapSeverity.MAJOR
        )

        assert len(resources) > 0
        assert all(isinstance(r, str) for r in resources)

    def test_create_milestone_targets(self, gap_analyzer):
        """Test creating milestone targets"""
        milestones = gap_analyzer._create_milestone_targets(
            current_score=2.0,
            target_score=4.0,
            timeline="6-12 months",
        )

        assert len(milestones) > 0
        assert all("target_score" in m for m in milestones)
        assert all("timeline" in m for m in milestones)

    def test_define_success_metrics(self, gap_analyzer):
        """Test defining success metrics"""
        metrics = gap_analyzer._define_success_metrics("technical_skills", target_score=4.0)

        assert len(metrics) > 0
        assert all(isinstance(m, str) for m in metrics)

    def test_parse_timeline_months(self, gap_analyzer):
        """Test parsing timeline strings to months"""
        assert gap_analyzer._parse_timeline_months("< 1 month") == 1
        assert gap_analyzer._parse_timeline_months("1-3 months") == 3
        assert gap_analyzer._parse_timeline_months("3-6 months") == 6
        assert gap_analyzer._parse_timeline_months("6-12 months") == 12
        assert gap_analyzer._parse_timeline_months("12+ months") == 18
        assert gap_analyzer._parse_timeline_months("unknown") == 6  # default

    def test_format_timeline_estimate(self, gap_analyzer):
        """Test formatting months to timeline estimate"""
        assert gap_analyzer._format_timeline_estimate(0) == "< 1 month"
        assert gap_analyzer._format_timeline_estimate(1) == "1-3 months"
        assert gap_analyzer._format_timeline_estimate(4) == "3-6 months"
        assert gap_analyzer._format_timeline_estimate(8) == "6-12 months"
        assert gap_analyzer._format_timeline_estimate(15) == "12+ months"

    def test_generate_immediate_actions(self, gap_analyzer):
        """Test generating immediate actions"""
        gaps = [
            SkillGap(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=2.0,
                target_score=4.0,
                gap_size=2.0,
                gap_severity=GapSeverity.CRITICAL,
                development_priority=DevelopmentPriority.HIGH,
                estimated_development_time="6-12 months",
                development_difficulty="moderate",
                recommended_activities=["Practice coding", "Take courses"],
            )
        ]

        actions = gap_analyzer._generate_immediate_actions(gaps)

        assert len(actions) > 0
        assert all(isinstance(a, str) for a in actions)

    def test_generate_short_term_goals(self, gap_analyzer):
        """Test generating short-term goals"""
        gaps = [
            SkillGap(
                competency_id="leadership",
                competency_name="Leadership",
                current_score=2.0,
                target_score=3.5,
                gap_size=1.5,
                gap_severity=GapSeverity.MAJOR,
                development_priority=DevelopmentPriority.HIGH,
                estimated_development_time="3-6 months",
                development_difficulty="moderate",
                milestone_targets=[
                    {"target_score": 2.5, "timeline": "First milestone", "description": "Reach 2.5"}
                ],
            )
        ]

        goals = gap_analyzer._generate_short_term_goals(gaps)

        assert len(goals) > 0
        assert all(isinstance(g, str) for g in goals)

    def test_calculate_role_readiness_score(self, gap_analyzer):
        """Test calculating role readiness score"""
        # No gaps - should be high readiness
        no_gaps = [
            SkillGap(
                competency_id="tech",
                competency_name="Tech",
                current_score=4.0,
                target_score=4.0,
                gap_size=0.0,
                gap_severity=GapSeverity.NONE,
                development_priority=DevelopmentPriority.OPTIONAL,
                estimated_development_time="0 months",
                development_difficulty="easy",
            )
        ]
        high_readiness = gap_analyzer._calculate_role_readiness_score(no_gaps)
        assert high_readiness >= 0.9

        # Critical gaps - should be low readiness
        critical_gaps = [
            SkillGap(
                competency_id="tech",
                competency_name="Tech",
                current_score=1.0,
                target_score=4.0,
                gap_size=3.0,
                gap_severity=GapSeverity.CRITICAL,
                development_priority=DevelopmentPriority.HIGH,
                estimated_development_time="12+ months",
                development_difficulty="challenging",
            )
        ]
        low_readiness = gap_analyzer._calculate_role_readiness_score(critical_gaps)
        # One CRITICAL gap = 0.4 penalty, so score = 1.0 - 0.4 = 0.6
        assert low_readiness == pytest.approx(0.6, rel=1e-9)
        assert low_readiness < 0.7  # Should be relatively low

    def test_calculate_analysis_confidence(self, gap_analyzer):
        """Test calculating analysis confidence"""
        user_context = {
            "experience_years": 3,
            "activity_count": 50,
            "assessment_count": 10,
        }

        skill_gaps = [
            SkillGap(
                competency_id="tech",
                competency_name="Tech",
                current_score=3.0,
                target_score=4.0,
                gap_size=1.0,
                gap_severity=GapSeverity.MAJOR,
                development_priority=DevelopmentPriority.HIGH,
                estimated_development_time="3-6 months",
                development_difficulty="medium",
            ),
            SkillGap(
                competency_id="leadership",
                competency_name="Leadership",
                current_score=2.5,
                target_score=3.5,
                gap_size=1.0,
                gap_severity=GapSeverity.MAJOR,
                development_priority=DevelopmentPriority.HIGH,
                estimated_development_time="3-6 months",
                development_difficulty="medium",
            ),
        ]

        confidence = gap_analyzer._calculate_analysis_confidence(
            skill_gaps=skill_gaps,
            user_context=user_context,
        )

        assert 0.0 <= confidence <= 1.0

    def test_calculate_data_quality_score(self, gap_analyzer):
        """Test calculating data quality score"""
        user_context = {
            "activity_count": 100,
            "recent_activity_count": 20,
            "assessment_count": 5,
        }

        quality = gap_analyzer._calculate_data_quality_score(
            current_scores={"tech": 3.0, "leadership": 2.5, "comm": 2.8},
            user_context=user_context,
        )

        assert 0.0 <= quality <= 1.0

    def test_analyze_role_readiness(
        self, gap_analyzer, sample_current_scores, sample_target_requirements
    ):
        """Test comprehensive role readiness analysis"""
        result = gap_analyzer.analyze_role_readiness(
            user_id="user123",
            current_scores=sample_current_scores,
            target_role="senior_engineer",
            role_requirements=sample_target_requirements,
        )

        assert isinstance(result, dict)
        assert result["target_role"] == "senior_engineer"
        assert 0.0 <= result["readiness_score"] <= 1.0
        assert result["total_gaps"] > 0
        assert "gap_analysis" in result

    def test_generate_career_path_recommendations(self, gap_analyzer, sample_current_scores):
        """Test generating career path recommendations"""
        available_roles = {
            "senior_engineer": {
                "technical_skills": 4.0,
                "leadership": 3.0,
                "communication": 3.5,
            },
            "team_lead": {
                "technical_skills": 3.5,
                "leadership": 4.5,
                "communication": 4.0,
            },
        }

        result = gap_analyzer.generate_career_path_recommendations(
            user_id="user123",
            current_scores=sample_current_scores,
            available_roles=available_roles,
            user_context={"role": "engineer", "experience_years": 3},
        )

        assert isinstance(result, list)
        assert len(result) > 0
        assert all("role_name" in r for r in result)
        assert all("readiness_score" in r for r in result)

    def test_create_development_roadmap(self, gap_analyzer):
        """Test creating complete development roadmap"""
        skill_gaps = [
            SkillGap(
                competency_id="technical_skills",
                competency_name="Technical Skills",
                current_score=2.5,
                target_score=4.0,
                gap_size=1.5,
                gap_severity=GapSeverity.MAJOR,
                development_priority=DevelopmentPriority.HIGH,
                estimated_development_time="6-12 months",
                development_difficulty="moderate",
                recommended_activities=["Practice coding", "Take courses"],
            )
        ]

        roadmap = gap_analyzer._create_development_roadmap(
            user_id="user123",
            skill_gaps=skill_gaps,
            priority_gaps=skill_gaps,  # Same as skill_gaps for this test
            user_context={"role": "engineer"},
            target_role="senior_engineer",
        )

        assert isinstance(roadmap, DevelopmentRoadmap)
        assert roadmap.user_id == "user123"
        assert roadmap.target_role == "senior_engineer"
        assert roadmap.total_gaps > 0
        assert len(roadmap.immediate_actions) > 0
        assert len(roadmap.focus_areas) > 0


class TestGlobalGapAnalyzerSingleton:
    """Test global gap analyzer singleton pattern"""

    def test_get_gap_analyzer_returns_singleton(self):
        """Test that get_gap_analyzer returns same instance"""
        analyzer1 = get_gap_analyzer()
        analyzer2 = get_gap_analyzer()

        assert analyzer1 is analyzer2
        assert analyzer1 is not None

    def test_get_gap_analyzer_initialization(self):
        """Test that global analyzer is properly initialized"""
        analyzer = get_gap_analyzer()

        assert analyzer.level_calculator is not None
        assert len(analyzer.skill_transfer_matrix) > 0
        assert len(analyzer.development_activities) > 0

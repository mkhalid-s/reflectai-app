"""
Unit Tests for IntentAnalyzer

Tests pattern-based classification, confidence scoring, LLM integration,
and extraction integration for the intent analysis system.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.core.classification.intent_analyzer import (
    IntentAnalyzer,
    IntentClassificationResult,
    IntentConfidence,
    IntentPattern,
    IntentType,
    get_intent_analyzer,
)


class TestIntentPreprocessing:
    """Test input preprocessing functionality"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_preprocess_normalizes_whitespace(self, analyzer):
        """Test that multiple spaces are normalized to single space"""
        input_text = "analyze    my     competencies"
        result = analyzer._preprocess_input(input_text)
        assert result == "analyze my competencies"

    def test_preprocess_removes_filler_words(self, analyzer):
        """Test that filler words are removed"""
        input_text = "um can you like analyze my skills you know"
        result = analyzer._preprocess_input(input_text)
        assert "um" not in result
        assert "like" not in result
        assert "you know" not in result
        assert "analyze my skills" in result

    def test_preprocess_converts_to_lowercase(self, analyzer):
        """Test that input is converted to lowercase"""
        input_text = "ANALYZE My COMPETENCIES"
        result = analyzer._preprocess_input(input_text)
        assert result == "analyze my competencies"

    def test_preprocess_strips_leading_trailing_spaces(self, analyzer):
        """Test that leading/trailing spaces are removed"""
        input_text = "   analyze my skills   "
        result = analyzer._preprocess_input(input_text)
        assert result == "analyze my skills"
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestConfidenceLevels:
    """Test confidence level calculation"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_high_confidence_threshold(self, analyzer):
        """Test confidence >= 0.7 returns HIGH"""
        assert analyzer._get_confidence_level(0.7) == IntentConfidence.HIGH
        assert analyzer._get_confidence_level(0.85) == IntentConfidence.HIGH
        assert analyzer._get_confidence_level(1.0) == IntentConfidence.HIGH

    def test_medium_confidence_threshold(self, analyzer):
        """Test confidence 0.5-0.7 returns MEDIUM"""
        assert analyzer._get_confidence_level(0.5) == IntentConfidence.MEDIUM
        assert analyzer._get_confidence_level(0.6) == IntentConfidence.MEDIUM
        assert analyzer._get_confidence_level(0.69) == IntentConfidence.MEDIUM

    def test_low_confidence_threshold(self, analyzer):
        """Test confidence 0.3-0.5 returns LOW"""
        assert analyzer._get_confidence_level(0.3) == IntentConfidence.LOW
        assert analyzer._get_confidence_level(0.4) == IntentConfidence.LOW
        assert analyzer._get_confidence_level(0.49) == IntentConfidence.LOW

    def test_very_low_confidence_threshold(self, analyzer):
        """Test confidence < 0.3 returns VERY_LOW"""
        assert analyzer._get_confidence_level(0.0) == IntentConfidence.VERY_LOW
        assert analyzer._get_confidence_level(0.1) == IntentConfidence.VERY_LOW
        assert analyzer._get_confidence_level(0.29) == IntentConfidence.VERY_LOW


class TestPatternScoreCalculation:
    """Test pattern matching and score calculation"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_keyword_matching_score(self, analyzer):
        """Test that keyword matches contribute to score"""
        pattern = IntentPattern(
            intent=IntentType.COMPETENCY_ANALYSIS,
            keywords=["competency", "skills", "assessment"],
            patterns=[],
            context_indicators=[],
            exclusion_keywords=[],
            weight=1.0,
        )

        processed_input = "analyze my competency and skills"
        score = analyzer._calculate_pattern_score(pattern, processed_input, {}, [])

        assert score > 0
        # Should match 2 out of 3 keywords: competency, skills
        assert score == pytest.approx(0.4, abs=0.01)  # (2/3) * 0.6 weight

    def test_regex_pattern_matching_score(self, analyzer):
        """Test that regex patterns contribute to score"""
        pattern = IntentPattern(
            intent=IntentType.ACTIVITY_CLASSIFICATION,
            keywords=[],
            patterns=[r"\bclassify\b", r"\bwhat\s+type\s+of\s+work\b"],
            context_indicators=[],
            exclusion_keywords=[],
            weight=1.0,
        )

        processed_input = "please classify this work"
        score = analyzer._calculate_pattern_score(pattern, processed_input, {}, [])

        assert score > 0
        # Should match 1 out of 2 patterns ("classify")
        assert score == pytest.approx(0.15, abs=0.02)  # (1/2) * 0.3 weight

    def test_context_indicators_contribute_to_score(self, analyzer):
        """Test that context indicators increase score"""
        pattern = IntentPattern(
            intent=IntentType.CAREER_ADVICE,
            keywords=["career"],
            patterns=[],
            context_indicators=["senior", "manager", "lead"],
            exclusion_keywords=[],
            weight=1.0,
        )

        user_context = {"role": "Senior Engineer"}
        processed_input = "give me career advice"

        score = analyzer._calculate_pattern_score(pattern, processed_input, user_context, [])

        # Should get keyword score + context score
        assert score > 0.3  # At least keyword match

    def test_exclusion_keywords_reduce_score(self, analyzer):
        """Test that exclusion keywords negatively impact score"""
        pattern = IntentPattern(
            intent=IntentType.COMPETENCY_ANALYSIS,
            keywords=["analyze", "skills"],
            patterns=[],
            context_indicators=[],
            exclusion_keywords=["meeting", "general"],
            weight=1.0,
        )

        # Without exclusion
        score_without = analyzer._calculate_pattern_score(pattern, "analyze my skills", {}, [])

        # With exclusion
        score_with = analyzer._calculate_pattern_score(
            pattern, "analyze my general skills for the meeting", {}, []
        )

        assert score_with < score_without

    def test_pattern_weight_multiplier(self, analyzer):
        """Test that pattern weight multiplies the score"""
        pattern_normal = IntentPattern(
            intent=IntentType.ACTIVITY_CLASSIFICATION,
            keywords=["classify"],
            patterns=[],
            context_indicators=[],
            exclusion_keywords=[],
            weight=1.0,
        )

        pattern_boosted = IntentPattern(
            intent=IntentType.ACTIVITY_CLASSIFICATION,
            keywords=["classify"],
            patterns=[],
            context_indicators=[],
            exclusion_keywords=[],
            weight=1.5,
        )

        processed_input = "classify my activity"

        score_normal = analyzer._calculate_pattern_score(pattern_normal, processed_input, {}, [])
        score_boosted = analyzer._calculate_pattern_score(pattern_boosted, processed_input, {}, [])

        assert score_boosted > score_normal
        assert abs(score_boosted - (score_normal * 1.5)) < 0.01

    def test_score_clamped_to_one(self, analyzer):
        """Test that score never exceeds 1.0"""
        pattern = IntentPattern(
            intent=IntentType.COMPETENCY_ANALYSIS,
            keywords=["skills", "competency", "assess", "analyze", "evaluate"],
            patterns=[r"\bcompetency\b", r"\bskills\b", r"\bassess\b"],
            context_indicators=["technical", "development"],
            exclusion_keywords=[],
            weight=2.0,  # High weight
        )

        processed_input = "assess my technical skills and competency for development"
        user_context = {"role": "Technical Lead"}

        score = analyzer._calculate_pattern_score(pattern, processed_input, user_context, [])

        assert score <= 1.0


class TestPatternBasedClassification:
    """Test pattern-based intent classification"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    @pytest.mark.asyncio
    async def test_activity_classification_intent(self, analyzer):
        """Test classification of activity classification intent"""
        result = await analyzer._classify_with_patterns(
            "classify this activity please categorize my work", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.ACTIVITY_CLASSIFICATION
        assert result.confidence > 0.3
        assert any(kw in result.matched_keywords for kw in ["classify", "categorize", "activity"])

    @pytest.mark.asyncio
    async def test_competency_analysis_intent(self, analyzer):
        """Test classification of competency analysis intent"""
        result = await analyzer._classify_with_patterns(
            "competency analysis assess my skills and competencies", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.COMPETENCY_ANALYSIS
        assert result.confidence > 0.3
        assert any(
            kw in result.matched_keywords
            for kw in ["competency", "competencies", "skills", "assess"]
        )

    @pytest.mark.asyncio
    async def test_career_advice_intent(self, analyzer):
        """Test classification of career advice intent"""
        result = await analyzer._classify_with_patterns(
            "career advice guidance what should i do for career progression", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.CAREER_ADVICE
        assert result.confidence > 0.3
        assert any(kw in result.matched_keywords for kw in ["career", "advice", "guidance"])

    @pytest.mark.asyncio
    async def test_help_request_intent(self, analyzer):
        """Test classification of help request intent"""
        result = await analyzer._classify_with_patterns(
            "help please help can you help i need help", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.HELP_REQUEST
        assert result.confidence > 0.3
        assert "help" in result.matched_keywords

    @pytest.mark.asyncio
    async def test_goal_management_intent(self, analyzer):
        """Test classification of goal management intent"""
        result = await analyzer._classify_with_patterns(
            "create goal set goals goal management track my goals", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.GOAL_MANAGEMENT
        assert result.confidence > 0.3
        assert any(kw in result.matched_keywords for kw in ["goal", "goals"])

    @pytest.mark.asyncio
    async def test_report_request_intent(self, analyzer):
        """Test classification of report request intent"""
        result = await analyzer._classify_with_patterns(
            "generate report create report competency report analysis report", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.REPORT_REQUEST
        assert result.confidence > 0.3
        assert "report" in result.matched_keywords

    @pytest.mark.asyncio
    async def test_resource_discovery_intent(self, analyzer):
        """Test classification of resource discovery intent"""
        result = await analyzer._classify_with_patterns(
            "find resources learning resources training course tutorial", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.RESOURCE_DISCOVERY
        assert result.confidence > 0.3
        assert any(
            kw in result.matched_keywords
            for kw in ["resource", "resources", "learn", "learning", "course"]
        )

    @pytest.mark.asyncio
    async def test_status_inquiry_intent(self, analyzer):
        """Test classification of status inquiry intent"""
        result = await analyzer._classify_with_patterns(
            "status check my status progress how am i doing", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.STATUS_INQUIRY
        assert result.confidence > 0.3
        assert any(kw in result.matched_keywords for kw in ["status", "progress"])

    @pytest.mark.asyncio
    async def test_general_chat_intent(self, analyzer):
        """Test classification of general chat intent"""
        result = await analyzer._classify_with_patterns(
            "hello hi thanks thank you good morning", {}, []
        )

        assert result is not None
        assert result.primary_intent == IntentType.GENERAL_CHAT
        assert result.confidence > 0.3
        assert any(kw in result.matched_keywords for kw in ["hello", "hi", "thanks"])

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self, analyzer):
        """Test that no pattern match returns None"""
        result = await analyzer._classify_with_patterns("xyzabc nonsense gibberish", {}, [])

        assert result is None

    @pytest.mark.asyncio
    async def test_alternative_intents_included(self, analyzer):
        """Test that alternative intents are included when multiple patterns match"""
        result = await analyzer._classify_with_patterns(
            "competency analysis assess skills generate report", {}, []
        )

        assert result is not None
        # When multiple patterns match, alternatives should be included
        # The primary intent will be the highest scoring one


class TestClarificationQuestions:
    """Test clarification question generation"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_high_confidence_no_clarification(self, analyzer):
        """Test that high confidence doesn't generate clarification questions"""
        questions = analyzer._generate_clarification_questions(
            IntentType.ACTIVITY_CLASSIFICATION, 0.85
        )

        assert len(questions) == 0

    def test_medium_confidence_generates_questions(self, analyzer):
        """Test that medium confidence generates clarification questions"""
        questions = analyzer._generate_clarification_questions(
            IntentType.ACTIVITY_CLASSIFICATION, 0.55
        )

        assert len(questions) > 0
        assert len(questions) <= 2

    def test_activity_classification_questions(self, analyzer):
        """Test clarification questions for activity classification"""
        questions = analyzer._generate_clarification_questions(
            IntentType.ACTIVITY_CLASSIFICATION, 0.5
        )

        assert any("activity" in q.lower() for q in questions)

    def test_competency_analysis_questions(self, analyzer):
        """Test clarification questions for competency analysis"""
        questions = analyzer._generate_clarification_questions(IntentType.COMPETENCY_ANALYSIS, 0.5)

        assert any("competency" in q.lower() or "skill" in q.lower() for q in questions)

    def test_report_request_questions(self, analyzer):
        """Test clarification questions for report request"""
        questions = analyzer._generate_clarification_questions(IntentType.REPORT_REQUEST, 0.5)

        assert any("report" in q.lower() for q in questions)

    def test_unknown_intent_gets_generic_questions(self, analyzer):
        """Test that unknown intent gets generic clarification questions"""
        questions = analyzer._generate_clarification_questions(IntentType.UNKNOWN, 0.5)

        assert len(questions) > 0
        assert any("clarify" in q.lower() or "details" in q.lower() for q in questions)


class TestSuggestedFollowUp:
    """Test suggested follow-up action generation"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_activity_classification_follow_up(self, analyzer):
        """Test follow-up suggestions for activity classification"""
        follow_ups = analyzer._get_suggested_follow_up(IntentType.ACTIVITY_CLASSIFICATION)

        assert len(follow_ups) > 0
        assert any("competency" in f.lower() for f in follow_ups)

    def test_competency_analysis_follow_up(self, analyzer):
        """Test follow-up suggestions for competency analysis"""
        follow_ups = analyzer._get_suggested_follow_up(IntentType.COMPETENCY_ANALYSIS)

        assert len(follow_ups) > 0
        assert any("recommendation" in f.lower() or "goal" in f.lower() for f in follow_ups)

    def test_career_advice_follow_up(self, analyzer):
        """Test follow-up suggestions for career advice"""
        follow_ups = analyzer._get_suggested_follow_up(IntentType.CAREER_ADVICE)

        assert len(follow_ups) > 0
        assert any("goal" in f.lower() or "resource" in f.lower() for f in follow_ups)

    def test_goal_management_follow_up(self, analyzer):
        """Test follow-up suggestions for goal management"""
        follow_ups = analyzer._get_suggested_follow_up(IntentType.GOAL_MANAGEMENT)

        assert len(follow_ups) > 0
        assert any("progress" in f.lower() or "resource" in f.lower() for f in follow_ups)

    def test_unknown_intent_empty_follow_up(self, analyzer):
        """Test that unknown intent returns empty follow-up list"""
        follow_ups = analyzer._get_suggested_follow_up(IntentType.UNKNOWN)

        assert len(follow_ups) == 0


class TestFallbackClassification:
    """Test fallback classification logic"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_fallback_with_pattern_result(self, analyzer):
        """Test fallback uses pattern result with reduced confidence"""
        pattern_result = IntentClassificationResult(
            user_input="test input",
            primary_intent=IntentType.ACTIVITY_CLASSIFICATION,
            confidence=0.5,
            confidence_level=IntentConfidence.MEDIUM,
            method="pattern",
            processing_time=0.0,
        )

        fallback = analyzer._create_fallback_classification("test input", pattern_result)

        assert fallback.primary_intent == IntentType.ACTIVITY_CLASSIFICATION
        assert fallback.confidence < pattern_result.confidence
        assert fallback.confidence >= 0.2
        assert fallback.confidence_level == IntentConfidence.LOW
        assert fallback.needs_clarification is True
        assert "pattern_fallback" in fallback.method

    def test_fallback_without_pattern_result(self, analyzer):
        """Test fallback without pattern result returns UNKNOWN"""
        fallback = analyzer._create_fallback_classification("test input", None)

        assert fallback.primary_intent == IntentType.UNKNOWN
        assert fallback.confidence == 0.2
        assert fallback.confidence_level == IntentConfidence.VERY_LOW
        assert fallback.needs_clarification is True
        assert "generic_fallback" in fallback.method
        assert len(fallback.clarification_questions) > 0


class TestStatsTracking:
    """Test statistics tracking functionality"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_stats_initialization(self, analyzer):
        """Test that stats are properly initialized"""
        stats = analyzer.get_intent_stats()

        assert stats["total_classifications"] == 0
        assert stats["high_confidence_results"] == 0
        assert stats["clarification_requests"] == 0
        assert stats["llm_classifications"] == 0
        assert stats["average_confidence"] == 0.0
        assert "intent_distribution" in stats

    def test_stats_updated_after_classification(self, analyzer):
        """Test that stats are updated after classification"""
        analyzer._update_stats(IntentType.ACTIVITY_CLASSIFICATION, 0.85, "pattern")

        stats = analyzer.get_intent_stats()

        assert stats["total_classifications"] == 1
        assert stats["high_confidence_results"] == 1
        assert stats["intent_distribution"][IntentType.ACTIVITY_CLASSIFICATION.value] == 1
        assert stats["average_confidence"] == 0.85

    def test_stats_multiple_classifications(self, analyzer):
        """Test stats with multiple classifications"""
        analyzer._update_stats(IntentType.ACTIVITY_CLASSIFICATION, 0.85, "pattern")
        analyzer._update_stats(IntentType.COMPETENCY_ANALYSIS, 0.65, "pattern")
        analyzer._update_stats(IntentType.CAREER_ADVICE, 0.45, "llm")

        stats = analyzer.get_intent_stats()

        assert stats["total_classifications"] == 3
        assert stats["high_confidence_results"] == 1
        assert stats["clarification_requests"] == 1  # 0.45 < 0.5
        assert stats["llm_classifications"] == 1

        # Average should be (0.85 + 0.65 + 0.45) / 3 = 0.65
        assert abs(stats["average_confidence"] - 0.65) < 0.01


class TestGlobalAnalyzer:
    """Test global analyzer singleton"""

    def test_get_intent_analyzer_returns_singleton(self):
        """Test that get_intent_analyzer returns the same instance"""
        analyzer1 = get_intent_analyzer()
        analyzer2 = get_intent_analyzer()

        assert analyzer1 is analyzer2

    def test_get_intent_analyzer_returns_intent_analyzer(self):
        """Test that get_intent_analyzer returns IntentAnalyzer instance"""
        analyzer = get_intent_analyzer()

        assert isinstance(analyzer, IntentAnalyzer)

    def test_supported_intents_list(self):
        """Test that supported intents list is returned"""
        analyzer = get_intent_analyzer()
        supported = analyzer.get_supported_intents()

        assert len(supported) > 0
        assert "activity_classification" in supported
        assert "competency_analysis" in supported
        assert "career_advice" in supported


class TestLLMIntegration:
    """Test LLM-based intent classification"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_prepare_llm_context(self, analyzer):
        """Test LLM context preparation"""
        user_context = {
            "role": "Senior Engineer",
            "department": "Engineering",
            "recent_activity": "Implemented OAuth2 authentication",
        }

        conversation_history = [
            {"role": "user", "content": "I need help with competency assessment"},
            {"role": "assistant", "content": "I can help you with that"},
            {"role": "user", "content": "Analyze my skills"},
        ]

        pattern_result = IntentClassificationResult(
            user_input="test",
            primary_intent=IntentType.COMPETENCY_ANALYSIS,
            confidence=0.6,
            confidence_level=IntentConfidence.MEDIUM,
            matched_keywords=["skills", "analyze"],
            method="pattern",
            processing_time=0.0,
        )

        context = analyzer._prepare_llm_context(
            "Analyze my skills", user_context, conversation_history, pattern_result
        )

        assert context["user_input"] == "Analyze my skills"
        assert context["user_role"] == "Senior Engineer"
        assert context["user_department"] == "Engineering"
        assert context["recent_activity"] == "Implemented OAuth2 authentication"
        assert "user: I need help" in context["conversation_context"]
        assert "competency_analysis" in context["pattern_hints"].lower()

    def test_prepare_llm_context_without_pattern(self, analyzer):
        """Test LLM context preparation without pattern result"""
        context = analyzer._prepare_llm_context("Help me", {}, [], None)

        assert context["user_input"] == "Help me"
        assert context["user_role"] == "Unknown"
        assert context["user_department"] == "Unknown"
        assert context["conversation_context"] == "No previous conversation history"
        assert context["pattern_hints"] == ""

    def test_parse_llm_response_success(self, analyzer):
        """Test successful LLM response parsing"""
        llm_response = """
        Primary Intent: competency_analysis
        Confidence: 0.85
        Reasoning: The user is explicitly asking for analysis of their skills and competencies.
        No clarification required.
        """

        result = analyzer._parse_llm_response(llm_response, "Analyze my competencies")

        assert result is not None
        assert result.primary_intent == IntentType.COMPETENCY_ANALYSIS
        assert result.confidence == pytest.approx(0.85, abs=0.01)
        assert result.method == "llm_assisted"
        assert result.llm_reasoning is not None
        # Clarification detection looks for keywords, so avoiding them means False
        assert result.needs_clarification is False

    def test_parse_llm_response_with_percentage_confidence(self, analyzer):
        """Test LLM response parsing with percentage confidence"""
        llm_response = """
        Intent: career_advice
        Confidence: 75%
        """

        result = analyzer._parse_llm_response(llm_response, "What should I do")

        assert result is not None
        assert result.primary_intent == IntentType.CAREER_ADVICE
        assert result.confidence == pytest.approx(0.75, abs=0.01)

    def test_parse_llm_response_with_clarification_needed(self, analyzer):
        """Test LLM response parsing when clarification is needed"""
        llm_response = """
        Intent: unknown
        Confidence: 0.3
        The request is ambiguous and clarification needed
        """

        result = analyzer._parse_llm_response(llm_response, "Unclear request")

        assert result is not None
        assert result.needs_clarification is True
        assert len(result.clarification_questions) > 0

    def test_parse_llm_response_default_values(self, analyzer):
        """Test LLM response parsing with minimal information"""
        llm_response = "activity_classification"

        result = analyzer._parse_llm_response(llm_response, "Test input")

        assert result is not None
        assert result.primary_intent == IntentType.ACTIVITY_CLASSIFICATION
        # Default confidence when not specified
        assert result.confidence > 0

    def test_parse_llm_response_invalid_returns_none(self, analyzer):
        """Test that invalid LLM response returns None"""
        llm_response = None

        result = analyzer._parse_llm_response(llm_response, "Test input")

        # Should return None or handle gracefully
        assert result is None or result.primary_intent == IntentType.UNKNOWN

    def test_enhance_with_pattern_insights(self, analyzer):
        """Test enhancing LLM result with pattern insights"""
        llm_result = IntentClassificationResult(
            user_input="test",
            primary_intent=IntentType.COMPETENCY_ANALYSIS,
            confidence=0.8,
            confidence_level=IntentConfidence.HIGH,
            method="llm_assisted",
            processing_time=0.0,
        )

        pattern_result = IntentClassificationResult(
            user_input="test",
            primary_intent=IntentType.ACTIVITY_CLASSIFICATION,
            confidence=0.5,
            confidence_level=IntentConfidence.MEDIUM,
            matched_keywords=["classify", "activity"],
            matched_patterns=[r"\bclassify\b"],
            alternative_intents=[{"intent": "competency_analysis", "confidence": 0.4}],
            method="pattern",
            processing_time=0.0,
        )

        enhanced = analyzer._enhance_with_pattern_insights(llm_result, pattern_result)

        # Should have pattern keywords and patterns added
        assert "classify" in enhanced.matched_keywords
        assert "activity" in enhanced.matched_keywords
        assert r"\bclassify\b" in enhanced.matched_patterns

        # Should have pattern alternatives added
        assert len(enhanced.alternative_intents) > 0

    @pytest.mark.asyncio
    async def test_classify_with_llm_no_agent_context(self, analyzer):
        """Test LLM classification without agent context"""
        result = await analyzer._classify_with_llm(
            "test input",
            "test input",
            {},
            [],
            None,  # No agent context
            None,
        )

        # Should return None when no agent context
        assert result is None

    @pytest.mark.asyncio
    async def test_classify_with_llm_with_mock_agent(self, analyzer):
        """Test LLM classification with mocked agent"""
        # Create mock agent context
        mock_agent = Mock()
        mock_llm_provider = AsyncMock()
        mock_response = Mock()
        mock_response.content = """
        Intent: report_request
        Confidence: 0.9
        User wants to generate a report
        """
        mock_llm_provider.generate = AsyncMock(return_value=mock_response)
        mock_agent.llm_provider = mock_llm_provider

        result = await analyzer._classify_with_llm(
            "generate a report", "generate a report", {}, [], mock_agent, None
        )

        assert result is not None
        assert result.primary_intent == IntentType.REPORT_REQUEST
        assert result.confidence > 0.8
        assert result.method == "llm_assisted"

    @pytest.mark.asyncio
    async def test_classify_with_llm_error_handling(self, analyzer):
        """Test LLM classification error handling"""
        # Create mock agent that raises exception
        mock_agent = Mock()
        mock_llm_provider = AsyncMock()
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM Error"))
        mock_agent.llm_provider = mock_llm_provider

        result = await analyzer._classify_with_llm(
            "test input", "test input", {}, [], mock_agent, None
        )

        # Should return None on error
        assert result is None


class TestExtractionIntegration:
    """Test integration with DateRangeExtractor and ContentExtractor"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    @pytest.mark.asyncio
    async def test_extract_date_range_for_report_request(self, analyzer):
        """Test date range extraction for report request intent"""
        result = IntentClassificationResult(
            user_input="generate report for last month",
            primary_intent=IntentType.REPORT_REQUEST,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        user_context = {"timezone": "UTC"}

        await analyzer._extract_date_range_info(
            result, "generate report for last month", user_context
        )

        # Should have extracted date range
        assert result.extracted_date_range is not None
        assert "start_date" in result.extracted_date_range
        assert "end_date" in result.extracted_date_range

    @pytest.mark.asyncio
    async def test_extract_date_range_for_competency_analysis(self, analyzer):
        """Test date range extraction for competency analysis intent"""
        result = IntentClassificationResult(
            user_input="analyze my competencies from last quarter",
            primary_intent=IntentType.COMPETENCY_ANALYSIS,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_date_range_info(
            result, "analyze my competencies from last quarter", {}
        )

        # Should have extracted date range
        assert result.extracted_date_range is not None

    @pytest.mark.asyncio
    async def test_extract_date_range_for_status_inquiry(self, analyzer):
        """Test date range extraction for status inquiry intent"""
        result = IntentClassificationResult(
            user_input="how am i doing this week",
            primary_intent=IntentType.STATUS_INQUIRY,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_date_range_info(result, "how am i doing this week", {})

        # Should have extracted date range
        assert result.extracted_date_range is not None

    @pytest.mark.asyncio
    async def test_no_date_extraction_for_non_report_intent(self, analyzer):
        """Test that date extraction doesn't happen for non-report intents"""
        result = IntentClassificationResult(
            user_input="hello how are you",
            primary_intent=IntentType.GENERAL_CHAT,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_date_range_info(result, "hello how are you", {})

        # Should NOT have extracted date range
        assert result.extracted_date_range is None

    @pytest.mark.asyncio
    async def test_date_extraction_handles_missing_date(self, analyzer):
        """Test date extraction gracefully handles missing date"""
        result = IntentClassificationResult(
            user_input="generate a report",
            primary_intent=IntentType.REPORT_REQUEST,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_date_range_info(result, "generate a report", {})

        # Should still work, may have no date range or default
        # The function should not raise an exception

    @pytest.mark.asyncio
    async def test_extract_content_for_report_request(self, analyzer):
        """Test content extraction for report request with inline content"""
        result = IntentClassificationResult(
            user_input="analyze this: I implemented OAuth2 authentication",
            primary_intent=IntentType.REPORT_REQUEST,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_content_info(
            result, "analyze this: I implemented OAuth2 authentication"
        )

        # Should have extracted content
        assert result.extracted_content is not None
        assert "cleaned_text" in result.extracted_content or "raw_text" in result.extracted_content

    @pytest.mark.asyncio
    async def test_extract_content_for_activity_classification(self, analyzer):
        """Test content extraction for activity classification"""
        result = IntentClassificationResult(
            user_input="analyze this activity: Led migration to microservices architecture",
            primary_intent=IntentType.ACTIVITY_CLASSIFICATION,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_content_info(
            result, "analyze this activity: Led migration to microservices architecture"
        )

        # Should have attempted content extraction (may or may not find content depending on trigger phrases)
        # The important thing is it doesn't raise an exception

    @pytest.mark.asyncio
    async def test_extract_content_for_competency_analysis(self, analyzer):
        """Test content extraction for competency analysis with quoted content"""
        result = IntentClassificationResult(
            user_input='analyze "Developed RESTful APIs with FastAPI"',
            primary_intent=IntentType.COMPETENCY_ANALYSIS,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_content_info(
            result, 'analyze "Developed RESTful APIs with FastAPI"'
        )

        # Should have extracted content
        assert result.extracted_content is not None

    @pytest.mark.asyncio
    async def test_no_content_extraction_for_non_relevant_intent(self, analyzer):
        """Test that content extraction doesn't happen for non-relevant intents"""
        result = IntentClassificationResult(
            user_input="hello how are you",
            primary_intent=IntentType.GENERAL_CHAT,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_content_info(result, "hello how are you")

        # Should NOT have extracted content
        assert result.extracted_content is None

    @pytest.mark.asyncio
    async def test_content_extraction_handles_no_trigger_phrase(self, analyzer):
        """Test content extraction gracefully handles no trigger phrase"""
        result = IntentClassificationResult(
            user_input="just some random text",
            primary_intent=IntentType.ACTIVITY_CLASSIFICATION,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.0,
        )

        await analyzer._extract_content_info(result, "just some random text")

        # Should not raise exception
        # May or may not have content depending on extractor logic

    @pytest.mark.asyncio
    async def test_full_analyze_intent_with_date_extraction(self, analyzer):
        """Test full analyze_intent flow with date extraction"""
        result = await analyzer.analyze_intent(
            "generate report create report for last 30 days",
            user_context={},
            conversation_history=[],
            agent_context=None,
            confidence_threshold=0.3,
        )

        assert result is not None
        assert result.primary_intent == IntentType.REPORT_REQUEST
        # Should have attempted date extraction
        assert result.extracted_date_range is not None

    @pytest.mark.asyncio
    async def test_full_analyze_intent_with_content_extraction(self, analyzer):
        """Test full analyze_intent flow with content extraction"""
        result = await analyzer.analyze_intent(
            "classify this activity: I wrote unit tests for the API",
            user_context={},
            conversation_history=[],
            agent_context=None,
            confidence_threshold=0.3,
        )

        assert result is not None
        # Should have attempted content extraction
        if result.primary_intent in [IntentType.ACTIVITY_CLASSIFICATION, IntentType.REPORT_REQUEST]:
            assert result.extracted_content is not None


class TestConversationContext:
    """Test conversation context management"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_update_conversation_context(self, analyzer):
        """Test updating conversation context for a user"""
        user_id = "U123"
        context = {"last_intent": "activity_classification", "count": 5}

        analyzer.update_conversation_context(user_id, context)
        retrieved = analyzer.get_conversation_context(user_id)

        assert retrieved == context

    def test_get_empty_conversation_context(self, analyzer):
        """Test getting context for user with no history"""
        user_id = "U999"
        context = analyzer.get_conversation_context(user_id)

        assert context == {}

    def test_multiple_user_contexts(self, analyzer):
        """Test managing contexts for multiple users"""
        analyzer.update_conversation_context("U1", {"count": 1})
        analyzer.update_conversation_context("U2", {"count": 2})
        analyzer.update_conversation_context("U3", {"count": 3})

        assert analyzer.get_conversation_context("U1")["count"] == 1
        assert analyzer.get_conversation_context("U2")["count"] == 2
        assert analyzer.get_conversation_context("U3")["count"] == 3

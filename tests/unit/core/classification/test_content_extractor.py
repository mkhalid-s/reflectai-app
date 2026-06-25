"""
Unit tests for ContentExtractor

Tests all extraction methods and edge cases for activity content extraction.
Ensures comprehensive coverage of inline content parsing.
"""

import sys
from pathlib import Path

# Add project root to path to allow direct import
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest

# Direct import to avoid circular dependencies
from src.core.classification.content_extractor import (
    ContentExtractor,
    ExtractionMethod,
    get_content_extractor,
    reset_content_extractor,
)


@pytest.fixture
def extractor():
    """Content extractor instance"""
    reset_content_extractor()  # Clear singleton
    return ContentExtractor()


class TestDelimiterExtraction:
    """Test delimiter-based content extraction"""

    @pytest.mark.asyncio
    async def test_analyze_this_colon(self, extractor):
        """Test: 'analyze this: [content]' extraction"""
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented a microservices platform with Kubernetes"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert result.confidence == 0.95
        assert "microservices platform" in result.raw_text
        assert result.trigger_phrase is not None
        assert "analyze this" in result.trigger_phrase.lower()

    @pytest.mark.asyncio
    async def test_assess_this_colon(self, extractor):
        """Test: 'assess this: [content]' extraction"""
        result = await extractor.extract_activity_content(
            "Assess this: Led team of 5 engineers to deliver project on time"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert result.confidence == 0.95
        assert "Led team" in result.raw_text

    @pytest.mark.asyncio
    async def test_evaluate_the_following(self, extractor):
        """Test: 'evaluate the following:' extraction"""
        result = await extractor.extract_activity_content(
            "Evaluate the following: Developed RESTful API with FastAPI and async patterns"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert "RESTful API" in result.raw_text

    @pytest.mark.asyncio
    async def test_report_on_this(self, extractor):
        """Test: 'report on this:' extraction"""
        result = await extractor.extract_activity_content(
            "Report on this: Optimized database queries reducing response time by 40%"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert "database queries" in result.raw_text

    @pytest.mark.asyncio
    async def test_this_activity_delimiter(self, extractor):
        """Test: 'this activity:' extraction"""
        result = await extractor.extract_activity_content(
            "This activity: Designed and implemented OAuth2 authentication system"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert result.confidence == 0.92  # Slightly lower confidence
        assert "OAuth2" in result.raw_text

    @pytest.mark.asyncio
    async def test_my_activity_delimiter(self, extractor):
        """Test: 'my activity:' extraction"""
        result = await extractor.extract_activity_content(
            "My activity: Created CI/CD pipeline using GitHub Actions"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert "CI/CD pipeline" in result.raw_text

    @pytest.mark.asyncio
    async def test_case_insensitive_delimiter(self, extractor):
        """Test: Case insensitive delimiter matching"""
        result = await extractor.extract_activity_content(
            "ANALYZE THIS: Built monitoring dashboard with Grafana"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.DELIMITER
        assert "monitoring dashboard" in result.raw_text


class TestContextExtraction:
    """Test context-based content extraction"""

    @pytest.mark.asyncio
    async def test_i_implemented(self, extractor):
        """Test: 'I implemented' context extraction"""
        result = await extractor.extract_activity_content(
            "I implemented a distributed caching layer using Redis"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.CONTEXT
        assert result.confidence == 0.80
        assert "I implemented" in result.raw_text
        assert result.trigger_phrase == "I implemented"

    @pytest.mark.asyncio
    async def test_i_developed(self, extractor):
        """Test: 'I developed' context extraction"""
        result = await extractor.extract_activity_content(
            "I developed a machine learning model for fraud detection"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.CONTEXT
        assert "machine learning model" in result.raw_text

    @pytest.mark.asyncio
    async def test_i_led(self, extractor):
        """Test: 'I led' context extraction"""
        result = await extractor.extract_activity_content(
            "I led the migration from monolith to microservices architecture"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.CONTEXT
        assert "migration" in result.raw_text

    @pytest.mark.asyncio
    async def test_we_implemented(self, extractor):
        """Test: 'we implemented' context extraction"""
        result = await extractor.extract_activity_content(
            "We implemented real-time data streaming with Apache Kafka"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.CONTEXT
        assert "Kafka" in result.raw_text

    @pytest.mark.asyncio
    async def test_our_team(self, extractor):
        """Test: 'our team' context extraction"""
        result = await extractor.extract_activity_content(
            "Our team built a scalable API gateway handling 10k requests per second"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.CONTEXT
        assert "API gateway" in result.raw_text

    @pytest.mark.asyncio
    async def test_multiple_indicators_earliest_wins(self, extractor):
        """Test: When multiple indicators exist, extract from earliest"""
        result = await extractor.extract_activity_content(
            "Last week I implemented authentication. Then I developed the dashboard."
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.CONTEXT
        # Should start from the earliest indicator
        assert "I implemented" in result.raw_text


class TestQuotedContentExtraction:
    """Test quoted content extraction"""

    @pytest.mark.asyncio
    async def test_double_quoted_content(self, extractor):
        """Test: Content in double quotes"""
        result = await extractor.extract_activity_content(
            'Analyze "I led the implementation of OAuth2 authentication system"'
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.EXPLICIT
        assert result.confidence == 0.88
        assert "OAuth2" in result.raw_text
        assert result.raw_text.strip() == "I led the implementation of OAuth2 authentication system"

    @pytest.mark.asyncio
    async def test_single_quoted_content(self, extractor):
        """Test: Content in single quotes"""
        result = await extractor.extract_activity_content(
            "Report on 'Developed RESTful API with FastAPI and PostgreSQL database integration'"
        )

        assert result is not None
        assert result.extraction_method == ExtractionMethod.EXPLICIT
        assert "RESTful API" in result.raw_text

    @pytest.mark.asyncio
    async def test_quotes_without_trigger_ignored(self, extractor):
        """Test: Quotes without trigger phrase are ignored"""
        result = await extractor.extract_activity_content('I said "hello" to my colleague')

        # Should fall through to context extraction instead
        if result:
            assert result.extraction_method != ExtractionMethod.EXPLICIT


class TestMultipleActivitiesExtraction:
    """Test extraction of multiple activities"""

    def test_numbered_list(self, extractor):
        """Test: Extract multiple activities from numbered list"""
        message = """
        1. Implemented microservices architecture for payment system
        2. Developed RESTful APIs with FastAPI and async patterns
        3. Optimized database queries reducing response time by 40%
        """

        activities = extractor.extract_multiple_activities(message)

        assert len(activities) == 3
        assert all(act.extraction_method == ExtractionMethod.EXPLICIT for act in activities)
        assert all(act.confidence == 0.85 for act in activities)
        assert "microservices" in activities[0].raw_text
        assert "RESTful APIs" in activities[1].raw_text
        assert "database queries" in activities[2].raw_text

    def test_bullet_list(self, extractor):
        """Test: Extract multiple activities from bullet list"""
        message = """
        - Built monitoring dashboard with Grafana and Prometheus
        - Created CI/CD pipeline using GitHub Actions
        - Mentored junior developer on code review best practices
        """

        activities = extractor.extract_multiple_activities(message)

        assert len(activities) == 3
        assert all(act.extraction_method == ExtractionMethod.EXPLICIT for act in activities)
        assert all(act.confidence == 0.83 for act in activities)
        assert "Grafana" in activities[0].raw_text
        assert "CI/CD" in activities[1].raw_text
        assert "Mentored" in activities[2].raw_text

    def test_single_activity_fallback(self, extractor):
        """Test: Falls back to single extraction if no list found"""
        message = "I implemented a distributed caching layer"

        activities = extractor.extract_multiple_activities(message)

        assert len(activities) == 1
        assert activities[0].extraction_method == ExtractionMethod.CONTEXT


class TestContentValidation:
    """Test content validation logic"""

    @pytest.mark.asyncio
    async def test_too_short_content_rejected(self, extractor):
        """Test: Content < 20 characters is rejected"""
        result = await extractor.extract_activity_content("Analyze this: Short")

        assert result is None

    @pytest.mark.asyncio
    async def test_just_trigger_phrase_rejected(self, extractor):
        """Test: Content that's just the trigger phrase is rejected"""
        result = await extractor.extract_activity_content("Analyze this")

        assert result is None

    @pytest.mark.asyncio
    async def test_insufficient_alpha_chars_rejected(self, extractor):
        """Test: Content with < 15 alpha characters is rejected"""
        result = await extractor.extract_activity_content("Analyze this: 123 456 789 000")

        assert result is None

    @pytest.mark.asyncio
    async def test_valid_long_content_accepted(self, extractor):
        """Test: Valid substantial content is accepted"""
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented a comprehensive authentication system"
        )

        assert result is not None


class TestContentCleaning:
    """Test content cleaning functionality"""

    @pytest.mark.asyncio
    async def test_whitespace_normalization(self, extractor):
        """Test: Extra whitespace is normalized"""
        result = await extractor.extract_activity_content(
            "Analyze this: I    implemented   a    microservices   platform"
        )

        assert result is not None
        assert "  " not in result.cleaned_text  # No double spaces
        assert result.cleaned_text == "I implemented a microservices platform"

    @pytest.mark.asyncio
    async def test_trailing_punctuation_removed(self, extractor):
        """Test: Trailing commas/semicolons/colons are removed"""
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented OAuth2 authentication,;"
        )

        assert result is not None
        assert not result.cleaned_text.endswith(",")
        assert not result.cleaned_text.endswith(";")

    @pytest.mark.asyncio
    async def test_very_long_content_truncated(self, extractor):
        """Test: Content > 2000 chars is truncated"""
        long_content = "I implemented " + ("x" * 2500)
        result = await extractor.extract_activity_content(f"Analyze this: {long_content}")

        assert result is not None
        assert len(result.cleaned_text) <= 2003  # 2000 + "..."
        assert result.cleaned_text.endswith("...")


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_string(self, extractor):
        """Test: Empty string returns None"""
        result = await extractor.extract_activity_content("")

        assert result is None

    @pytest.mark.asyncio
    async def test_none_input(self, extractor):
        """Test: None input returns None"""
        result = await extractor.extract_activity_content(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_very_short_message(self, extractor):
        """Test: Message < 10 chars returns None"""
        result = await extractor.extract_activity_content("Short")

        assert result is None

    @pytest.mark.asyncio
    async def test_no_content_found(self, extractor):
        """Test: Message with no extractable content returns None"""
        result = await extractor.extract_activity_content("Hello, how are you doing today?")

        assert result is None

    @pytest.mark.asyncio
    async def test_delimiter_priority_over_context(self, extractor):
        """Test: Delimiter method has priority over context"""
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented auth. I also developed the UI."
        )

        assert result is not None
        # Should use delimiter, not context
        assert result.extraction_method == ExtractionMethod.DELIMITER
        # Should not include "Analyze this:"
        assert not result.raw_text.startswith("Analyze")

    @pytest.mark.asyncio
    async def test_multiline_content(self, extractor):
        """Test: Multi-line content is handled"""
        result = await extractor.extract_activity_content(
            """Analyze this: I implemented a microservices platform
            with Kubernetes orchestration and
            distributed caching using Redis"""
        )

        assert result is not None
        assert "Kubernetes" in result.raw_text
        assert "Redis" in result.raw_text


class TestToDict:
    """Test ActivityContent to_dict method"""

    @pytest.mark.asyncio
    async def test_to_dict_serialization(self, extractor):
        """Test: ActivityContent can be serialized to dictionary"""
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented microservices"
        )

        assert result is not None
        dict_result = result.to_dict()

        assert isinstance(dict_result, dict)
        assert "raw_text" in dict_result
        assert "extraction_method" in dict_result
        assert "confidence" in dict_result
        assert "cleaned_text" in dict_result
        assert "trigger_phrase" in dict_result

        # Check values
        assert dict_result["extraction_method"] == "delimiter"
        assert dict_result["confidence"] == 0.95


class TestSingletonPattern:
    """Test singleton getter"""

    def test_get_content_extractor_singleton(self):
        """Test: get_content_extractor returns singleton"""
        reset_content_extractor()

        instance1 = get_content_extractor()
        instance2 = get_content_extractor()

        assert instance1 is instance2

    def test_reset_content_extractor(self):
        """Test: reset_content_extractor clears singleton"""
        instance1 = get_content_extractor()
        reset_content_extractor()
        instance2 = get_content_extractor()

        assert instance1 is not instance2


class TestConfidenceScores:
    """Test confidence scores for different methods"""

    @pytest.mark.asyncio
    async def test_delimiter_high_confidence(self, extractor):
        """Test: Delimiter extraction has highest confidence (0.95)"""
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented microservices"
        )

        assert result is not None
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_activity_delimiter_medium_high_confidence(self, extractor):
        """Test: Activity delimiter has 0.92 confidence"""
        result = await extractor.extract_activity_content(
            "This activity: Built API gateway with load balancing and caching"
        )

        assert result is not None
        assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_quoted_content_medium_confidence(self, extractor):
        """Test: Quoted content has 0.88 confidence"""
        result = await extractor.extract_activity_content(
            'Analyze "I implemented authentication system with OAuth2 and JWT tokens"'
        )

        assert result is not None
        assert result.confidence == 0.88

    @pytest.mark.asyncio
    async def test_context_medium_confidence(self, extractor):
        """Test: Context extraction has 0.80 confidence"""
        result = await extractor.extract_activity_content(
            "I implemented a distributed caching layer"
        )

        assert result is not None
        assert result.confidence == 0.80


class TestTriggerPhrases:
    """Test various trigger phrases"""

    @pytest.mark.asyncio
    async def test_all_delimiter_triggers(self, extractor):
        """Test: All delimiter trigger phrases work"""
        triggers = [
            "analyze this:",
            "assess this:",
            "evaluate this:",
            "report on this:",
            "analyze the following:",
            "assess the following:",
        ]

        for trigger in triggers:
            result = await extractor.extract_activity_content(
                f"{trigger} I implemented microservices with Kubernetes"
            )

            assert result is not None, f"Failed for trigger: {trigger}"
            assert result.extraction_method == ExtractionMethod.DELIMITER

    @pytest.mark.asyncio
    async def test_all_context_indicators(self, extractor):
        """Test: Various activity indicators work"""
        indicators = [
            "I implemented",
            "I developed",
            "I led",
            "I managed",
            "we implemented",
            "our team built",
        ]

        for indicator in indicators:
            result = await extractor.extract_activity_content(
                f"{indicator} a complex distributed system with high availability"
            )

            assert result is not None, f"Failed for indicator: {indicator}"
            assert result.extraction_method == ExtractionMethod.CONTEXT

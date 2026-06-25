"""
Content Extraction for ReflectAI

Extracts activity content from natural language user input for inline analysis.
Supports various extraction methods:
- Delimiter-based: "analyze this: [CONTENT]", "assess this activity: [CONTENT]"
- Context-based: Detects activity indicators like "I implemented", "I led"
- Multi-line: Handles multi-line activity descriptions

This component is critical for enabling inline content analysis workflows
where users provide activity descriptions directly in their messages.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.shared import get_logger


class ExtractionMethod(Enum):
    """Methods used to extract content"""

    DELIMITER = "delimiter"
    CONTEXT = "context"
    EXPLICIT = "explicit"
    UNKNOWN = "unknown"


@dataclass
class ActivityContent:
    """Represents extracted activity content"""

    raw_text: str
    extraction_method: ExtractionMethod
    confidence: float  # 0.0-1.0
    cleaned_text: str | None = None
    trigger_phrase: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "raw_text": self.raw_text,
            "extraction_method": self.extraction_method.value,
            "confidence": self.confidence,
            "cleaned_text": self.cleaned_text or self.raw_text,
            "trigger_phrase": self.trigger_phrase,
        }


class ContentExtractor:
    """
    Extract activity content from natural language text.

    Uses pattern matching and context analysis to identify and extract
    activity descriptions from user messages. Provides confidence scoring
    for routing and validation logic.

    Usage:
        extractor = get_content_extractor()
        result = await extractor.extract_activity_content(
            "Analyze this: I implemented a microservices platform"
        )
    """

    def __init__(self):
        """Initialize content extractor."""
        self.logger = get_logger("classification.content")
        self._compile_patterns()

        # Activity indicators - common phrases that suggest activity descriptions
        self.activity_indicators = [
            "I implemented",
            "I developed",
            "I built",
            "I created",
            "I designed",
            "I architected",
            "I deployed",
            "I launched",
            "I led",
            "I managed",
            "I coordinated",
            "I organized",
            "I mentored",
            "I coached",
            "I trained",
            "I guided",
            "I analyzed",
            "I researched",
            "I investigated",
            "I evaluated",
            "I optimized",
            "I improved",
            "I enhanced",
            "I refactored",
            "I fixed",
            "I resolved",
            "I debugged",
            "I troubleshot",
            "I wrote",
            "I documented",
            "I presented",
            "I communicated",
            "we implemented",
            "we developed",
            "we built",
            "we created",
            "our team",
            "my team",
            "the team",
        ]

        # Trigger phrases for delimiter-based extraction
        self.trigger_phrases = [
            "analyze this",
            "assess this",
            "evaluate this",
            "report on this",
            "report on",
            "analyze the following",
            "assess the following",
            "this activity",
            "my activity",
            "recent activity",
            "here's what",
            "here is what",
            "analyze",
            "assess",
            "evaluate",
        ]

    def _compile_patterns(self) -> None:
        """Compile regex patterns for content extraction"""

        # Delimiter pattern: trigger phrase followed by colon
        self.delimiter_pattern = re.compile(
            r"\b(analyze|assess|evaluate|report\s+on)\s+(this|the\s+following)\s*:", re.IGNORECASE
        )

        # Alternative delimiter: "this activity:" or "my activity:"
        self.activity_delimiter_pattern = re.compile(
            r"\b(this|my|recent)\s+activity\s*:", re.IGNORECASE
        )

        # Quote-wrapped content: content in quotes after trigger
        self.quote_pattern = re.compile(r'["\'](.+?)["\']', re.DOTALL)

        # Multi-line content after trigger
        self.multiline_pattern = re.compile(
            r"(?:analyze|assess|evaluate|report\s+on)\s+(?:this|the\s+following)\s*[:\-]?\s*(.+)",
            re.IGNORECASE | re.DOTALL,
        )

    async def extract_activity_content(
        self, user_message: str, trigger_patterns: list[str] | None = None
    ) -> ActivityContent | None:
        """
        Extract activity content from user message.

        Tries multiple extraction methods in priority order:
        1. Delimiter-based (highest confidence)
        2. Context-based (medium confidence)
        3. Explicit patterns (lower confidence)

        Args:
            user_message: User input text
            trigger_patterns: Optional additional trigger patterns

        Returns:
            ActivityContent if found, None otherwise
        """
        if not user_message or len(user_message.strip()) < 10:
            return None

        # Try extraction methods in priority order (most specific first)
        extractors = [
            self._extract_delimiter_content,  # Highest confidence: "analyze this: content"
            self._extract_quoted_content,  # Medium-high confidence: quoted content
            self._extract_context_content,  # Medium confidence: "I implemented"
        ]

        for extractor in extractors:
            try:
                result = extractor(user_message)
                if result and self._validate_content(result.raw_text):
                    # Clean the content
                    result.cleaned_text = self._clean_content(result.raw_text)

                    self.logger.info(
                        f"Extracted activity content via {result.extraction_method.value}",
                        extra={
                            "method": result.extraction_method.value,
                            "confidence": result.confidence,
                            "length": len(result.cleaned_text),
                            "trigger": result.trigger_phrase,
                        },
                    )
                    return result
            except Exception as e:
                self.logger.warning(f"Content extraction error in {extractor.__name__}: {e}")
                continue

        self.logger.debug("No activity content found in message")
        return None

    def _extract_delimiter_content(self, text: str) -> ActivityContent | None:
        """
        Extract content using delimiter pattern.

        Examples:
        - "Analyze this: I implemented microservices"
        - "Assess this activity: Led team of 5 engineers"
        """
        # Method 1: Standard delimiter pattern
        match = self.delimiter_pattern.search(text)
        if match:
            # Extract everything after the colon
            colon_pos = text.find(":", match.start())
            if colon_pos != -1:
                content = text[colon_pos + 1 :].strip()
                if content:
                    return ActivityContent(
                        raw_text=content,
                        extraction_method=ExtractionMethod.DELIMITER,
                        confidence=0.95,
                        trigger_phrase=match.group(0).strip(),
                    )

        # Method 2: Activity-specific delimiter
        match = self.activity_delimiter_pattern.search(text)
        if match:
            colon_pos = text.find(":", match.start())
            if colon_pos != -1:
                content = text[colon_pos + 1 :].strip()
                if content:
                    return ActivityContent(
                        raw_text=content,
                        extraction_method=ExtractionMethod.DELIMITER,
                        confidence=0.92,
                        trigger_phrase=match.group(0).strip(),
                    )

        return None

    def _extract_context_content(self, text: str) -> ActivityContent | None:
        """
        Extract content using activity indicators.

        Examples:
        - "I implemented a microservices platform with Kubernetes"
        - "Our team developed a new API gateway"
        """
        text_lower = text.lower()

        # Find the earliest activity indicator
        earliest_pos = len(text)
        matched_indicator = None

        for indicator in self.activity_indicators:
            pos = text_lower.find(indicator.lower())
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos
                matched_indicator = indicator

        if matched_indicator:
            # Extract from the indicator to the end
            content = text[earliest_pos:].strip()

            # Check if there's a sentence-ending punctuation
            # If so, extract just that sentence/paragraph
            sentences = re.split(r"[.!?]\s+", content)
            if sentences:
                # Use the first complete sentence or all content if no punctuation
                content = sentences[0] if len(sentences) > 1 else content

            return ActivityContent(
                raw_text=content,
                extraction_method=ExtractionMethod.CONTEXT,
                confidence=0.80,
                trigger_phrase=matched_indicator,
            )

        return None

    def _extract_quoted_content(self, text: str) -> ActivityContent | None:
        """
        Extract content from quotes.

        Examples:
        - 'Analyze "I led the implementation of OAuth2"'
        - "Report on 'Developed RESTful API with FastAPI'"
        """
        # Check if message contains trigger phrases
        has_trigger = any(phrase in text.lower() for phrase in self.trigger_phrases)

        if has_trigger:
            match = self.quote_pattern.search(text)
            if match:
                content = match.group(1).strip()
                if content:
                    return ActivityContent(
                        raw_text=content,
                        extraction_method=ExtractionMethod.EXPLICIT,
                        confidence=0.88,
                        trigger_phrase="quoted content",
                    )

        return None

    def _clean_content(self, text: str) -> str:
        """
        Clean extracted content.

        - Normalize whitespace
        - Remove extra punctuation
        - Trim to reasonable length
        """
        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", text.strip())

        # Remove trailing punctuation (keep internal punctuation)
        cleaned = re.sub(r"[,;:]+$", "", cleaned)

        # Truncate if too long (keep first 2000 characters)
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "..."
            self.logger.info("Content truncated to 2000 characters")

        return cleaned

    def _validate_content(self, text: str) -> bool:
        """
        Validate that extracted content is substantial.

        Args:
            text: Content to validate

        Returns:
            True if content is valid, False otherwise
        """
        if not text:
            return False

        # Check minimum length (at least 20 characters)
        if len(text.strip()) < 20:
            return False

        # Check that it's not just the trigger phrase
        trigger_words = ["analyze", "assess", "evaluate", "report", "this", "following"]
        words = text.lower().split()
        if len(words) <= 3 and all(word in trigger_words for word in words):
            return False

        # Check that it contains some meaningful words
        # (not just numbers, punctuation, etc.)
        alpha_chars = sum(1 for c in text if c.isalpha())
        if alpha_chars < 15:
            return False

        return True

    def extract_multiple_activities(self, user_message: str) -> list[ActivityContent]:
        """
        Extract multiple activities from a single message.

        Examples:
        - Numbered list: "1. Implemented X\n2. Developed Y"
        - Bullet points: "- Built A\n- Created B"

        Args:
            user_message: User input text

        Returns:
            List of ActivityContent objects
        """
        activities = []

        # Try to split by numbered list
        numbered_pattern = re.compile(r"^\s*\d+[\.\)]\s+(.+)$", re.MULTILINE)
        matches = numbered_pattern.findall(user_message)

        if matches and len(matches) > 1:
            for i, match in enumerate(matches):
                if self._validate_content(match):
                    activities.append(
                        ActivityContent(
                            raw_text=match.strip(),
                            extraction_method=ExtractionMethod.EXPLICIT,
                            confidence=0.85,
                            trigger_phrase=f"item {i + 1}",
                        )
                    )

            if activities:
                self.logger.info(f"Extracted {len(activities)} activities from numbered list")
                return activities

        # Try to split by bullet points
        bullet_pattern = re.compile(r"^\s*[-•*]\s+(.+)$", re.MULTILINE)
        matches = bullet_pattern.findall(user_message)

        if matches and len(matches) > 1:
            for i, match in enumerate(matches):
                if self._validate_content(match):
                    activities.append(
                        ActivityContent(
                            raw_text=match.strip(),
                            extraction_method=ExtractionMethod.EXPLICIT,
                            confidence=0.83,
                            trigger_phrase=f"bullet {i + 1}",
                        )
                    )

            if activities:
                self.logger.info(f"Extracted {len(activities)} activities from bullet list")
                return activities

        # If no multiple activities found, try single extraction
        single_result = None
        try:
            # Use synchronous call since we're already in a sync context
            import asyncio

            single_result = asyncio.run(self.extract_activity_content(user_message))
        except Exception as e:
            self.logger.warning(f"Error in single extraction: {e}")

        if single_result:
            return [single_result]

        return []


# Singleton instance
_content_extractor_instance: ContentExtractor | None = None


def get_content_extractor() -> ContentExtractor:
    """Get or create singleton content extractor instance"""
    global _content_extractor_instance

    if _content_extractor_instance is None:
        _content_extractor_instance = ContentExtractor()

    return _content_extractor_instance


def reset_content_extractor() -> None:
    """Reset singleton instance (primarily for testing)"""
    global _content_extractor_instance
    _content_extractor_instance = None

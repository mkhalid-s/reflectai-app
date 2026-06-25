"""
Intent Classification and Analysis for ReflectAI

Implements  Intent Classification and Analysis including:
- LLM-powered intent analysis using Analysis Agent for cost efficiency
- Intent types: activity_classification, competency_analysis, career_advice, help_request
- Context-aware intent detection using conversation history and user profile
- Intent confidence scoring with threshold-based routing

Provides intelligent intent detection for user requests and queries.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.types import IntentConfidence, IntentType
from src.shared import get_logger


@dataclass
class IntentPattern:
    """Pattern for intent recognition"""

    intent: IntentType
    keywords: list[str]
    patterns: list[str]
    context_indicators: list[str]
    exclusion_keywords: list[str]
    weight: float = 1.0
    requires_context: bool = False


class IntentClassificationResult(BaseModel):
    """Result of intent classification"""

    user_input: str = Field(..., description="Original user input")
    primary_intent: IntentType = Field(..., description="Primary detected intent")
    confidence: float = Field(..., description="Intent confidence (0-1)")
    confidence_level: IntentConfidence = Field(..., description="Confidence category")

    # Alternative intents
    alternative_intents: list[dict[str, Any]] = Field(
        default_factory=list, description="Other possible intents"
    )

    # Classification details
    method: str = Field(..., description="Classification method used")
    matched_patterns: list[str] = Field(default_factory=list, description="Patterns that matched")
    matched_keywords: list[str] = Field(default_factory=list, description="Keywords that matched")
    context_factors: list[str] = Field(
        default_factory=list, description="Context factors considered"
    )

    # LLM analysis (if used)
    llm_reasoning: str | None = Field(None, description="LLM reasoning")
    llm_confidence: float | None = Field(None, description="LLM confidence")

    # Routing suggestions
    needs_clarification: bool = Field(False, description="Whether clarification is needed")
    clarification_questions: list[str] = Field(
        default_factory=list, description="Questions to ask for clarification"
    )
    suggested_follow_up: list[str] = Field(
        default_factory=list, description="Suggested follow-up actions"
    )

    # Extracted information
    extracted_date_range: dict[str, Any] | None = Field(
        None, description="Extracted date range if present in user input"
    )
    extracted_content: dict[str, Any] | None = Field(
        None, description="Extracted inline content if present in user input"
    )

    # Processing metadata
    processing_time: float = Field(..., description="Time taken for classification")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IntentAnalyzer:
    """
    LLM-powered intent analyzer for user requests

    Provides intelligent intent detection with context awareness and confidence scoring.
    Uses both rule-based patterns and LLM analysis for accurate classification.
    """

    def __init__(self):
        self.logger = get_logger("classification.intent")

        # Intent patterns
        self._patterns = self._build_intent_patterns()

        # Performance tracking
        self._stats = {
            "total_classifications": 0,
            "high_confidence_results": 0,
            "clarification_requests": 0,
            "llm_classifications": 0,
            "average_confidence": 0.0,
            "intent_distribution": {intent.value: 0 for intent in IntentType},
        }

        # LLM prompt template
        self._llm_prompt = self._build_llm_prompt_template()

        # Context tracking
        self._conversation_context: dict[str, Any] = {}

    async def analyze_intent(
        self,
        user_input: str,
        user_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        agent_context: Any | None = None,
        confidence_threshold: float = 0.7,
    ) -> IntentClassificationResult:
        """
        Analyze user intent from input

        Args:
            user_input: User's input text
            user_context: User profile and context information
            conversation_history: Recent conversation messages
            agent_context: Agent context for LLM access
            confidence_threshold: Threshold for direct routing

        Returns:
            IntentClassificationResult with classification details
        """
        start_time = datetime.now(UTC)

        try:
            # Step 1: Pre-process input
            processed_input = self._preprocess_input(user_input)

            # Step 2: Try pattern-based classification
            pattern_result = await self._classify_with_patterns(
                processed_input, user_context or {}, conversation_history or []
            )

            # Step 3: If pattern classification succeeded, use it
            # (Threshold already checked in _classify_with_patterns at line 281)
            if pattern_result:
                # Extract date range if present (for report requests)
                await self._extract_date_range_info(pattern_result, user_input, user_context)

                # Extract inline content if present (for inline reports)
                await self._extract_content_info(pattern_result, user_input)

                processing_time = (datetime.now(UTC) - start_time).total_seconds()
                pattern_result.processing_time = processing_time
                self._update_stats(
                    pattern_result.primary_intent, pattern_result.confidence, "pattern"
                )
                return pattern_result

            # Step 4: Use LLM for complex intent analysis
            if agent_context:
                llm_result = await self._classify_with_llm(
                    user_input,
                    processed_input,
                    user_context or {},
                    conversation_history or [],
                    agent_context,
                    pattern_result,
                )

                if llm_result:
                    # Extract date range if present (for report requests)
                    await self._extract_date_range_info(llm_result, user_input, user_context)

                    # Extract inline content if present (for inline reports)
                    await self._extract_content_info(llm_result, user_input)

                    processing_time = (datetime.now(UTC) - start_time).total_seconds()
                    llm_result.processing_time = processing_time
                    self._update_stats(llm_result.primary_intent, llm_result.confidence, "llm")
                    return llm_result

            # Step 5: Fallback classification
            fallback_result = self._create_fallback_classification(user_input, pattern_result)

            # Extract date range if present (for report requests)
            await self._extract_date_range_info(fallback_result, user_input, user_context)

            # Extract inline content if present (for inline reports)
            await self._extract_content_info(fallback_result, user_input)

            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            fallback_result.processing_time = processing_time

            self._update_stats(
                fallback_result.primary_intent, fallback_result.confidence, "fallback"
            )
            return fallback_result

        except Exception as e:
            self.logger.error(f"Intent analysis failed: {str(e)}")

            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            return IntentClassificationResult(
                user_input=user_input,
                primary_intent=IntentType.UNKNOWN,
                confidence=0.1,
                confidence_level=IntentConfidence.VERY_LOW,
                method="error_fallback",
                processing_time=processing_time,
                needs_clarification=True,
                clarification_questions=[
                    "I'm sorry, I didn't understand. Could you please rephrase your request?"
                ],
            )

    def _preprocess_input(self, user_input: str) -> str:
        """Preprocess user input for better classification"""

        # Normalize whitespace
        processed = re.sub(r"\s+", " ", user_input.strip())

        # Convert to lowercase for pattern matching
        processed = processed.lower()

        # Remove common filler words
        filler_words = ["um", "uh", "like", "you know", "basically", "actually"]
        for filler in filler_words:
            processed = re.sub(rf"\b{filler}\b", "", processed)

        # Clean up extra spaces
        processed = re.sub(r"\s+", " ", processed).strip()

        return processed

    async def _classify_with_patterns(
        self,
        processed_input: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, str]],
    ) -> IntentClassificationResult | None:
        """Classify using pattern-based approach"""

        scores = {}
        matched_details = {}

        for pattern in self._patterns:
            score = self._calculate_pattern_score(
                pattern, processed_input, user_context, conversation_history
            )

            if score > 0:
                scores[pattern.intent] = max(scores.get(pattern.intent, 0), score)

                if pattern.intent not in matched_details:
                    matched_details[pattern.intent] = {
                        "keywords": [],
                        "patterns": [],
                        "context": [],
                    }

                # Track what matched
                for keyword in pattern.keywords:
                    if keyword in processed_input:
                        matched_details[pattern.intent]["keywords"].append(keyword)

                for regex_pattern in pattern.patterns:
                    if re.search(regex_pattern, processed_input, re.IGNORECASE):
                        matched_details[pattern.intent]["patterns"].append(regex_pattern)

        if not scores:
            return None

        # Get best match
        best_intent = max(scores.keys(), key=lambda x: scores[x])
        best_score = scores[best_intent]

        # Lower threshold to accept simple greetings/help requests
        # Pattern scoring gives ~0.16 for single keyword/pattern matches
        if best_score < 0.15:
            return None

        # Get alternative intents
        alternatives = []
        for intent, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:3]:
            alternatives.append({"intent": intent.value, "confidence": score})

        # Determine if clarification is needed
        needs_clarification = best_score < 0.7
        clarification_questions = self._generate_clarification_questions(best_intent, best_score)

        return IntentClassificationResult(
            user_input=processed_input,
            primary_intent=best_intent,
            confidence=best_score,
            confidence_level=self._get_confidence_level(best_score),
            alternative_intents=alternatives,
            method="pattern_based",
            matched_patterns=matched_details[best_intent]["patterns"],
            matched_keywords=matched_details[best_intent]["keywords"],
            context_factors=matched_details[best_intent]["context"],
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions,
            suggested_follow_up=self._get_suggested_follow_up(best_intent),
            processing_time=0.0,
        )

    async def _classify_with_llm(
        self,
        original_input: str,
        processed_input: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, str]],
        agent_context: Any,
        pattern_result: IntentClassificationResult | None = None,
    ) -> IntentClassificationResult | None:
        """Classify using LLM analysis"""

        try:
            # Prepare context for LLM
            context_info = self._prepare_llm_context(
                original_input, user_context, conversation_history, pattern_result
            )

            # Generate LLM prompt
            prompt = self._llm_prompt.format(**context_info)

            # Call LLM via agent context
            if hasattr(agent_context, "llm_provider"):
                response = await agent_context.llm_provider.generate(
                    prompt=prompt, max_tokens=400, temperature=0.2
                )

                # Parse LLM response
                llm_result = self._parse_llm_response(response.content, original_input)

                if llm_result:
                    # Enhance with pattern insights if available
                    if pattern_result:
                        llm_result = self._enhance_with_pattern_insights(llm_result, pattern_result)

                    return llm_result

            return None

        except Exception as e:
            self.logger.warning(f"LLM intent classification failed: {str(e)}")
            return None

    def _calculate_pattern_score(
        self,
        pattern: IntentPattern,
        processed_input: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, str]],
    ) -> float:
        """Calculate how well a pattern matches the input"""

        score = 0.0

        # Keyword matching
        keyword_matches = sum(1 for keyword in pattern.keywords if keyword in processed_input)
        if keyword_matches > 0:
            keyword_score = min(keyword_matches / len(pattern.keywords), 1.0) * 0.6
            score += keyword_score

        # Pattern matching
        pattern_matches = sum(
            1
            for regex_pattern in pattern.patterns
            if re.search(regex_pattern, processed_input, re.IGNORECASE)
        )
        if pattern_matches > 0:
            pattern_score = min(pattern_matches / len(pattern.patterns), 1.0) * 0.3
            score += pattern_score

        # Context indicators
        if pattern.context_indicators:
            context_matches = 0

            # Check user context
            user_role = user_context.get("role", "").lower()
            user_department = user_context.get("department", "").lower()

            for indicator in pattern.context_indicators:
                if (
                    indicator in user_role
                    or indicator in user_department
                    or any(
                        indicator in msg.get("content", "").lower()
                        for msg in conversation_history[-3:]
                    )
                ):  # Check recent history
                    context_matches += 1

            if context_matches > 0:
                context_score = min(context_matches / len(pattern.context_indicators), 1.0) * 0.1
                score += context_score

        # Exclusion keywords (negative scoring)
        exclusion_matches = sum(
            1 for keyword in pattern.exclusion_keywords if keyword in processed_input
        )
        if exclusion_matches > 0:
            score -= exclusion_matches * 0.2

        # Apply pattern weight
        score *= pattern.weight

        return max(0.0, min(score, 1.0))

    def _get_confidence_level(self, confidence: float) -> IntentConfidence:
        """Get confidence level enum from numeric confidence"""
        if confidence >= 0.7:
            return IntentConfidence.HIGH
        elif confidence >= 0.5:
            return IntentConfidence.MEDIUM
        elif confidence >= 0.3:
            return IntentConfidence.LOW
        else:
            return IntentConfidence.VERY_LOW

    def _generate_clarification_questions(self, intent: IntentType, confidence: float) -> list[str]:
        """Generate clarification questions based on intent and confidence"""

        if confidence >= 0.7:
            return []

        questions = {
            IntentType.ACTIVITY_CLASSIFICATION: [
                "Could you provide more details about the activity you'd like me to classify?",
                "What specific work did you do that you'd like categorized?",
            ],
            IntentType.COMPETENCY_ANALYSIS: [
                "Which competency area would you like me to analyze?",
                "Are you looking for an overall competency assessment or analysis of a specific skill?",
            ],
            IntentType.CAREER_ADVICE: [
                "What specific aspect of your career would you like advice on?",
                "Are you looking for guidance on skills, roles, or career progression?",
            ],
            IntentType.GOAL_MANAGEMENT: [
                "Would you like to create, update, or review your goals?",
                "Which specific goal would you like to work on?",
            ],
            IntentType.REPORT_REQUEST: [
                "What type of report would you like me to generate?",
                "Should this be a competency report, career progress report, or something else?",
            ],
        }

        return questions.get(
            intent,
            [
                "Could you please provide more details about what you're looking for?",
                "I want to make sure I understand correctly - could you clarify your request?",
            ],
        )[:2]

    def _get_suggested_follow_up(self, intent: IntentType) -> list[str]:
        """Get suggested follow-up actions for an intent"""

        follow_ups = {
            IntentType.ACTIVITY_CLASSIFICATION: [
                "After classification, I can suggest related competency development opportunities",
                "I can also analyze how this activity impacts your overall competency progression",
            ],
            IntentType.COMPETENCY_ANALYSIS: [
                "I can provide specific recommendations for improving identified competency gaps",
                "Would you like me to create learning goals based on this analysis?",
            ],
            IntentType.CAREER_ADVICE: [
                "I can help create specific goals and action plans based on this advice",
                "Would you like me to find relevant learning resources or opportunities?",
            ],
            IntentType.GOAL_MANAGEMENT: [
                "I can track progress and provide regular updates on your goals",
                "Would you like me to suggest related learning resources or milestones?",
            ],
        }

        return follow_ups.get(intent, [])

    def _build_intent_patterns(self) -> list[IntentPattern]:
        """Build comprehensive intent recognition patterns"""

        patterns = []

        # Activity Classification Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.ACTIVITY_CLASSIFICATION,
                keywords=[
                    "classify",
                    "categorize",
                    "what type",
                    "activity type",
                    "classify activity",
                    "what category",
                    "type of work",
                    "classify this",
                    "categorize this",
                ],
                patterns=[
                    r"\b(classify|categorize)\s+\w*activity\w*",
                    r"\bwhat\s+(type|category|kind)\s+of\s+\w*(work|activity|task)\w*",
                    r"\b(is\s+this|classify\s+this|categorize\s+this)\b",
                    r"\bactivity\s+(classification|category|type)\b",
                ],
                context_indicators=["work", "task", "project", "coding", "development"],
                exclusion_keywords=["meeting", "general"],
                weight=1.2,
            )
        )

        # Competency Analysis Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.COMPETENCY_ANALYSIS,
                keywords=[
                    "competency",
                    "competencies",
                    "skills",
                    "skill level",
                    "assess",
                    "assessment",
                    "analyze skills",
                    "competency analysis",
                    "skill assessment",
                    "evaluate",
                    "how good",
                    "proficiency",
                    "expertise",
                ],
                patterns=[
                    r"\b(competency|competencies|skill)\s+(analysis|assessment|evaluation)\b",
                    r"\b(analyze|assess|evaluate)\s+\w*(competency|competencies|skill)\w*",
                    r"\bhow\s+(good|proficient|skilled)\s+am\s+i\b",
                    r"\b(skill\s+level|competency\s+level|proficiency\s+level)\b",
                ],
                context_indicators=["technical", "leadership", "communication", "development"],
                exclusion_keywords=["classify", "categorize"],
                weight=1.1,
            )
        )

        # Career Advice Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.CAREER_ADVICE,
                keywords=[
                    "career",
                    "advice",
                    "guidance",
                    "recommendation",
                    "next step",
                    "career path",
                    "promotion",
                    "advancement",
                    "career development",
                    "career progression",
                    "what should i",
                    "how to advance",
                    "career goals",
                ],
                patterns=[
                    r"\bcareer\s+(advice|guidance|path|development|progression)\b",
                    r"\bhow\s+(to|can\s+i)\s+(advance|progress|grow|develop)\b",
                    r"\bwhat\s+should\s+i\s+(do|focus|learn|work)\b",
                    r"\b(next\s+step|promotion|advancement)\b",
                ],
                context_indicators=["senior", "junior", "lead", "manager", "goal"],
                exclusion_keywords=["classify", "assess"],
                weight=1.0,
            )
        )

        # Help Request Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.HELP_REQUEST,
                keywords=[
                    "help",
                    "how do i",
                    "how to",
                    "can you",
                    "please help",
                    "i need",
                    "confused",
                    "don't understand",
                    "not sure",
                    "question",
                ],
                patterns=[
                    r"\b(help|assist|support)\b",
                    r"\bhow\s+(do\s+i|to|can\s+i)\b",
                    r"\b(can\s+you|could\s+you|would\s+you)\b",
                    r"\b(don't\s+understand|not\s+sure|confused|question)\b",
                ],
                context_indicators=["new", "first time", "beginner"],
                exclusion_keywords=[],
                weight=1.1,  # Boost help request confidence
            )
        )

        # Goal Management Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.GOAL_MANAGEMENT,
                keywords=[
                    "goal",
                    "goals",
                    "objective",
                    "objectives",
                    "target",
                    "milestone",
                    "create goal",
                    "set goal",
                    "update goal",
                    "goal progress",
                    "track goal",
                ],
                patterns=[
                    r"\bgoal\s+(management|tracking|progress|update|creation)\b",
                    r"\b(create|set|update|track|manage)\s+\w*goal\w*",
                    r"\b(objective|objectives|target|milestone)\b",
                    r"\bmy\s+goals?\b",
                ],
                context_indicators=["development", "learning", "career", "improvement"],
                exclusion_keywords=["advice", "classify"],
                weight=1.0,
            )
        )

        # Report Request Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.REPORT_REQUEST,
                keywords=[
                    "report",
                    "generate report",
                    "create report",
                    "summary",
                    "analysis report",
                    "competency report",
                    "progress report",
                    "dashboard",
                    "overview",
                ],
                patterns=[
                    r"\b(generate|create|produce)\s+\w*report\w*",
                    r"\breport\s+(on|about|for)\b",
                    r"\b(summary|overview|analysis)\s+report\b",
                    r"\b(competency|progress|performance)\s+report\b",
                ],
                context_indicators=["monthly", "quarterly", "annual", "manager"],
                exclusion_keywords=["help", "how to"],
                weight=1.0,
            )
        )

        # Resource Discovery Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.RESOURCE_DISCOVERY,
                keywords=[
                    "resource",
                    "resources",
                    "learn",
                    "learning",
                    "course",
                    "training",
                    "book",
                    "tutorial",
                    "certification",
                    "find resources",
                    "recommend resources",
                ],
                patterns=[
                    r"\b(find|discover|recommend)\s+\w*resource\w*",
                    r"\b(learning|training|education)\s+(resource|material)\w*",
                    r"\b(course|tutorial|book|certification)\s+recommendation\w*",
                    r"\bwhere\s+(can\s+i|to)\s+(learn|study|train)\b",
                ],
                context_indicators=["skill", "development", "improvement", "learning"],
                exclusion_keywords=["classify", "assess"],
                weight=1.0,
            )
        )

        # Status Inquiry Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.STATUS_INQUIRY,
                keywords=[
                    "status",
                    "progress",
                    "how am i doing",
                    "where am i",
                    "current state",
                    "my progress",
                    "check status",
                    "update me",
                ],
                patterns=[
                    r"\b(status|progress|state)\s+(check|update|inquiry)\b",
                    r"\bhow\s+am\s+i\s+(doing|progressing)\b",
                    r"\bwhere\s+am\s+i\s+(at|with|in\s+my)\b",
                    r"\b(current|my)\s+(status|progress|state)\b",
                ],
                context_indicators=["goal", "development", "competency", "career"],
                exclusion_keywords=["help", "advice"],
                weight=0.9,
            )
        )

        # General Chat Intent
        patterns.append(
            IntentPattern(
                intent=IntentType.GENERAL_CHAT,
                keywords=[
                    "hello",
                    "hi",
                    "thanks",
                    "thank you",
                    "good morning",
                    "good afternoon",
                    "how are you",
                    "what's up",
                    "chat",
                    "conversation",
                ],
                patterns=[
                    r"\b(hello|hi|hey|greetings)\b",
                    r"\b(thanks|thank\s+you|good\s+(morning|afternoon|evening))\b",
                    r"\bhow\s+are\s+you\b",
                    r"\b(chat|conversation|talk)\b",
                ],
                context_indicators=[],
                exclusion_keywords=["help", "advice", "goal", "competency"],
                weight=1.2,  # Boost greeting confidence to avoid over-clarification
            )
        )

        return patterns

    def _build_llm_prompt_template(self) -> str:
        """Build LLM prompt template for intent classification"""

        return """
You are an expert at understanding user intents in a career development context. Analyze the following user input and classify their intent.

User Input: {user_input}

User Context:
- Role: {user_role}
- Department: {user_department}
- Recent Activity: {recent_activity}

Conversation Context:
{conversation_context}

{pattern_hints}

Available Intent Types:
- activity_classification: User wants to classify a work activity
- competency_analysis: User wants competency/skill assessment
- career_advice: User seeks career guidance or recommendations
- help_request: User needs help or has questions
- goal_management: User wants to create, update, or track goals
- report_request: User wants to generate reports or summaries
- resource_discovery: User wants to find learning resources
- status_inquiry: User wants to check their progress/status
- general_chat: Casual conversation or greetings
- unknown: Intent is unclear or doesn't fit above categories

Analyze the user's input and provide:
1. Primary intent (from list above)
2. Confidence level (0.0-1.0)
3. Brief reasoning
4. Whether clarification is needed (yes/no)

Focus on what the user actually wants to accomplish.

Intent Analysis:
"""

    def _prepare_llm_context(
        self,
        user_input: str,
        user_context: dict[str, Any],
        conversation_history: list[dict[str, str]],
        pattern_result: IntentClassificationResult | None = None,
    ) -> dict[str, str]:
        """Prepare context for LLM prompt"""

        # User context
        user_role = user_context.get("role", "Unknown")
        user_department = user_context.get("department", "Unknown")
        recent_activity = user_context.get("recent_activity", "None available")

        # Conversation context
        if conversation_history:
            context_messages = []
            for msg in conversation_history[-3:]:  # Last 3 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:100]  # Truncate long messages
                context_messages.append(f"{role}: {content}")
            conversation_context = "\n".join(context_messages)
        else:
            conversation_context = "No previous conversation history"

        # Pattern hints
        pattern_hints = ""
        if pattern_result:
            pattern_hints = f"""
Pattern-based analysis suggests:
- Intent: {pattern_result.primary_intent.value}
- Confidence: {pattern_result.confidence:.2f}
- Matched Keywords: {", ".join(pattern_result.matched_keywords)}
Consider this analysis but make your own determination.
"""

        return {
            "user_input": user_input,
            "user_role": user_role,
            "user_department": user_department,
            "recent_activity": recent_activity,
            "conversation_context": conversation_context,
            "pattern_hints": pattern_hints,
        }

    def _parse_llm_response(
        self, response_content: str, user_input: str
    ) -> IntentClassificationResult | None:
        """Parse LLM response into structured result"""

        try:
            # Extract intent
            intent = IntentType.UNKNOWN
            for intent_type in IntentType:
                if intent_type.value.lower() in response_content.lower():
                    intent = intent_type
                    break

            # Extract confidence
            confidence = 0.6  # Default
            confidence_patterns = [
                r"confidence[:\s]*(\d+\.?\d*)%?",
                r"confident[:\s]*(\d+\.?\d*)%?",
                r"certainty[:\s]*(\d+\.?\d*)%?",
            ]

            for pattern in confidence_patterns:
                match = re.search(pattern, response_content, re.IGNORECASE)
                if match:
                    conf_value = float(match.group(1))
                    confidence = conf_value / 100 if conf_value > 1 else conf_value
                    break

            # Extract clarification need
            needs_clarification = any(
                phrase in response_content.lower()
                for phrase in [
                    "clarification needed",
                    "needs clarification",
                    "unclear",
                    "ambiguous",
                ]
            )

            # Extract reasoning
            reasoning = (
                response_content[:300] + "..." if len(response_content) > 300 else response_content
            )

            return IntentClassificationResult(
                user_input=user_input,
                primary_intent=intent,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                method="llm_assisted",
                llm_reasoning=reasoning,
                llm_confidence=confidence,
                needs_clarification=needs_clarification,
                clarification_questions=self._generate_clarification_questions(intent, confidence),
                suggested_follow_up=self._get_suggested_follow_up(intent),
                processing_time=0.0,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse LLM response: {str(e)}")
            return None

    def _enhance_with_pattern_insights(
        self, llm_result: IntentClassificationResult, pattern_result: IntentClassificationResult
    ) -> IntentClassificationResult:
        """Enhance LLM result with pattern-based insights"""

        # Combine matched keywords and patterns
        llm_result.matched_keywords.extend(pattern_result.matched_keywords)
        llm_result.matched_patterns.extend(pattern_result.matched_patterns)

        # Add pattern alternatives to LLM alternatives
        pattern_alternatives = [
            {
                "intent": pattern_result.primary_intent.value,
                "confidence": pattern_result.confidence,
                "method": "pattern_based",
            }
        ]
        pattern_alternatives.extend(pattern_result.alternative_intents)
        llm_result.alternative_intents.extend(pattern_alternatives)

        return llm_result

    def _create_fallback_classification(
        self, user_input: str, pattern_result: IntentClassificationResult | None = None
    ) -> IntentClassificationResult:
        """Create fallback classification when other methods fail"""

        # Use pattern result if available
        if pattern_result:
            return IntentClassificationResult(
                user_input=user_input,
                primary_intent=pattern_result.primary_intent,
                confidence=max(pattern_result.confidence * 0.6, 0.2),
                confidence_level=IntentConfidence.LOW,
                alternative_intents=pattern_result.alternative_intents,
                method="pattern_fallback",
                matched_patterns=pattern_result.matched_patterns,
                matched_keywords=pattern_result.matched_keywords,
                needs_clarification=True,
                clarification_questions=[
                    "I'm not completely sure what you're looking for. Could you provide more details?",
                    "To better assist you, could you clarify what specific help you need?",
                ],
                processing_time=0.0,
            )
        else:
            return IntentClassificationResult(
                user_input=user_input,
                primary_intent=IntentType.UNKNOWN,
                confidence=0.2,
                confidence_level=IntentConfidence.VERY_LOW,
                method="generic_fallback",
                needs_clarification=True,
                clarification_questions=[
                    "I didn't quite understand your request. Could you please rephrase it?",
                    "What specific task would you like me to help you with?",
                ],
                suggested_follow_up=[
                    "I can help with activity classification, competency analysis, career advice, and more",
                    "Try asking something like 'analyze my competencies' or 'classify this activity'",
                ],
                processing_time=0.0,
            )

    async def _extract_date_range_info(
        self,
        result: IntentClassificationResult,
        user_input: str,
        user_context: dict[str, Any] | None,
    ) -> None:
        """
        Extract date range information from user input if present.

        Updates the result object in-place with extracted date range.

        Args:
            result: Intent classification result to update
            user_input: Original user input
            user_context: User context for extraction
        """
        try:
            # Only extract for report-related intents
            if result.primary_intent not in [
                IntentType.REPORT_REQUEST,
                IntentType.COMPETENCY_ANALYSIS,
                IntentType.STATUS_INQUIRY,
            ]:
                return

            from src.core.classification.date_range_extractor import get_date_range_extractor

            date_extractor = get_date_range_extractor()
            date_range = await date_extractor.extract_date_range(user_input, user_context)

            if date_range:
                result.extracted_date_range = date_range.to_dict()
                self.logger.info(
                    f"Extracted date range: {date_range.original_text}",
                    extra={
                        "start": date_range.start_date.isoformat(),
                        "end": date_range.end_date.isoformat(),
                        "days": date_range.days_span,
                        "confidence": date_range.confidence,
                    },
                )
        except Exception as e:
            self.logger.warning(f"Date range extraction failed: {e}")

    async def _extract_content_info(
        self, result: IntentClassificationResult, user_input: str
    ) -> None:
        """
        Extract inline content from user input if present.

        Updates the result object in-place with extracted content.

        Args:
            result: Intent classification result to update
            user_input: Original user input
        """
        try:
            # Only extract for report-related intents
            if result.primary_intent not in [
                IntentType.REPORT_REQUEST,
                IntentType.ACTIVITY_CLASSIFICATION,
                IntentType.COMPETENCY_ANALYSIS,
            ]:
                return

            from src.core.classification.content_extractor import get_content_extractor

            content_extractor = get_content_extractor()
            activity_content = await content_extractor.extract_activity_content(user_input)

            if activity_content:
                result.extracted_content = activity_content.to_dict()
                self.logger.info(
                    f"Extracted inline content: {activity_content.extraction_method.value}",
                    extra={
                        "method": activity_content.extraction_method.value,
                        "confidence": activity_content.confidence,
                        "length": len(activity_content.cleaned_text or activity_content.raw_text),
                        "trigger": activity_content.trigger_phrase,
                    },
                )
        except Exception as e:
            self.logger.warning(f"Content extraction failed: {e}")

    def _update_stats(self, intent: IntentType, confidence: float, method: str):
        """Update classification statistics"""

        self._stats["total_classifications"] += 1
        self._stats["intent_distribution"][intent.value] += 1

        if confidence >= 0.7:
            self._stats["high_confidence_results"] += 1

        if confidence < 0.5:
            self._stats["clarification_requests"] += 1

        if method in ["llm_assisted", "llm"]:
            self._stats["llm_classifications"] += 1

        # Update average confidence
        total = self._stats["total_classifications"]
        current_avg = self._stats["average_confidence"]
        self._stats["average_confidence"] = ((current_avg * (total - 1)) + confidence) / total

    def get_intent_stats(self) -> dict[str, Any]:
        """Get intent analysis statistics"""
        return self._stats.copy()

    def get_supported_intents(self) -> list[str]:
        """Get list of supported intent types"""
        return [intent.value for intent in IntentType]

    def update_conversation_context(self, user_id: str, context: dict[str, Any]):
        """Update conversation context for a user"""
        self._conversation_context[user_id] = context

    def get_conversation_context(self, user_id: str) -> dict[str, Any]:
        """Get conversation context for a user"""
        return self._conversation_context.get(user_id, {})


# Global analyzer instance
_global_analyzer: IntentAnalyzer | None = None


def get_intent_analyzer() -> IntentAnalyzer:
    """Get global intent analyzer instance"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = IntentAnalyzer()
    return _global_analyzer

"""
Activity Classification Engine for ReflectAI

Implements  Activity Classification Engine including:
- Rule-based classifier with pattern matching and keyword detection
- LLM-assisted classification via Analysis Agent for complex cases
- Fallback strategy with confidence scoring
- Activity type taxonomy with competency category mapping

Provides robust activity classification with high accuracy and fallback mechanisms.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.storage.models.activity_data import ActivityType
from src.core.storage.models.competency_data import CompetencyCategory
from src.shared import get_logger


class ClassificationMethod(Enum):
    """Classification method used"""

    RULE_BASED = "rule_based"
    LLM_ASSISTED = "llm_assisted"
    HYBRID = "hybrid"
    FALLBACK = "fallback"


class ClassificationConfidence(Enum):
    """Classification confidence levels"""

    HIGH = "high"  # >0.8
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"  # 0.3-0.5
    VERY_LOW = "very_low"  # <0.3


@dataclass
class ClassificationRule:
    """Individual classification rule"""

    name: str
    activity_type: ActivityType
    competency_categories: list[CompetencyCategory]
    keywords: list[str]
    patterns: list[str]
    exclusion_keywords: list[str]
    weight: float = 1.0
    context_boost: dict[str, float] = None

    def __post_init__(self):
        if self.context_boost is None:
            self.context_boost = {}


class ActivityClassificationResult(BaseModel):
    """Result of activity classification"""

    activity_description: str = Field(..., description="Original activity description")
    primary_classification: ActivityType = Field(..., description="Primary activity type")
    competency_categories: list[CompetencyCategory] = Field(
        ..., description="Related competency categories"
    )

    # Classification metadata
    confidence: float = Field(..., description="Classification confidence (0-1)")
    confidence_level: ClassificationConfidence = Field(..., description="Confidence category")
    method: ClassificationMethod = Field(..., description="Classification method used")

    # Alternative classifications
    alternative_classifications: list[dict[str, Any]] = Field(
        default_factory=list, description="Other possible classifications"
    )

    # Rule-based details
    matched_rules: list[str] = Field(default_factory=list, description="Rules that matched")
    keyword_matches: dict[str, list[str]] = Field(
        default_factory=dict, description="Keywords that matched"
    )
    pattern_matches: list[str] = Field(default_factory=list, description="Patterns that matched")

    # LLM details (if used)
    llm_reasoning: str | None = Field(None, description="LLM reasoning for classification")
    llm_confidence: float | None = Field(None, description="LLM confidence score")

    # Processing metadata
    processing_time: float = Field(..., description="Time taken for classification")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_confidence_level(self) -> ClassificationConfidence:
        """Get confidence level enum from numeric confidence"""
        if self.confidence >= 0.8:
            return ClassificationConfidence.HIGH
        elif self.confidence >= 0.5:
            return ClassificationConfidence.MEDIUM
        elif self.confidence >= 0.3:
            return ClassificationConfidence.LOW
        else:
            return ClassificationConfidence.VERY_LOW


class ActivityClassificationEngine:
    """
    Advanced activity classification engine

    Provides rule-based classification with LLM fallback for complex cases.
    Uses sophisticated pattern matching and context awareness.
    """

    def __init__(self, enable_llm_fallback: bool = True):
        self.logger = get_logger("classification.activity")
        self.enable_llm_fallback = enable_llm_fallback

        # Classification rules
        self._rules = self._build_classification_rules()

        # Performance tracking
        self._stats = {
            "total_classifications": 0,
            "rule_based_success": 0,
            "llm_fallback_used": 0,
            "high_confidence_results": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0,
        }

        # LLM prompt template
        self._llm_prompt = self._build_llm_prompt_template()

    async def classify_activity(
        self,
        activity_description: str,
        user_context: dict[str, Any] | None = None,
        agent_context: Any | None = None,
        confidence_threshold: float = 0.3,
    ) -> ActivityClassificationResult:
        """
        Classify an activity description

        Args:
            activity_description: Description of the activity
            user_context: Optional user context for better classification
            agent_context: Agent context for LLM access
            confidence_threshold: Minimum confidence for rule-based classification

        Returns:
            ActivityClassificationResult with classification details
        """
        start_time = datetime.now(UTC)

        try:
            # Step 1: Try rule-based classification
            rule_result = await self._classify_with_rules(activity_description, user_context or {})

            # Check if rule-based classification meets threshold
            if rule_result and rule_result.confidence >= confidence_threshold:
                # Rule-based classification succeeded
                self._update_stats(
                    "rule_based",
                    rule_result.confidence,
                    (datetime.now(UTC) - start_time).total_seconds(),
                )
                return rule_result

            # Step 2: Try LLM-assisted classification if enabled
            if self.enable_llm_fallback and agent_context:
                llm_result = await self._classify_with_llm(
                    activity_description,
                    user_context or {},
                    agent_context,
                    rule_result,  # Pass rule result for hybrid approach
                )

                if llm_result:
                    self._update_stats(
                        "llm_fallback",
                        llm_result.confidence,
                        (datetime.now(UTC) - start_time).total_seconds(),
                    )
                    return llm_result

            # Step 3: Fallback classification
            fallback_result = self._create_fallback_classification(
                activity_description, rule_result
            )

            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            fallback_result.processing_time = processing_time

            self._update_stats("fallback", fallback_result.confidence, processing_time)
            return fallback_result

        except Exception as e:
            self.logger.error(f"Activity classification failed: {str(e)}")

            # Create error fallback
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            return ActivityClassificationResult(
                activity_description=activity_description,
                primary_classification=ActivityType.OTHER,
                competency_categories=[CompetencyCategory.TECHNICAL_SKILLS],
                confidence=0.1,
                confidence_level=ClassificationConfidence.VERY_LOW,
                method=ClassificationMethod.FALLBACK,
                processing_time=processing_time,
            )

    async def _classify_with_rules(
        self, description: str, user_context: dict[str, Any]
    ) -> ActivityClassificationResult | None:
        """Classify using rule-based approach"""

        normalized_desc = description.lower().strip()
        best_matches = []

        for rule in self._rules:
            match_score = self._calculate_rule_match_score(rule, normalized_desc, user_context)

            if match_score > 0:
                best_matches.append(
                    {
                        "rule": rule,
                        "score": match_score,
                        "keyword_matches": self._find_keyword_matches(
                            rule.keywords, normalized_desc
                        ),
                        "pattern_matches": self._find_pattern_matches(
                            rule.patterns, normalized_desc
                        ),
                    }
                )

        if not best_matches:
            return None

        # Sort by score
        best_matches.sort(key=lambda x: x["score"], reverse=True)
        best_match = best_matches[0]

        if best_match["score"] < 0.3:
            return None

        # Build result
        rule = best_match["rule"]
        confidence = min(best_match["score"], 1.0)

        # Get alternative classifications
        alternatives = []
        for match in best_matches[1:3]:  # Top 2 alternatives
            alternatives.append(
                {
                    "activity_type": match["rule"].activity_type.value,
                    "confidence": match["score"],
                    "competency_categories": [
                        cc.value for cc in match["rule"].competency_categories
                    ],
                }
            )

        return ActivityClassificationResult(
            activity_description=description,
            primary_classification=rule.activity_type,
            competency_categories=rule.competency_categories,
            confidence=confidence,
            confidence_level=ClassificationConfidence.HIGH
            if confidence >= 0.8
            else ClassificationConfidence.MEDIUM
            if confidence >= 0.5
            else ClassificationConfidence.LOW,
            method=ClassificationMethod.RULE_BASED,
            alternative_classifications=alternatives,
            matched_rules=[rule.name],
            keyword_matches={rule.name: best_match["keyword_matches"]},
            pattern_matches=best_match["pattern_matches"],
            processing_time=0.0,  # Will be set by caller
        )

    async def _classify_with_llm(
        self,
        description: str,
        user_context: dict[str, Any],
        agent_context: Any,
        rule_result: ActivityClassificationResult | None = None,
    ) -> ActivityClassificationResult | None:
        """Classify using LLM assistance"""

        try:
            # Prepare context for LLM
            context_info = self._prepare_llm_context(description, user_context, rule_result)

            # Generate LLM prompt
            prompt = self._llm_prompt.format(**context_info)

            # Call LLM via agent context (simplified)
            if hasattr(agent_context, "llm_provider"):
                response = await agent_context.llm_provider.generate(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.2,  # Lower temperature for more consistent classification
                )

                # Parse LLM response
                llm_classification = self._parse_llm_response(response.content, description)

                if llm_classification:
                    # Combine with rule-based insights if available
                    if rule_result:
                        return self._create_hybrid_classification(
                            description, rule_result, llm_classification
                        )
                    else:
                        return llm_classification

            return None

        except Exception as e:
            self.logger.warning(f"LLM classification failed: {str(e)}")
            return None

    def _calculate_rule_match_score(
        self, rule: ClassificationRule, description: str, user_context: dict[str, Any]
    ) -> float:
        """Calculate how well a rule matches the description"""

        score = 0.0

        # Keyword matching
        keyword_matches = sum(1 for keyword in rule.keywords if keyword in description)
        if keyword_matches > 0:
            keyword_score = (keyword_matches / len(rule.keywords)) * 0.6
            score += keyword_score

        # Pattern matching
        pattern_matches = sum(
            1 for pattern in rule.patterns if re.search(pattern, description, re.IGNORECASE)
        )
        if pattern_matches > 0:
            pattern_score = (pattern_matches / len(rule.patterns)) * 0.3
            score += pattern_score

        # Exclusion keywords (negative scoring)
        exclusion_matches = sum(1 for keyword in rule.exclusion_keywords if keyword in description)
        if exclusion_matches > 0:
            score -= exclusion_matches * 0.2

        # Context boost
        user_role = user_context.get("role", "").lower()
        if user_role in rule.context_boost:
            score += rule.context_boost[user_role]

        # Apply rule weight
        score *= rule.weight

        return max(0.0, min(score, 1.0))

    def _find_keyword_matches(self, keywords: list[str], description: str) -> list[str]:
        """Find which keywords matched in the description"""
        return [keyword for keyword in keywords if keyword in description]

    def _find_pattern_matches(self, patterns: list[str], description: str) -> list[str]:
        """Find which patterns matched in the description"""
        matches = []
        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _prepare_llm_context(
        self,
        description: str,
        user_context: dict[str, Any],
        rule_result: ActivityClassificationResult | None,
    ) -> dict[str, str]:
        """Prepare context information for LLM prompt"""

        # Activity types and categories
        activity_types = "\n".join([f"- {at.value}: {at.name}" for at in ActivityType])
        competency_categories = "\n".join([f"- {cc.value}: {cc.name}" for cc in CompetencyCategory])

        # User context
        user_role = user_context.get("role", "Unknown")
        user_department = user_context.get("department", "Unknown")

        # Rule-based hints
        rule_hints = ""
        if rule_result:
            rule_hints = f"""
Rule-based analysis suggests:
- Activity Type: {rule_result.primary_classification.value}
- Confidence: {rule_result.confidence:.2f}
- Matched Keywords: {", ".join(rule_result.keyword_matches.get(rule_result.matched_rules[0], []))}
Please consider this analysis but make your own determination.
"""

        return {
            "description": description,
            "activity_types": activity_types,
            "competency_categories": competency_categories,
            "user_role": user_role,
            "user_department": user_department,
            "rule_hints": rule_hints,
        }

    def _parse_llm_response(
        self, response_content: str, description: str
    ) -> ActivityClassificationResult | None:
        """Parse LLM response into structured classification result"""

        # Simplified parsing - in production would use structured JSON output
        try:
            # Extract activity type
            activity_type = ActivityType.OTHER
            for at in ActivityType:
                if at.value.lower() in response_content.lower():
                    activity_type = at
                    break

            # Extract competency categories
            competency_categories = []
            for cc in CompetencyCategory:
                if cc.value.lower() in response_content.lower():
                    competency_categories.append(cc)

            if not competency_categories:
                competency_categories = [CompetencyCategory.TECHNICAL_SKILLS]

            # Extract confidence (look for confidence mentions)
            confidence = 0.7  # Default LLM confidence
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

            # Extract reasoning
            reasoning = (
                response_content[:200] + "..." if len(response_content) > 200 else response_content
            )

            return ActivityClassificationResult(
                activity_description=description,
                primary_classification=activity_type,
                competency_categories=competency_categories[:3],  # Max 3
                confidence=confidence,
                confidence_level=ClassificationConfidence.HIGH
                if confidence >= 0.8
                else ClassificationConfidence.MEDIUM
                if confidence >= 0.5
                else ClassificationConfidence.LOW,
                method=ClassificationMethod.LLM_ASSISTED,
                llm_reasoning=reasoning,
                llm_confidence=confidence,
                processing_time=0.0,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse LLM response: {str(e)}")
            return None

    def _create_hybrid_classification(
        self,
        description: str,
        rule_result: ActivityClassificationResult,
        llm_result: ActivityClassificationResult,
    ) -> ActivityClassificationResult:
        """Create hybrid classification from rule and LLM results"""

        # Weighted combination of confidences
        rule_weight = 0.6
        llm_weight = 0.4

        combined_confidence = (
            rule_result.confidence * rule_weight + llm_result.confidence * llm_weight
        )

        # Choose primary classification based on confidence
        if rule_result.confidence > llm_result.confidence:
            primary = rule_result.primary_classification
            competencies = rule_result.competency_categories
        else:
            primary = llm_result.primary_classification
            competencies = llm_result.competency_categories

        # Combine alternative classifications
        alternatives = (
            rule_result.alternative_classifications + llm_result.alternative_classifications
        )

        return ActivityClassificationResult(
            activity_description=description,
            primary_classification=primary,
            competency_categories=competencies,
            confidence=combined_confidence,
            confidence_level=ClassificationConfidence.HIGH
            if combined_confidence >= 0.8
            else ClassificationConfidence.MEDIUM
            if combined_confidence >= 0.5
            else ClassificationConfidence.LOW,
            method=ClassificationMethod.HYBRID,
            alternative_classifications=alternatives[:5],  # Top 5
            matched_rules=rule_result.matched_rules,
            keyword_matches=rule_result.keyword_matches,
            pattern_matches=rule_result.pattern_matches,
            llm_reasoning=llm_result.llm_reasoning,
            llm_confidence=llm_result.llm_confidence,
            processing_time=0.0,
        )

    def _create_fallback_classification(
        self, description: str, rule_result: ActivityClassificationResult | None = None
    ) -> ActivityClassificationResult:
        """Create fallback classification when other methods fail"""

        # Use rule result if available, otherwise generic fallback
        if rule_result:
            return ActivityClassificationResult(
                activity_description=description,
                primary_classification=rule_result.primary_classification,
                competency_categories=rule_result.competency_categories,
                confidence=max(rule_result.confidence * 0.5, 0.2),  # Reduce confidence
                confidence_level=ClassificationConfidence.LOW,
                method=ClassificationMethod.FALLBACK,
                alternative_classifications=rule_result.alternative_classifications,
                matched_rules=rule_result.matched_rules,
                processing_time=0.0,
            )
        else:
            return ActivityClassificationResult(
                activity_description=description,
                primary_classification=ActivityType.OTHER,
                competency_categories=[CompetencyCategory.TECHNICAL_SKILLS],
                confidence=0.2,
                confidence_level=ClassificationConfidence.LOW,
                method=ClassificationMethod.FALLBACK,
                processing_time=0.0,
            )

    def _build_classification_rules(self) -> list[ClassificationRule]:
        """Build comprehensive classification rules"""

        rules = []

        # Technical Activities
        rules.append(
            ClassificationRule(
                name="coding_development",
                activity_type=ActivityType.CODING,
                competency_categories=[
                    CompetencyCategory.TECHNICAL_SKILLS,
                    CompetencyCategory.PROBLEM_SOLVING,
                ],
                keywords=[
                    "code",
                    "coding",
                    "programming",
                    "develop",
                    "implement",
                    "script",
                    "function",
                    "method",
                    "algorithm",
                    "refactor",
                    "commit",
                    "git",
                    "github",
                    "python",
                    "javascript",
                    "java",
                    "c++",
                    "sql",
                    "api",
                    "library",
                ],
                patterns=[
                    r"\b(wrote|implemented|coded|developed)\s+\w+",
                    r"\b(fix|fixed|fixing)\s+\w*bug\w*",
                    r"\b(create|created|building)\s+\w*(app|application|service|component)\w*",
                    r"\b(git\s+commit|pull\s+request|merge|branch)\b",
                ],
                exclusion_keywords=["meeting", "discussion", "planning"],
                weight=1.2,
                context_boost={"engineer": 0.1, "developer": 0.1, "programmer": 0.1},
            )
        )

        rules.append(
            ClassificationRule(
                name="debugging_troubleshooting",
                activity_type=ActivityType.DEBUGGING,
                competency_categories=[
                    CompetencyCategory.PROBLEM_SOLVING,
                    CompetencyCategory.TECHNICAL_SKILLS,
                ],
                keywords=[
                    "debug",
                    "bug",
                    "fix",
                    "error",
                    "issue",
                    "troubleshoot",
                    "investigate",
                    "trace",
                    "diagnose",
                    "resolve",
                    "crash",
                    "exception",
                    "logs",
                    "root cause",
                ],
                patterns=[
                    r"\b(debug|debugging)\b",
                    r"\b(fix|fixed|fixing)\s+(bug|issue|error|problem)",
                    r"\b(investigate|investigating)\s+\w*(issue|problem|error)\w*",
                    r"\b(root\s+cause|troubleshoot|diagnose)\b",
                ],
                exclusion_keywords=["documentation", "meeting"],
                weight=1.1,
            )
        )

        rules.append(
            ClassificationRule(
                name="testing_qa",
                activity_type=ActivityType.TESTING,
                competency_categories=[
                    CompetencyCategory.QUALITY_ASSURANCE,
                    CompetencyCategory.TECHNICAL_SKILLS,
                ],
                keywords=[
                    "test",
                    "testing",
                    "unit test",
                    "integration test",
                    "qa",
                    "quality",
                    "validation",
                    "verify",
                    "automation",
                    "selenium",
                    "junit",
                    "pytest",
                    "coverage",
                    "mock",
                    "stub",
                ],
                patterns=[
                    r"\b(test|testing|tested)\b",
                    r"\b(unit|integration|e2e|end.to.end)\s+test",
                    r"\b(quality\s+assurance|qa|validation)\b",
                    r"\b(test\s+coverage|code\s+coverage)\b",
                ],
                exclusion_keywords=["meeting", "planning"],
                weight=1.0,
                context_boost={"tester": 0.2, "qa": 0.2},
            )
        )

        # Leadership Activities
        rules.append(
            ClassificationRule(
                name="mentoring_coaching",
                activity_type=ActivityType.MENTORING,
                competency_categories=[
                    CompetencyCategory.LEADERSHIP,
                    CompetencyCategory.COMMUNICATION,
                ],
                keywords=[
                    "mentor",
                    "coach",
                    "guide",
                    "teach",
                    "train",
                    "onboard",
                    "junior",
                    "intern",
                    "help",
                    "support",
                    "pair programming",
                    "knowledge transfer",
                    "shadowing",
                    "1:1",
                    "one on one",
                ],
                patterns=[
                    r"\b(mentor|mentoring|coached|coaching)\b",
                    r"\b(helped|helping|assisted)\s+\w*(junior|intern|new|colleague)\w*",
                    r"\b(pair\s+programming|knowledge\s+transfer)\b",
                    r"\b(onboard|onboarding|training)\s+\w*(new|junior)\w*",
                ],
                exclusion_keywords=["meeting", "formal training"],
                weight=1.1,
                context_boost={"senior": 0.1, "lead": 0.2, "manager": 0.2},
            )
        )

        rules.append(
            ClassificationRule(
                name="project_planning",
                activity_type=ActivityType.PLANNING,
                competency_categories=[
                    CompetencyCategory.PROJECT_MANAGEMENT,
                    CompetencyCategory.LEADERSHIP,
                ],
                keywords=[
                    "plan",
                    "planning",
                    "strategy",
                    "roadmap",
                    "estimate",
                    "schedule",
                    "timeline",
                    "milestone",
                    "goal",
                    "objective",
                    "scope",
                    "requirements",
                    "sprint planning",
                    "backlog",
                    "user story",
                    "epic",
                ],
                patterns=[
                    r"\b(plan|planning|planned)\b",
                    r"\b(roadmap|timeline|milestone|schedule)\b",
                    r"\b(sprint\s+planning|backlog\s+refinement)\b",
                    r"\b(estimate|estimation|scoping)\b",
                ],
                exclusion_keywords=["vacation", "personal"],
                weight=1.0,
                context_boost={"lead": 0.1, "manager": 0.2, "architect": 0.1},
            )
        )

        # Learning Activities
        rules.append(
            ClassificationRule(
                name="research_investigation",
                activity_type=ActivityType.RESEARCH,
                competency_categories=[
                    CompetencyCategory.LEARNING_DEVELOPMENT,
                    CompetencyCategory.INNOVATION,
                ],
                keywords=[
                    "research",
                    "study",
                    "investigate",
                    "explore",
                    "analyze",
                    "evaluate",
                    "compare",
                    "prototype",
                    "poc",
                    "proof of concept",
                    "spike",
                    "feasibility",
                    "benchmark",
                    "survey",
                    "analysis",
                ],
                patterns=[
                    r"\b(research|researching|investigated)\b",
                    r"\b(proof\s+of\s+concept|poc|prototype|prototyping)\b",
                    r"\b(feasibility\s+study|technical\s+analysis)\b",
                    r"\b(benchmark|benchmarking|comparison)\b",
                ],
                exclusion_keywords=["meeting", "discussion"],
                weight=1.0,
            )
        )

        rules.append(
            ClassificationRule(
                name="documentation_writing",
                activity_type=ActivityType.DOCUMENTATION,
                competency_categories=[
                    CompetencyCategory.COMMUNICATION,
                    CompetencyCategory.QUALITY_ASSURANCE,
                ],
                keywords=[
                    "document",
                    "documentation",
                    "wiki",
                    "readme",
                    "spec",
                    "specification",
                    "write",
                    "article",
                    "guide",
                    "manual",
                    "instructions",
                    "comments",
                    "docstring",
                    "api docs",
                    "user guide",
                ],
                patterns=[
                    r"\b(document|documenting|documented)\b",
                    r"\b(wrote|writing|updated)\s+\w*(documentation|docs|guide|manual)\w*",
                    r"\b(readme|spec|specification|wiki)\b",
                    r"\b(api\s+doc|user\s+guide|technical\s+writing)\b",
                ],
                exclusion_keywords=["meeting notes", "email"],
                weight=1.0,
            )
        )

        # Communication Activities
        rules.append(
            ClassificationRule(
                name="meetings_collaboration",
                activity_type=ActivityType.TEAM_MEETINGS,
                competency_categories=[
                    CompetencyCategory.COLLABORATION,
                    CompetencyCategory.COMMUNICATION,
                ],
                keywords=[
                    "meeting",
                    "standup",
                    "retrospective",
                    "planning meeting",
                    "sync",
                    "discussion",
                    "review meeting",
                    "1:1",
                    "one on one",
                    "demo",
                    "presentation",
                    "brainstorm",
                    "workshop",
                    "collaboration",
                ],
                patterns=[
                    r"\b(meeting|meetings|attended|participated)\b",
                    r"\b(standup|stand.up|daily\s+sync)\b",
                    r"\b(retrospective|retro|sprint\s+review)\b",
                    r"\b(brainstorm|brainstorming|workshop)\b",
                ],
                exclusion_keywords=["coding", "implementation"],
                weight=0.9,  # Lower weight as meetings are common
            )
        )

        return rules

    def _build_llm_prompt_template(self) -> str:
        """Build LLM prompt template for classification"""

        return """
You are an expert at classifying software engineering activities. Classify the following activity into the most appropriate category.

Activity: {description}

User Context:
- Role: {user_role}
- Department: {user_department}

{rule_hints}

Available Activity Types:
{activity_types}

Available Competency Categories:
{competency_categories}

Please analyze the activity and provide:
1. Primary activity type (from the list above)
2. 1-3 most relevant competency categories
3. Confidence level (0.0-1.0)
4. Brief reasoning for your classification

Focus on the core action being performed rather than peripheral activities.

Classification:
"""

    def _update_stats(self, method: str, confidence: float, processing_time: float):
        """Update classification statistics"""

        self._stats["total_classifications"] += 1

        if method == "rule_based":
            self._stats["rule_based_success"] += 1
        elif method == "llm_fallback":
            self._stats["llm_fallback_used"] += 1

        if confidence >= 0.8:
            self._stats["high_confidence_results"] += 1

        # Update averages
        total = self._stats["total_classifications"]
        current_avg_conf = self._stats["average_confidence"]
        current_avg_time = self._stats["average_processing_time"]

        self._stats["average_confidence"] = ((current_avg_conf * (total - 1)) + confidence) / total
        self._stats["average_processing_time"] = (
            (current_avg_time * (total - 1)) + processing_time
        ) / total

    def get_classification_stats(self) -> dict[str, Any]:
        """Get classification performance statistics"""
        return self._stats.copy()

    def get_supported_activity_types(self) -> list[str]:
        """Get list of supported activity types"""
        return [at.value for at in ActivityType]

    def get_supported_competency_categories(self) -> list[str]:
        """Get list of supported competency categories"""
        return [cc.value for cc in CompetencyCategory]


# Global classifier instance
_global_classifier: ActivityClassificationEngine | None = None


def get_activity_classifier(enable_llm_fallback: bool = True) -> ActivityClassificationEngine:
    """Get global activity classification engine instance"""
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = ActivityClassificationEngine(enable_llm_fallback=enable_llm_fallback)
    return _global_classifier

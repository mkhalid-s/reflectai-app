"""
Matching Engine for ReflectAI
Handles opportunity matching, recommendations, and fit scoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np

from src.shared.error_handlers import handle_errors
from src.shared.exceptions import ErrorCategory
from src.shared.logging import get_logger

logger = get_logger(__name__)


class MatchType(Enum):
    """Types of matches."""

    ROLE = "role"
    PROJECT = "project"
    MENTOR = "mentor"
    TEAM = "team"
    LEARNING = "learning"
    COLLABORATION = "collaboration"


@dataclass
class Opportunity:
    """Represents an opportunity to match."""

    opportunity_id: str
    type: MatchType
    title: str
    description: str
    requirements: dict[str, Any]
    preferences: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


@dataclass
class MatchResult:
    """Result of a matching operation."""

    match_id: str
    user_id: str
    opportunity: Opportunity
    match_score: float  # 0.0 to 1.0
    fit_analysis: dict[str, float]
    strengths: list[str]
    gaps: list[str]
    recommendation: str
    confidence: float


class MatchingEngine:
    """
    Engine for matching users with opportunities.

    Features:
    - Multi-criteria matching
    - Weighted scoring algorithms
    - Fit analysis
    - Recommendation generation
    - Match optimization
    """

    def __init__(self):
        self.matching_weights = self._initialize_weights()
        self.scoring_functions = self._initialize_scoring_functions()

        logger.info("Matching Engine initialized")

    def _initialize_weights(self) -> dict[str, dict[str, float]]:
        """Initialize matching weights for different match types."""
        return {
            MatchType.ROLE: {
                "skills": 0.35,
                "experience": 0.25,
                "culture": 0.15,
                "growth": 0.15,
                "preferences": 0.10,
            },
            MatchType.PROJECT: {
                "skills": 0.40,
                "availability": 0.20,
                "interest": 0.20,
                "experience": 0.20,
            },
            MatchType.MENTOR: {
                "expertise": 0.30,
                "availability": 0.20,
                "style": 0.20,
                "goals": 0.30,
            },
            MatchType.TEAM: {
                "skills": 0.25,
                "culture": 0.35,
                "collaboration": 0.25,
                "diversity": 0.15,
            },
            MatchType.LEARNING: {"relevance": 0.35, "level": 0.25, "format": 0.20, "timing": 0.20},
        }

    def _initialize_scoring_functions(self) -> dict[str, Any]:
        """Initialize scoring functions for different criteria."""
        return {
            "skills": self._score_skills_match,
            "experience": self._score_experience_match,
            "culture": self._score_culture_match,
            "availability": self._score_availability_match,
            "interest": self._score_interest_match,
            "expertise": self._score_expertise_match,
            "relevance": self._score_relevance_match,
        }

    @handle_errors(category=ErrorCategory.BUSINESS_RULE_ERROR)
    async def find_matches(
        self,
        user_profile: dict[str, Any],
        opportunities: list[Opportunity],
        match_type: MatchType | None = None,
        top_k: int = 10,
    ) -> list[MatchResult]:
        """
        Find best matches for a user.

        Args:
            user_profile: User profile data
            opportunities: Available opportunities
            match_type: Filter by match type
            top_k: Number of top matches to return

        Returns:
            Sorted list of match results
        """
        try:
            matches = []

            for opportunity in opportunities:
                # Filter by type if specified
                if match_type and opportunity.type != match_type:
                    continue

                # Calculate match score
                match_result = await self._calculate_match(user_profile, opportunity)

                if match_result.match_score > 0.3:  # Minimum threshold
                    matches.append(match_result)

            # Sort by score
            matches.sort(key=lambda m: m.match_score, reverse=True)

            # Apply diversity optimization
            optimized_matches = self._optimize_diversity(matches, top_k)

            logger.info(
                f"Found {len(optimized_matches)} matches",
                extra={
                    "user_id": user_profile.get("user_id"),
                    "total_opportunities": len(opportunities),
                    "match_type": match_type.value if match_type else "all",
                },
            )

            return optimized_matches[:top_k]

        except Exception as e:
            logger.error(f"Failed to find matches: {e}")
            raise

    async def _calculate_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> MatchResult:
        """Calculate match between user and opportunity."""
        # Get weights for this match type
        weights = self.matching_weights.get(opportunity.type, self.matching_weights[MatchType.ROLE])

        # Calculate component scores
        fit_analysis = {}
        total_score = 0.0

        for criterion, weight in weights.items():
            scoring_func = self.scoring_functions.get(criterion, self._default_scoring)

            score = await scoring_func(user_profile, opportunity)
            fit_analysis[criterion] = score
            total_score += score * weight

        # Identify strengths and gaps
        strengths = [criterion for criterion, score in fit_analysis.items() if score > 0.7]

        gaps = [criterion for criterion, score in fit_analysis.items() if score < 0.4]

        # Generate recommendation
        recommendation = self._generate_recommendation(total_score, strengths, gaps, opportunity)

        # Calculate confidence
        confidence = self._calculate_confidence(fit_analysis, user_profile, opportunity)

        return MatchResult(
            match_id=f"{user_profile.get('user_id', 'unknown')}_{opportunity.opportunity_id}",
            user_id=user_profile.get("user_id", "unknown"),
            opportunity=opportunity,
            match_score=total_score,
            fit_analysis=fit_analysis,
            strengths=strengths,
            gaps=gaps,
            recommendation=recommendation,
            confidence=confidence,
        )

    async def _score_skills_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score skills match between user and opportunity."""
        user_skills = set(user_profile.get("skills", []))
        required_skills = set(opportunity.requirements.get("skills", []))

        if not required_skills:
            return 0.5  # Neutral if no requirements

        # Calculate overlap
        overlap = user_skills.intersection(required_skills)
        coverage = len(overlap) / len(required_skills)

        # Bonus for extra relevant skills
        extra_skills = user_skills - required_skills
        bonus = min(len(extra_skills) / 10, 0.2)

        return min(coverage + bonus, 1.0)

    async def _score_experience_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score experience match."""
        user_exp = user_profile.get("experience_years", 0)
        min_exp = opportunity.requirements.get("min_experience", 0)
        max_exp = opportunity.requirements.get("max_experience", 100)
        ideal_exp = opportunity.preferences.get("ideal_experience", (min_exp + max_exp) / 2)

        if user_exp < min_exp:
            return max(0, 1 - (min_exp - user_exp) / min_exp)
        elif user_exp > max_exp:
            return max(0, 1 - (user_exp - max_exp) / max_exp)
        else:
            # Calculate distance from ideal
            distance = abs(user_exp - ideal_exp)
            max_distance = max(ideal_exp - min_exp, max_exp - ideal_exp)
            return 1 - (distance / max_distance) if max_distance > 0 else 1.0

    async def _score_culture_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score cultural fit."""
        user_values = set(user_profile.get("values", []))
        org_values = set(opportunity.metadata.get("culture_values", []))

        if not org_values:
            return 0.5  # Neutral if no data

        overlap = user_values.intersection(org_values)
        return len(overlap) / len(org_values) if org_values else 0.5

    async def _score_availability_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score availability match."""
        user_availability = user_profile.get("availability_hours", 40)
        required_hours = opportunity.requirements.get("hours_per_week", 40)

        if user_availability >= required_hours:
            return 1.0
        else:
            return user_availability / required_hours

    async def _score_interest_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score interest alignment."""
        user_interests = set(user_profile.get("interests", []))
        opp_keywords = set(
            opportunity.title.lower().split() + opportunity.description.lower().split()[:20]
        )

        # Simple keyword matching (would use embeddings in production)
        interest_keywords = set()
        for interest in user_interests:
            interest_keywords.update(interest.lower().split())

        overlap = interest_keywords.intersection(opp_keywords)
        return min(len(overlap) / 5, 1.0)  # 5 keywords = perfect match

    async def _score_expertise_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score expertise match for mentoring."""
        user_expertise = user_profile.get("expertise_areas", {})
        needed_expertise = opportunity.requirements.get("expertise_areas", {})

        if not needed_expertise:
            return 0.5

        total_score = 0.0
        for area, required_level in needed_expertise.items():
            user_level = user_expertise.get(area, 0)
            if user_level >= required_level:
                total_score += 1.0
            else:
                total_score += user_level / required_level if required_level > 0 else 0

        return total_score / len(needed_expertise) if needed_expertise else 0.5

    async def _score_relevance_match(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Score relevance for learning opportunities."""
        user_goals = user_profile.get("learning_goals", [])
        opp_topics = opportunity.metadata.get("topics", [])

        if not opp_topics or not user_goals:
            return 0.5

        # Check topic alignment with goals
        relevance_score = 0.0
        for topic in opp_topics:
            for goal in user_goals:
                if topic.lower() in goal.lower() or goal.lower() in topic.lower():
                    relevance_score += 1.0

        return min(relevance_score / len(opp_topics), 1.0)

    async def _default_scoring(
        self, user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Default scoring function."""
        return 0.5  # Neutral score

    def _generate_recommendation(
        self, score: float, strengths: list[str], gaps: list[str], opportunity: Opportunity
    ) -> str:
        """Generate recommendation text."""
        if score > 0.8:
            return f"Excellent match! Your strengths in {', '.join(strengths[:2])} make you ideal for this {opportunity.type.value}."
        elif score > 0.6:
            return f"Good match with growth potential. Consider improving {', '.join(gaps[:2])} to maximize success."
        elif score > 0.4:
            return f"Moderate match. This {opportunity.type.value} could be a stretch opportunity to develop {', '.join(gaps[:2])}."
        else:
            return f"Limited match. Focus on building {', '.join(gaps[:2])} before pursuing this opportunity."

    def _calculate_confidence(
        self, fit_analysis: dict[str, float], user_profile: dict[str, Any], opportunity: Opportunity
    ) -> float:
        """Calculate confidence in match score."""
        # Base confidence on data completeness
        profile_completeness = len([v for v in user_profile.values() if v]) / 10
        opp_completeness = len([v for v in opportunity.requirements.values() if v]) / 5

        data_confidence = (profile_completeness + opp_completeness) / 2

        # Adjust based on score variance
        scores = list(fit_analysis.values())
        if scores:
            score_variance = np.std(scores)
            consistency_factor = 1 - min(score_variance, 0.5)
        else:
            consistency_factor = 0.5

        return min(data_confidence * consistency_factor, 1.0)

    def _optimize_diversity(self, matches: list[MatchResult], top_k: int) -> list[MatchResult]:
        """Optimize match list for diversity."""
        if len(matches) <= top_k:
            return matches

        optimized = []
        remaining = matches.copy()

        # Add top match
        if remaining:
            optimized.append(remaining.pop(0))

        # Add diverse matches
        while len(optimized) < top_k and remaining:
            # Find most diverse match
            max_diversity = 0
            most_diverse = None
            most_diverse_idx = 0

            for idx, match in enumerate(remaining):
                diversity = self._calculate_diversity(match, optimized)
                if diversity > max_diversity:
                    max_diversity = diversity
                    most_diverse = match
                    most_diverse_idx = idx

            if most_diverse:
                optimized.append(most_diverse)
                remaining.pop(most_diverse_idx)

        return optimized

    def _calculate_diversity(self, candidate: MatchResult, selected: list[MatchResult]) -> float:
        """Calculate diversity score for a candidate match."""
        if not selected:
            return 1.0

        # Type diversity
        type_diversity = sum(
            1 for m in selected if m.opportunity.type != candidate.opportunity.type
        ) / len(selected)

        # Score diversity
        score_differences = [abs(candidate.match_score - m.match_score) for m in selected]
        score_diversity = np.mean(score_differences) if score_differences else 0

        return (type_diversity + score_diversity) / 2

    async def explain_match(self, match_result: MatchResult) -> dict[str, Any]:
        """Generate detailed explanation of a match."""
        explanation = {
            "summary": f"Match score: {match_result.match_score:.2%}",
            "strengths_detail": {},
            "gaps_detail": {},
            "improvement_areas": [],
            "success_factors": [],
        }

        # Detailed strengths
        for strength in match_result.strengths:
            score = match_result.fit_analysis.get(strength, 0)
            explanation["strengths_detail"][strength] = {
                "score": score,
                "description": f"Strong {strength} alignment ({score:.2%})",
            }

        # Detailed gaps
        for gap in match_result.gaps:
            score = match_result.fit_analysis.get(gap, 0)
            explanation["gaps_detail"][gap] = {
                "score": score,
                "description": f"Gap in {gap} ({score:.2%})",
                "improvement": f"Focus on improving {gap} to increase match score",
            }

        # Success factors
        if match_result.match_score > 0.7:
            explanation["success_factors"] = [
                "High overall compatibility",
                "Strong alignment in key areas",
                "Good potential for success",
            ]

        # Improvement areas
        for criterion, score in match_result.fit_analysis.items():
            if score < 0.6:
                explanation["improvement_areas"].append(
                    {
                        "area": criterion,
                        "current_score": score,
                        "target_score": 0.7,
                        "impact": "High" if criterion in match_result.gaps else "Medium",
                    }
                )

        return explanation

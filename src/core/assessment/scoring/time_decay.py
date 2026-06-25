"""
Time Decay Calculation for ReflectAI Competency Assessment

Implements  Simple Competency Assessment time decay logic:
- Linear time decay: activities lose value over time (1.0 weight today → 0.0 weight at 90 days)
- Exponential decay options for different activity types
- Configurable decay parameters per competency type
- Time window management and calculation utilities

Provides time-based weighting for activity relevance in competency scoring.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared import get_logger


class DecayFunction(Enum):
    """Time decay function types"""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    STEP = "step"
    CUSTOM = "custom"


@dataclass
class DecayParameters:
    """Parameters for time decay calculation"""

    function_type: DecayFunction
    time_window_days: int = 90
    decay_rate: float = 1.0  # Rate of decay (higher = faster decay)
    minimum_weight: float = 0.0  # Minimum weight (floor)
    maximum_weight: float = 1.0  # Maximum weight (ceiling)
    half_life_days: int | None = None  # For exponential decay
    step_boundaries: list[int] | None = None  # For step function


class TimeDecayResult(BaseModel):
    """Result of time decay calculation"""

    original_value: float = Field(..., description="Original activity value")
    decay_weight: float = Field(..., description="Calculated decay weight (0.0-1.0)")
    weighted_value: float = Field(..., description="Value after applying decay weight")
    days_ago: int = Field(..., description="Days since the activity")
    decay_function: str = Field(..., description="Decay function used")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Decay parameters used")


class TimeDecayCalculator:
    """Time decay calculator for competency assessment"""

    def __init__(self) -> None:
        self.logger = get_logger("assessment.time_decay")

        # Default decay parameters for different competency types
        self.default_parameters = {
            "technical_skills": DecayParameters(
                function_type=DecayFunction.LINEAR,
                time_window_days=90,
                decay_rate=1.0,
                minimum_weight=0.0,
            ),
            "leadership": DecayParameters(
                function_type=DecayFunction.EXPONENTIAL,
                time_window_days=120,  # Leadership experience lasts longer
                decay_rate=0.8,
                minimum_weight=0.1,
                half_life_days=60,
            ),
            "communication": DecayParameters(
                function_type=DecayFunction.LINEAR,
                time_window_days=60,  # Communication skills need regular practice
                decay_rate=1.2,
                minimum_weight=0.0,
            ),
            "project_management": DecayParameters(
                function_type=DecayFunction.STEP,
                time_window_days=90,
                step_boundaries=[30, 60, 90],
                minimum_weight=0.2,
            ),
            "general": DecayParameters(
                function_type=DecayFunction.LINEAR,
                time_window_days=90,
                decay_rate=1.0,
                minimum_weight=0.0,
            ),
        }

    def calculate_decay_weight(
        self,
        activity_date: datetime,
        competency_type: str = "general",
        reference_date: datetime | None = None,
        custom_parameters: DecayParameters | None = None,
    ) -> float:
        """Calculate time decay weight for an activity"""

        if reference_date is None:
            reference_date = datetime.now(UTC)

        # Get decay parameters
        parameters = custom_parameters or self.default_parameters.get(
            competency_type, self.default_parameters["general"]
        )

        # Calculate days since activity
        days_ago = (reference_date - activity_date).days

        # Handle future dates or same day
        if days_ago <= 0:
            return parameters.maximum_weight

        # Handle activities outside time window
        if days_ago > parameters.time_window_days:
            return parameters.minimum_weight

        # Calculate decay weight based on function type
        if parameters.function_type == DecayFunction.LINEAR:
            weight = self._linear_decay(days_ago, parameters)
        elif parameters.function_type == DecayFunction.EXPONENTIAL:
            weight = self._exponential_decay(days_ago, parameters)
        elif parameters.function_type == DecayFunction.LOGARITHMIC:
            weight = self._logarithmic_decay(days_ago, parameters)
        elif parameters.function_type == DecayFunction.STEP:
            weight = self._step_decay(days_ago, parameters)
        else:
            weight = self._linear_decay(days_ago, parameters)  # Default fallback

        # Apply bounds
        weight = max(parameters.minimum_weight, min(parameters.maximum_weight, weight))

        return weight

    def calculate_weighted_value(
        self,
        activity_value: float,
        activity_date: datetime,
        competency_type: str = "general",
        reference_date: datetime | None = None,
        custom_parameters: DecayParameters | None = None,
    ) -> TimeDecayResult:
        """Calculate weighted value with decay applied"""

        if reference_date is None:
            reference_date = datetime.now(UTC)

        parameters = custom_parameters or self.default_parameters.get(
            competency_type, self.default_parameters["general"]
        )

        days_ago = (reference_date - activity_date).days
        decay_weight = self.calculate_decay_weight(
            activity_date, competency_type, reference_date, custom_parameters
        )

        weighted_value = activity_value * decay_weight

        return TimeDecayResult(
            original_value=activity_value,
            decay_weight=decay_weight,
            weighted_value=weighted_value,
            days_ago=max(0, days_ago),
            decay_function=parameters.function_type.value,
            parameters={
                "time_window_days": parameters.time_window_days,
                "decay_rate": parameters.decay_rate,
                "minimum_weight": parameters.minimum_weight,
                "maximum_weight": parameters.maximum_weight,
            },
        )

    def calculate_bulk_weighted_values(
        self,
        activities: list[dict[str, Any]],
        value_field: str = "value",
        date_field: str = "date",
        competency_field: str = "competency_type",
        reference_date: datetime | None = None,
    ) -> list[TimeDecayResult]:
        """Calculate weighted values for multiple activities"""

        results = []

        for activity in activities:
            try:
                activity_value = activity.get(value_field, 1.0)
                activity_date = activity.get(date_field)
                competency_type = activity.get(competency_field, "general")

                # Handle date parsing if needed
                if isinstance(activity_date, str):
                    activity_date = datetime.fromisoformat(activity_date.replace("Z", "+00:00"))
                elif activity_date is None:
                    self.logger.warning("Missing date for activity, using current time")
                    activity_date = datetime.now(UTC)

                result = self.calculate_weighted_value(
                    activity_value, activity_date, competency_type, reference_date
                )

                results.append(result)

            except Exception as e:
                self.logger.error(f"Error calculating decay for activity: {str(e)}")
                # Create a fallback result
                results.append(
                    TimeDecayResult(
                        original_value=activity.get(value_field, 0.0),
                        decay_weight=0.0,
                        weighted_value=0.0,
                        days_ago=999,
                        decay_function="error",
                        parameters={},
                    )
                )

        return results

    def _linear_decay(self, days_ago: int, params: DecayParameters) -> float:
        """Calculate linear decay weight"""
        # Linear decay: weight = 1.0 - (days_ago / time_window) * decay_rate
        decay_progress = min(1.0, days_ago / params.time_window_days)
        weight = 1.0 - (decay_progress * params.decay_rate)
        return weight

    def _exponential_decay(self, days_ago: int, params: DecayParameters) -> float:
        """Calculate exponential decay weight"""
        if params.half_life_days:
            # Exponential decay with half-life
            weight = 0.5 ** (days_ago / params.half_life_days)
        else:
            # Standard exponential decay
            decay_constant = params.decay_rate / params.time_window_days
            weight = math.exp(-decay_constant * days_ago)

        return weight

    def _logarithmic_decay(self, days_ago: int, params: DecayParameters) -> float:
        """Calculate logarithmic decay weight"""
        if days_ago == 0:
            return 1.0

        # Logarithmic decay: weight = 1 - log(1 + days_ago * decay_rate) / log(1 + time_window)
        max_log = math.log(1 + params.time_window_days * params.decay_rate)
        current_log = math.log(1 + days_ago * params.decay_rate)
        weight = 1.0 - (current_log / max_log)

        return weight

    def _step_decay(self, days_ago: int, params: DecayParameters) -> float:
        """Calculate step function decay weight"""
        if not params.step_boundaries:
            return self._linear_decay(days_ago, params)  # Fallback to linear

        boundaries = sorted(params.step_boundaries)

        # Determine which step we're in
        for i, boundary in enumerate(boundaries):
            if days_ago <= boundary:
                # Weight decreases with each step
                step_weight = 1.0 - (i / len(boundaries))
                return step_weight

        # Beyond all boundaries
        return params.minimum_weight

    def get_competency_parameters(self, competency_type: str) -> DecayParameters:
        """Get decay parameters for a competency type"""
        return self.default_parameters.get(competency_type, self.default_parameters["general"])

    def update_competency_parameters(
        self, competency_type: str, parameters: DecayParameters
    ) -> None:
        """Update decay parameters for a competency type"""
        self.default_parameters[competency_type] = parameters
        self.logger.info(f"Updated decay parameters for competency type: {competency_type}")

    def get_time_window_activities(
        self,
        activities: list[dict[str, Any]],
        competency_type: str = "general",
        date_field: str = "date",
        reference_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Filter activities within the time window for a competency type"""

        if reference_date is None:
            reference_date = datetime.now(UTC)

        parameters = self.get_competency_parameters(competency_type)
        cutoff_date = reference_date - timedelta(days=parameters.time_window_days)

        filtered_activities = []

        for activity in activities:
            try:
                activity_date = activity.get(date_field)

                if isinstance(activity_date, str):
                    activity_date = datetime.fromisoformat(activity_date.replace("Z", "+00:00"))
                elif activity_date is None:
                    continue  # Skip activities without dates

                if activity_date >= cutoff_date:
                    filtered_activities.append(activity)

            except Exception as e:
                self.logger.warning(f"Error parsing activity date: {str(e)}")
                continue

        return filtered_activities


# Global calculator instance
_global_calculator: TimeDecayCalculator | None = None


def get_time_decay_calculator() -> TimeDecayCalculator:
    """Get global time decay calculator instance"""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = TimeDecayCalculator()
    return _global_calculator

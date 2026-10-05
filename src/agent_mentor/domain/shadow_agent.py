from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShadowToolName(StrEnum):
    GET_WEAK_KNOWLEDGE_POINTS = "get_weak_knowledge_points"
    GET_UNCOVERED_TOPICS = "get_uncovered_topics"
    GET_RECENT_TRAINING_STATE = "get_recent_training_state"


class ShadowTrainingObjective(StrEnum):
    BALANCED = "balanced"
    STRENGTHEN_WEAKNESSES = "strengthen_weaknesses"
    CLOSE_COVERAGE_GAPS = "close_coverage_gaps"
    CONTINUE_REVIEW = "continue_review"


PRIMARY_TOOL_BY_OBJECTIVE: dict[ShadowTrainingObjective, ShadowToolName] = {
    ShadowTrainingObjective.BALANCED: ShadowToolName.GET_RECENT_TRAINING_STATE,
    ShadowTrainingObjective.STRENGTHEN_WEAKNESSES: ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS,
    ShadowTrainingObjective.CLOSE_COVERAGE_GAPS: ShadowToolName.GET_UNCOVERED_TOPICS,
    ShadowTrainingObjective.CONTINUE_REVIEW: ShadowToolName.GET_RECENT_TRAINING_STATE,
}


class ShadowRecommendationAction(StrEnum):
    FOCUSED_INTERVIEW = "focused_interview"
    REVIEW_PLAN = "review_plan"
    COVERAGE_STUDY = "coverage_study"
    MAINTAIN_CURRENT_PLAN = "maintain_current_plan"


class ShadowRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_action: ShadowRecommendationAction
    topic: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=1, max_length=600)
    supporting_observations: list[ShadowToolName] = Field(default_factory=list, max_length=3)
    suggested_parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    requires_confirmation: Literal[True] = True


class ShadowAgentDecision(BaseModel):
    """One model decision. Tool arguments are validated again by the executor."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["tool", "finish"]
    reasoning: str = Field(min_length=1, max_length=600)
    tool_name: ShadowToolName | None = None
    arguments: dict[str, object] = Field(default_factory=dict)
    recommendation: ShadowRecommendation | None = None

    @model_validator(mode="after")
    def validate_decision_shape(self) -> ShadowAgentDecision:
        if self.decision == "tool":
            if self.tool_name is None or self.recommendation is not None:
                raise ValueError("tool decision requires tool_name and forbids recommendation")
        elif self.tool_name is not None or self.arguments or self.recommendation is None:
            raise ValueError("finish decision requires recommendation and forbids tool fields")
        return self


class ShadowAgentV2Decision(BaseModel):
    """The model may inspect a second tool or finish; policy owns the final action."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["tool", "finish"]
    reasoning: str = Field(min_length=1, max_length=600)
    tool_name: ShadowToolName | None = None
    arguments: dict[str, object] = Field(default_factory=dict)
    topic: str | None = Field(default=None, max_length=160)
    suggested_parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_decision_shape(self) -> ShadowAgentV2Decision:
        if self.decision == "tool":
            if self.tool_name is None or self.topic is not None or self.suggested_parameters:
                raise ValueError("tool decision requires only tool_name and arguments")
        elif self.tool_name is not None or self.arguments:
            raise ValueError("finish decision forbids tool fields")
        return self


class ShadowToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=5, ge=1, le=10)


class ShadowAgentStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(ge=1, le=3)
    decision: Literal["tool", "finish", "fallback"]
    reasoning: str
    tool_name: ShadowToolName | None = None
    validated_arguments: dict[str, object] = Field(default_factory=dict)
    tool_result: dict[str, object] | None = None
    latency_ms: float = Field(ge=0)
    error_code: str | None = None


class ShadowAgentRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: Literal["completed", "fallback"]
    recommendation: ShadowRecommendation
    steps: list[ShadowAgentStep] = Field(min_length=1, max_length=3)
    termination_reason: str
    used_fallback: bool
    business_writes: Literal[0] = 0

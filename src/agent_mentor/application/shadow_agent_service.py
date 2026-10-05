from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol
from uuid import UUID, uuid4

from agent_mentor.application.profile_service import ProfileService
from agent_mentor.domain.shadow_agent import (
    ShadowAgentDecision,
    ShadowAgentRun,
    ShadowAgentStep,
    ShadowRecommendation,
    ShadowRecommendationAction,
    ShadowToolArguments,
    ShadowToolName,
)
from agent_mentor.ports.llm_gateway import LLMGateway, Message, ModelPolicy, TraceContext


class ShadowTraceRepository(Protocol):
    async def save(
        self, *, user_id: UUID, knowledge_base_id: UUID, run: ShadowAgentRun
    ) -> None: ...


class ShadowToolExecutor(Protocol):
    async def execute(
        self,
        tool_name: ShadowToolName,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        arguments: ShadowToolArguments,
    ) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class NullShadowTraceRepository:
    async def save(
        self, *, user_id: UUID, knowledge_base_id: UUID, run: ShadowAgentRun
    ) -> None:
        del user_id, knowledge_base_id, run


class ShadowReadTools:
    """Read-only facade. It exposes no profile, evaluation, task, or coverage mutation."""

    def __init__(self, profiles: ProfileService) -> None:
        self._profiles = profiles

    async def execute(
        self,
        tool_name: ShadowToolName,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        arguments: ShadowToolArguments,
    ) -> dict[str, object]:
        handlers: dict[ShadowToolName, Callable[[], Awaitable[dict[str, object]]]] = {
            ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: lambda: self._weak_points(
                user_id, knowledge_base_id, arguments.limit
            ),
            ShadowToolName.GET_UNCOVERED_TOPICS: lambda: self._uncovered_topics(
                knowledge_base_id, arguments.limit
            ),
            ShadowToolName.GET_RECENT_TRAINING_STATE: lambda: self._training_state(
                user_id, knowledge_base_id, arguments.limit
            ),
        }
        return await handlers[tool_name]()

    async def _weak_points(
        self, user_id: UUID, knowledge_base_id: UUID, limit: int
    ) -> dict[str, object]:
        snapshot = await self._profiles.get_snapshot(user_id, knowledge_base_id)
        points = sorted(
            (
                item
                for item in snapshot.abilities
                if item.profile_level == "topic" and item.mastery_score < 0.72
            ),
            key=lambda item: (item.mastery_score, item.knowledge_point),
        )[:limit]
        return {
            "items": [
                {
                    "knowledge_point": item.subtopic_title
                    or item.topic_title
                    or item.knowledge_point,
                    "topic_key": item.topic_key,
                    "mastery_score": item.mastery_score,
                    "confidence_weighted_count": item.confidence_weighted_count,
                }
                for item in points
            ]
        }

    async def _uncovered_topics(
        self, knowledge_base_id: UUID, limit: int
    ) -> dict[str, object]:
        coverage = await self._profiles.get_coverage(knowledge_base_id)
        items = [
            item
            for item in coverage.points
            if item.status in {"uncovered", "attempted", "insufficient_evidence"}
        ][:limit]
        return {
            "summary": {
                "total": coverage.total,
                "uncovered": coverage.uncovered,
                "attempted": coverage.attempted,
                "verified": coverage.verified,
            },
            "items": [
                {
                    "title": item.title,
                    "status": item.status,
                    "attempt_count": item.attempt_count,
                    "trusted_evaluation_count": item.trusted_evaluation_count,
                    "average_score": item.average_score,
                }
                for item in items
            ],
        }

    async def _training_state(
        self, user_id: UUID, knowledge_base_id: UUID, limit: int
    ) -> dict[str, object]:
        state = await self._profiles.get_recent_training_state(
            user_id, knowledge_base_id, limit=limit
        )
        return {
            "open_review_task_count": state.open_review_task_count,
            "open_review_tasks": [
                {
                    "knowledge_point": task.subtopic_title
                    or task.topic_title
                    or task.knowledge_point,
                    "error_type": str(task.error_type),
                    "priority": task.priority,
                    "verification_streak": task.verification_streak,
                    "due_at": task.due_at.isoformat(),
                }
                for task in state.open_review_tasks
            ],
            "recent_evaluations": [
                {
                    "topic": item.topic,
                    "total": item.total,
                    "confidence": item.confidence,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                }
                for item in state.recent_evaluations
            ],
        }


class ShadowAgentService:
    MAX_STEPS = 3

    def __init__(
        self,
        tools: ShadowToolExecutor,
        llm: LLMGateway | None,
        repository: ShadowTraceRepository | None = None,
        *,
        default_model: str | None = None,
    ) -> None:
        self._tools = tools
        self._llm = llm
        self._repository = repository or NullShadowTraceRepository()
        self._default_model = default_model

    async def recommend(
        self, *, user_id: UUID, knowledge_base_id: UUID
    ) -> ShadowAgentRun:
        run_id = str(uuid4())
        observations: list[dict[str, object]] = []
        steps: list[ShadowAgentStep] = []
        called_tools: set[ShadowToolName] = set()
        if self._llm is None:
            run = await self._fallback_run(
                run_id=run_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                steps=steps,
                reason="llm_unavailable",
            )
            await self._repository.save(
                user_id=user_id, knowledge_base_id=knowledge_base_id, run=run
            )
            return run

        try:
            for step_index in range(1, self.MAX_STEPS + 1):
                started = perf_counter()
                decision = await self._decide(run_id, step_index, observations)
                latency_ms = round((perf_counter() - started) * 1000, 3)
                if decision.decision == "finish":
                    recommendation = decision.recommendation
                    if recommendation is None:
                        raise ValueError("finish decision omitted recommendation")
                    unsupported = set(recommendation.supporting_observations) - called_tools
                    if unsupported:
                        raise ValueError("recommendation cites tools that were not called")
                    steps.append(
                        ShadowAgentStep(
                            step_index=step_index,
                            decision="finish",
                            reasoning=decision.reasoning,
                            latency_ms=latency_ms,
                        )
                    )
                    run = ShadowAgentRun(
                        run_id=run_id,
                        status="completed",
                        recommendation=recommendation,
                        steps=steps,
                        termination_reason="model_finished",
                        used_fallback=False,
                    )
                    await self._repository.save(
                        user_id=user_id, knowledge_base_id=knowledge_base_id, run=run
                    )
                    return run

                if decision.tool_name is None:
                    raise ValueError("tool decision omitted tool_name")
                arguments = ShadowToolArguments.model_validate(decision.arguments)
                tool_result = await self._tools.execute(
                    decision.tool_name,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    arguments=arguments,
                )
                called_tools.add(decision.tool_name)
                observations.append(
                    {"tool_name": decision.tool_name.value, "result": tool_result}
                )
                steps.append(
                    ShadowAgentStep(
                        step_index=step_index,
                        decision="tool",
                        reasoning=decision.reasoning,
                        tool_name=decision.tool_name,
                        validated_arguments=arguments.model_dump(),
                        tool_result=tool_result,
                        latency_ms=latency_ms,
                    )
                )
        except Exception as exc:
            reason = f"agent_error:{type(exc).__name__}"
            run = await self._fallback_run(
                run_id=run_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                steps=steps,
                reason=reason,
            )
            await self._repository.save(
                user_id=user_id, knowledge_base_id=knowledge_base_id, run=run
            )
            return run

        run = await self._fallback_run(
            run_id=run_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            steps=steps,
            reason="max_steps_reached",
        )
        await self._repository.save(
            user_id=user_id, knowledge_base_id=knowledge_base_id, run=run
        )
        return run

    async def _decide(
        self, run_id: str, step_index: int, observations: list[dict[str, object]]
    ) -> ShadowAgentDecision:
        if self._llm is None:
            raise RuntimeError("LLM is unavailable")
        available_tools = [item.value for item in ShadowToolName]
        return await self._llm.generate_structured(
            operation="shadow_training_recommendation",
            messages=(
                Message(
                    role="system",
                    content=(
                        "You are a read-only training recommendation agent. Choose exactly one "
                        "whitelisted tool or finish with a grounded recommendation. Never claim "
                        "to update scores, profiles, review tasks, or interviews. All recommended "
                        "actions require user confirmation."
                    ),
                ),
                Message(
                    role="user",
                    content=json.dumps(
                        {
                            "step": step_index,
                            "max_steps": self.MAX_STEPS,
                            "available_tools": available_tools,
                            "observations": observations,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                ),
            ),
            response_model=ShadowAgentDecision,
            model_policy=ModelPolicy(model=self._default_model, max_retries=1),
            trace_context=TraceContext(
                trace_id=run_id, operation="shadow_training_recommendation"
            ),
        )

    async def _fallback_run(
        self,
        *,
        run_id: str,
        user_id: UUID,
        knowledge_base_id: UUID,
        steps: list[ShadowAgentStep],
        reason: str,
    ) -> ShadowAgentRun:
        result = await self._tools.execute(
            ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            arguments=ShadowToolArguments(limit=1),
        )
        items = result.get("items", [])
        first = items[0] if isinstance(items, list) and items else None
        topic = first.get("knowledge_point") if isinstance(first, dict) else None
        recommendation = ShadowRecommendation(
            recommended_action=(
                ShadowRecommendationAction.FOCUSED_INTERVIEW
                if topic
                else ShadowRecommendationAction.MAINTAIN_CURRENT_PLAN
            ),
            topic=str(topic) if topic else None,
            reason=(
                "按确定性画像规则，优先复习当前掌握度最低的主题。"
                if topic
                else "当前没有可确认的薄弱主题，继续现有训练计划。"
            ),
            supporting_observations=[ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS],
            suggested_parameters={"question_count": 3} if topic else {},
            requires_confirmation=True,
        )
        if len(steps) < self.MAX_STEPS:
            steps.append(
                ShadowAgentStep(
                    step_index=len(steps) + 1,
                    decision="fallback",
                    reasoning="Use deterministic read-only profile recommendation.",
                    tool_name=ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS,
                    validated_arguments={"limit": 1},
                    tool_result=result,
                    latency_ms=0,
                    error_code=reason,
                )
            )
        return ShadowAgentRun(
            run_id=run_id,
            status="fallback",
            recommendation=recommendation,
            steps=steps,
            termination_reason=reason,
            used_fallback=True,
        )

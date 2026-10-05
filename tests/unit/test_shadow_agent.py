from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from agent_mentor.application.shadow_agent_service import ShadowAgentService
from agent_mentor.config import AppEnvironment, Settings
from agent_mentor.domain.shadow_agent import (
    ShadowAgentRun,
    ShadowToolArguments,
    ShadowToolName,
    ShadowTrainingObjective,
)
from agent_mentor.infrastructure.fakes import FakeLLMGateway
from agent_mentor.main import create_app


@dataclass(slots=True)
class FakeReadTools:
    results: dict[ShadowToolName, dict[str, object]]
    calls: list[tuple[ShadowToolName, UUID, UUID, ShadowToolArguments]] = field(
        default_factory=list
    )

    async def execute(
        self,
        tool_name: ShadowToolName,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        arguments: ShadowToolArguments,
    ) -> dict[str, object]:
        self.calls.append((tool_name, user_id, knowledge_base_id, arguments))
        return self.results.get(tool_name, {"items": []})


@dataclass(slots=True)
class RecordingRepository:
    saved: list[tuple[UUID, UUID, ShadowAgentRun]] = field(default_factory=list)

    async def save(
        self, *, user_id: UUID, knowledge_base_id: UUID, run: ShadowAgentRun
    ) -> None:
        self.saved.append((user_id, knowledge_base_id, run))


def decision(**overrides: Any) -> dict[str, object]:
    value: dict[str, object] = {
        "decision": "tool",
        "reasoning": "Inspect a supplementary observation before completing the recommendation.",
        "tool_name": "get_uncovered_topics",
        "arguments": {"limit": 3},
        "topic": None,
        "suggested_parameters": {},
    }
    value.update(overrides)
    return value


def finish_decision(**overrides: Any) -> dict[str, object]:
    value: dict[str, object] = {
        "decision": "finish",
        "reasoning": "The observed topic is sufficient for a user-confirmed recommendation.",
        "tool_name": None,
        "arguments": {},
        "topic": "Redis consistency",
        "suggested_parameters": {"question_count": 3, "difficulty": "medium"},
    }
    value.update(overrides)
    return value


@pytest.mark.asyncio
async def test_shadow_agent_runs_real_tool_loop_and_records_trace() -> None:
    user_id = uuid4()
    knowledge_base_id = uuid4()
    tools = FakeReadTools(
        {
            ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {
                "items": [{"knowledge_point": "Redis consistency", "mastery_score": 0.42}]
            }
        }
    )
    llm = FakeLLMGateway(
        structured_responses=[
            finish_decision(),
        ]
    )
    repository = RecordingRepository()

    run = await ShadowAgentService(
        tools, llm, repository, default_model="test-model"
    ).recommend(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        objective=ShadowTrainingObjective.STRENGTHEN_WEAKNESSES,
    )

    assert run.status == "completed"
    assert not run.used_fallback
    assert run.business_writes == 0
    assert [step.decision for step in run.steps] == ["tool", "finish"]
    assert tools.calls[0][0] == ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS
    assert len(repository.saved) == 1
    assert len(llm.calls) == 1


@pytest.mark.asyncio
async def test_shadow_agent_rejects_invalid_tool_arguments_and_falls_back() -> None:
    tools = FakeReadTools(
        {
            ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {
                "items": [{"knowledge_point": "JVM", "mastery_score": 0.4}]
            }
        }
    )
    llm = FakeLLMGateway(structured_responses=[decision(arguments={"limit": 999})])

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(),
        knowledge_base_id=uuid4(),
        objective=ShadowTrainingObjective.STRENGTHEN_WEAKNESSES,
    )

    assert run.status == "fallback"
    assert run.termination_reason == "agent_error:ValidationError"
    assert run.recommendation.topic == "JVM"
    assert len(tools.calls) == 2


@pytest.mark.asyncio
async def test_shadow_agent_enforces_three_step_budget() -> None:
    tools = FakeReadTools(
        {ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {"items": []}}
    )
    llm = FakeLLMGateway(
        structured_responses=[
            decision(),
            decision(tool_name="get_recent_training_state"),
        ]
    )

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(),
        knowledge_base_id=uuid4(),
        objective=ShadowTrainingObjective.STRENGTHEN_WEAKNESSES,
    )

    assert run.status == "fallback"
    assert run.termination_reason == "max_steps_reached"
    assert len(run.steps) == 3
    assert len(llm.calls) == 2


@pytest.mark.asyncio
async def test_shadow_agent_replaces_hallucinated_topic_with_observed_topic() -> None:
    tools = FakeReadTools(
        {ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {"items": []}}
    )
    llm = FakeLLMGateway(
        structured_responses=[
            finish_decision(topic="An unobserved topic"),
        ]
    )

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(), knowledge_base_id=uuid4()
    )

    assert run.status == "completed"
    assert run.recommendation.recommended_action.value == "maintain_current_plan"
    assert run.recommendation.topic is None


@pytest.mark.asyncio
async def test_missing_llm_uses_deterministic_read_only_fallback() -> None:
    tools = FakeReadTools(
        {ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {"items": []}}
    )

    run = await ShadowAgentService(tools, None).recommend(
        user_id=uuid4(), knowledge_base_id=uuid4()
    )

    assert run.status == "fallback"
    assert run.termination_reason == "llm_unavailable"
    assert run.recommendation.recommended_action == "maintain_current_plan"
    assert run.recommendation.requires_confirmation


@pytest.mark.asyncio
async def test_fallback_respects_read_only_training_objective() -> None:
    tools = FakeReadTools(
        {
            ShadowToolName.GET_UNCOVERED_TOPICS: {
                "items": [{"title": "MCP safety", "status": "uncovered"}]
            }
        }
    )

    run = await ShadowAgentService(tools, None).recommend(
        user_id=uuid4(),
        knowledge_base_id=uuid4(),
        objective=ShadowTrainingObjective.CLOSE_COVERAGE_GAPS,
    )

    assert run.status == "fallback"
    assert run.recommendation.recommended_action.value == "coverage_study"
    assert run.recommendation.topic == "MCP safety"
    assert tools.calls[0][0] == ShadowToolName.GET_UNCOVERED_TOPICS


@pytest.mark.asyncio
async def test_v2_policy_derives_coverage_action_from_coverage_objective() -> None:
    tools = FakeReadTools(
        {
            ShadowToolName.GET_UNCOVERED_TOPICS: {
                "items": [{"title": "Agent safety", "status": "uncovered"}]
            }
        }
    )
    llm = FakeLLMGateway(
        structured_responses=[
            finish_decision(topic="Agent safety", suggested_parameters={"study_minutes": 30})
        ]
    )

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(),
        knowledge_base_id=uuid4(),
        objective=ShadowTrainingObjective.CLOSE_COVERAGE_GAPS,
    )

    assert tools.calls[0][0] == ShadowToolName.GET_UNCOVERED_TOPICS
    assert run.recommendation.recommended_action.value == "coverage_study"
    assert run.recommendation.topic == "Agent safety"


@pytest.mark.asyncio
async def test_v2_can_use_one_dynamic_supplementary_tool_after_policy_primary() -> None:
    tools = FakeReadTools(
        {
            ShadowToolName.GET_RECENT_TRAINING_STATE: {
                "open_review_task_count": 0,
                "open_review_tasks": [],
            },
            ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {
                "items": [{"knowledge_point": "RAG ranking", "mastery_score": 0.43}]
            },
        }
    )
    llm = FakeLLMGateway(
        structured_responses=[
            decision(tool_name="get_weak_knowledge_points"),
            finish_decision(topic="RAG ranking"),
        ]
    )

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(),
        knowledge_base_id=uuid4(),
        objective=ShadowTrainingObjective.BALANCED,
    )

    assert [call[0] for call in tools.calls] == [
        ShadowToolName.GET_RECENT_TRAINING_STATE,
        ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS,
    ]
    assert run.status == "completed"
    assert run.recommendation.recommended_action.value == "focused_interview"
    assert run.recommendation.topic == "RAG ranking"


@pytest.mark.asyncio
async def test_shadow_agent_api_is_default_off() -> None:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/knowledge-bases/{uuid4()}/shadow-agent/recommendation"
        )

    assert response.status_code == 404
    assert response.json()["code"] == "SHADOW_AGENT_DISABLED"

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
        "reasoning": "Need the weakest knowledge point before making a recommendation.",
        "tool_name": "get_weak_knowledge_points",
        "arguments": {"limit": 3},
        "recommendation": None,
    }
    value.update(overrides)
    return value


def recommendation() -> dict[str, object]:
    return {
        "recommended_action": "focused_interview",
        "topic": "Redis consistency",
        "reason": "The weakest observed topic has mastery below the training threshold.",
        "supporting_observations": ["get_weak_knowledge_points"],
        "suggested_parameters": {"question_count": 3, "difficulty": "medium"},
        "requires_confirmation": True,
    }


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
            decision(),
            decision(
                decision="finish",
                tool_name=None,
                arguments={},
                recommendation=recommendation(),
                reasoning="Enough grounded evidence is available.",
            ),
        ]
    )
    repository = RecordingRepository()

    run = await ShadowAgentService(
        tools, llm, repository, default_model="test-model"
    ).recommend(user_id=user_id, knowledge_base_id=knowledge_base_id)

    assert run.status == "completed"
    assert not run.used_fallback
    assert run.business_writes == 0
    assert [step.decision for step in run.steps] == ["tool", "finish"]
    assert tools.calls[0][0] == ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS
    assert len(repository.saved) == 1
    assert len(llm.calls) == 2


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
        user_id=uuid4(), knowledge_base_id=uuid4()
    )

    assert run.status == "fallback"
    assert run.termination_reason == "agent_error:ValidationError"
    assert run.recommendation.topic == "JVM"
    assert len(tools.calls) == 1


@pytest.mark.asyncio
async def test_shadow_agent_enforces_three_step_budget() -> None:
    tools = FakeReadTools(
        {ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {"items": []}}
    )
    llm = FakeLLMGateway(structured_responses=[decision(), decision(), decision()])

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(), knowledge_base_id=uuid4()
    )

    assert run.status == "fallback"
    assert run.termination_reason == "max_steps_reached"
    assert len(run.steps) == 3
    assert len(llm.calls) == 3


@pytest.mark.asyncio
async def test_shadow_agent_cannot_cite_an_observation_it_did_not_call() -> None:
    tools = FakeReadTools(
        {ShadowToolName.GET_WEAK_KNOWLEDGE_POINTS: {"items": []}}
    )
    unsupported = recommendation()
    unsupported["supporting_observations"] = ["get_uncovered_topics"]
    llm = FakeLLMGateway(
        structured_responses=[
            decision(
                decision="finish",
                tool_name=None,
                arguments={},
                recommendation=unsupported,
                reasoning="Finish without evidence.",
            )
        ]
    )

    run = await ShadowAgentService(tools, llm).recommend(
        user_id=uuid4(), knowledge_base_id=uuid4()
    )

    assert run.status == "fallback"
    assert run.termination_reason == "agent_error:ValueError"


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
async def test_shadow_agent_api_is_default_off() -> None:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/knowledge-bases/{uuid4()}/shadow-agent/recommendation"
        )

    assert response.status_code == 404
    assert response.json()["code"] == "SHADOW_AGENT_DISABLED"

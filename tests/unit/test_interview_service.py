from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import Table, UniqueConstraint
from sqlalchemy.dialects import postgresql

from agent_mentor.application.interview_service import (
    QUESTION_ANGLES,
    RECENT_QUESTION_COOLDOWN_LIMIT,
    CoverageFocus,
    FollowUpDecisionOutput,
    InterviewPolicyDecision,
    InterviewQuestionOutput,
    InterviewService,
)
from agent_mentor.domain.interview import Difficulty, QuestionType
from agent_mentor.infrastructure.database.models import (
    InterviewFollowUpModel,
    InterviewSessionModel,
    QuestionCoverageModel,
    UserAnswerModel,
)


class _FakeSession:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing
        self.added: list[object] = []

    async def scalar(self, _statement: object) -> object | None:
        return self.existing

    def add(self, item: object) -> None:
        self.added.append(item)


def test_coverage_gap_sequence_reserves_second_question_for_multi_question_interview() -> None:
    service = InterviewService.__new__(InterviewService)

    assert service._coverage_gap_sequence(3) == 2
    assert service._coverage_gap_sequence(2) == 2
    assert service._coverage_gap_sequence(1) == 1


def test_question_search_text_includes_coverage_focus_when_present() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        topic="RAG",
        difficulty=Difficulty.MEDIUM,
    )
    angle = QUESTION_ANGLES[2]

    query = service._question_search_text(
        cast(Any, interview),
        QuestionType.SCENARIO,
        "引用白名单与证据边界",
        angle,
    )

    assert "RAG" in query
    assert "工程落地" in query
    assert angle.title in query
    assert angle.search_hint in query
    assert "专项训练" in query
    assert "引用白名单与证据边界" in query


def test_coverage_focus_carries_point_id_and_title() -> None:
    point_id = uuid4()
    focus = CoverageFocus(point_id=point_id, title="引用白名单与证据边界")

    assert focus.point_id == point_id
    assert focus.title == "引用白名单与证据边界"


def test_coverage_gap_focus_prioritizes_points_with_more_sources() -> None:
    service = InterviewService.__new__(InterviewService)

    statement = service._coverage_gap_focus_statement(uuid4())
    compiled = str(statement.compile(compile_kwargs={"literal_binds": False})).lower()

    assert "count(" in compiled
    assert "order by count(knowledge_catalog_sources.id) desc" in compiled


def test_recent_question_statement_scopes_to_same_knowledge_base_and_excludes_current() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(id=uuid4(), knowledge_base_id=uuid4())

    statement = service._recent_question_statement(cast(Any, interview))
    compiled_statement = statement.compile(compile_kwargs={"literal_binds": False})
    compiled = str(compiled_statement).lower()

    assert "interview_sessions.knowledge_base_id" in compiled
    assert "interview_sessions.id !=" in compiled or "interview_sessions.id ! =" in compiled
    assert RECENT_QUESTION_COOLDOWN_LIMIT in compiled_statement.params.values()


def test_question_search_text_keeps_original_query_without_coverage_focus() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        topic="LangGraph",
        difficulty=Difficulty.HARD,
    )

    query = service._question_search_text(cast(Any, interview), QuestionType.CONCEPT, None)

    assert "LangGraph" in query
    assert "定义 原理 核心概念" in query
    assert "覆盖盲区" not in query


def test_question_angle_rotates_by_interview_and_sequence() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        topic="RAG",
        difficulty=Difficulty.MEDIUM,
    )

    first = service._question_angle(cast(Any, interview), 1)
    second = service._question_angle(cast(Any, interview), 2)
    third = service._question_angle(cast(Any, interview), 3)

    assert len({first.key, second.key, third.key}) == 3
    assert first in QUESTION_ANGLES
    assert second in QUESTION_ANGLES
    assert third in QUESTION_ANGLES


def test_deterministic_question_text_exposes_angle() -> None:
    service = InterviewService.__new__(InterviewService)
    interview = SimpleNamespace(
        id=uuid4(),
        topic="RAG",
        question_count=3,
    )
    angle = QUESTION_ANGLES[0]

    question = service._question_text(cast(Any, interview), 1, angle, [])

    assert angle.title in question
    assert "易混淆点" in question


def test_question_output_defaults_to_llm_generation_mode() -> None:
    output = InterviewQuestionOutput(
        question_text="请说明 RAG 的核心边界。",
        reference_answer="RAG 需要基于检索证据回答。",
        required_points=["证据边界"],
    )

    assert output.generation_mode == "llm"
    assert output.fallback_reason is None


def test_follow_up_decision_defaults_to_no_follow_up() -> None:
    output = FollowUpDecisionOutput()

    assert output.should_follow_up is False
    assert output.follow_up_question is None
    assert output.generation_mode == "llm"


def test_deterministic_follow_up_triggers_for_short_answer() -> None:
    service = object.__new__(InterviewService)
    question = SimpleNamespace(
        question_text="请说明 RAG 的引用边界。",
        knowledge_points=["引用白名单", "证据不足降级"],
        reference_answer="RAG 回答需要使用引用白名单，并在证据不足时显式降级。",
        rubric={
            "items": [
                {
                    "criterion": "correctness",
                    "required_points": ["引用白名单", "证据不足降级"],
                }
            ]
        },
    )
    answer = SimpleNamespace(answer_text="RAG 就是检索后生成。")

    decision = service._deterministic_follow_up_decision(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, question),
        cast(Any, answer),
    )

    assert decision.should_follow_up is True
    assert decision.follow_up_question is not None
    assert "追问" in decision.follow_up_question
    assert "引用白名单" in decision.expected_points
    assert decision.confidence >= 0.70


def test_deterministic_follow_up_skips_when_answer_covers_rubric() -> None:
    service = object.__new__(InterviewService)
    question = SimpleNamespace(
        question_text="请说明 RAG 的引用边界。",
        knowledge_points=["引用白名单", "证据不足降级"],
        reference_answer="RAG 回答需要使用引用白名单，并在证据不足时显式降级。",
        rubric={
            "items": [
                {
                    "criterion": "correctness",
                    "required_points": ["引用白名单", "证据不足降级"],
                }
            ]
        },
    )
    answer = SimpleNamespace(
        answer_text=(
            "RAG 需要先检索资料，再把允许的 chunk 作为引用白名单传给生成阶段。"
            "如果引用白名单里没有证据，答案应该显式降级，说明证据不足，不能硬答。"
            "工程上还要记录检索诊断和引用校验结果，方便后续回归。"
        )
    )

    decision = service._deterministic_follow_up_decision(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, question),
        cast(Any, answer),
    )

    assert decision.should_follow_up is False
    assert "不追加追问" in decision.reason


@pytest.mark.asyncio
async def test_follow_up_decision_is_suppressed_for_substantive_answer() -> None:
    service = object.__new__(InterviewService)
    service._llm = None  # pyright: ignore[reportPrivateUsage]
    interview = SimpleNamespace(topic="RAG", question_count=3)
    question = SimpleNamespace(
        question_text="请说明 RAG 的引用边界。",
        sequence=1,
        knowledge_points=["引用白名单", "证据不足降级"],
        reference_answer="RAG 回答需要使用引用白名单，并在证据不足时显式降级。",
        rubric={
            "items": [
                {
                    "criterion": "correctness",
                    "required_points": ["引用白名单", "证据不足降级"],
                }
            ]
        },
    )
    answer = SimpleNamespace(
        answer_text=(
            "我会先基于检索片段回答，并把允许引用的 chunk 作为引用白名单传给生成阶段。"
            "如果检索证据不足，就明确说明无法根据资料确认，而不是硬答。"
            "工程上要记录检索诊断、引用校验、置信度和降级原因，方便回归。"
        )
    )

    decision = await service._generate_follow_up_decision(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        cast(Any, question),
        cast(Any, answer),
    )

    assert decision.should_follow_up is False
    assert decision.generation_mode == "deterministic_gate"


def test_question_prompt_includes_recent_history_cooldown() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(
        topic="RAG",
        difficulty="medium",
        question_count=3,
    )

    prompt = service._question_prompt(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        1,
        QuestionType.CONCEPT,
        QUESTION_ANGLES[0],
        [],
        ["本轮题目"],
        ["历史题目 A", "历史题目 B"],
        None,
        "引用白名单",
        InterviewPolicyDecision(
            next_action="ask_cooldown_aware_question",
            reason="同知识库近期已经出现相似训练题，本题需要切换角度以提升题目多样性。",
            target_topic="RAG · 概念边界",
            difficulty="medium",
            deterministic_gate="历史题冷却由应用层计算，LLM 不能绕过相似度检测。",
        ),
    )

    assert "同知识库最近历史题目" in prompt
    assert "历史题目 A" in prompt
    assert "避开最近历史题目的核心问法" in prompt
    assert "轻量面试官策略" in prompt
    assert "画像推荐考点：引用白名单" in prompt
    assert "ask_cooldown_aware_question" in prompt
    assert "LLM 不能绕过相似度检测" in prompt


def test_question_policy_prioritizes_coverage_gap() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(topic="RAG", difficulty=Difficulty.MEDIUM)

    policy = service._question_policy(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        sequence=2,
        coverage_focus="引用白名单",
        profile_focus="RAG 检索增强生成",
        question_angle=QUESTION_ANGLES[0],
        recent_questions=[],
    )

    assert policy.next_action == "ask_coverage_gap_question"
    assert policy.target_topic == "引用白名单"
    assert "查漏" in policy.reason
    assert "InterviewService" in policy.deterministic_gate


def test_question_policy_uses_cooldown_when_recent_questions_exist() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(topic="RAG", difficulty=Difficulty.MEDIUM)

    policy = service._question_policy(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        sequence=3,
        coverage_focus=None,
        profile_focus=None,
        question_angle=QUESTION_ANGLES[1],
        recent_questions=["历史题目"],
    )

    assert policy.next_action == "ask_cooldown_aware_question"
    assert "题目多样性" in policy.reason
    assert "相似度检测" in policy.deterministic_gate


def test_question_policy_defaults_to_planned_question() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(topic="LangGraph", difficulty=Difficulty.HARD)

    policy = service._question_policy(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        sequence=1,
        coverage_focus=None,
        profile_focus=None,
        question_angle=QUESTION_ANGLES[2],
        recent_questions=[],
    )

    assert policy.next_action == "ask_planned_question"
    assert policy.target_topic == "LangGraph · 异常与降级"
    assert "状态机" in policy.deterministic_gate


def test_question_policy_uses_profile_focus_before_cooldown() -> None:
    service = object.__new__(InterviewService)
    interview = SimpleNamespace(topic="RAG", difficulty=Difficulty.MEDIUM)

    policy = service._question_policy(  # pyright: ignore[reportPrivateUsage, reportArgumentType]
        cast(Any, interview),
        sequence=1,
        coverage_focus=None,
        profile_focus="引用白名单",
        question_angle=QUESTION_ANGLES[0],
        recent_questions=["历史题目"],
    )

    assert policy.next_action == "ask_profile_targeted_question"
    assert policy.target_topic == "引用白名单"
    assert "能力画像" in policy.reason


def test_user_answer_idempotency_is_enforced_by_database_constraint() -> None:
    table = cast(Table, UserAnswerModel.__table__)
    constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == "uq_answer_idempotency"
        and {column.name for column in constraint.columns}
        == {"question_id", "idempotency_key"}
        for constraint in constraints
    )


def test_answer_submission_locks_interview_session_before_state_advance() -> None:
    service = InterviewService.__new__(InterviewService)
    session_id = uuid4()

    statement = service._session_for_update_statement(  # pyright: ignore[reportPrivateUsage]
        session_id
    )
    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )

    assert InterviewSessionModel.__tablename__ in compiled
    assert "FOR UPDATE" in compiled


def test_follow_up_is_limited_to_one_per_question_by_database_constraint() -> None:
    table = cast(Table, InterviewFollowUpModel.__table__)
    constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == "uq_followup_question_once"
        and {column.name for column in constraint.columns} == {"question_id"}
        for constraint in constraints
    )


@pytest.mark.asyncio
async def test_ensure_question_coverage_adds_missing_focus_point() -> None:
    service = InterviewService.__new__(InterviewService)
    db = _FakeSession()
    question_id = uuid4()
    knowledge_point_id = uuid4()

    await service._ensure_question_coverage(
        cast(Any, db),
        question_id=question_id,
        knowledge_point_id=knowledge_point_id,
    )

    assert len(db.added) == 1
    coverage = db.added[0]
    assert isinstance(coverage, QuestionCoverageModel)
    assert coverage.question_id == question_id
    assert coverage.knowledge_point_id == knowledge_point_id


@pytest.mark.asyncio
async def test_ensure_question_coverage_keeps_existing_focus_point() -> None:
    service = InterviewService.__new__(InterviewService)
    db = _FakeSession(existing=uuid4())

    await service._ensure_question_coverage(
        cast(Any, db),
        question_id=uuid4(),
        knowledge_point_id=uuid4(),
    )

    assert db.added == []

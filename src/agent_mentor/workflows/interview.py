from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkflowNodeSpec:
    name: str
    event: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class InterviewWorkflowState:
    session_id: UUID
    thread_id: str
    current_node: str
    current_question_index: int
    question_count: int
    waiting_for_answer: bool

    def checkpoint(self) -> dict[str, object]:
        return {
            "session_id": str(self.session_id),
            "thread_id": self.thread_id,
            "current_node": self.current_node,
            "current_question_index": self.current_question_index,
            "question_count": self.question_count,
            "waiting_for_answer": self.waiting_for_answer,
        }


WORKFLOW_NODE_SPECS: tuple[WorkflowNodeSpec, ...] = (
    WorkflowNodeSpec("load_profile", "workflow.started", "加载画像", "读取本机用户画像和薄弱点。"),
    WorkflowNodeSpec("plan_interview", "workflow.planned", "规划面试", "确定主题、难度和题量。"),
    WorkflowNodeSpec(
        "generate_question",
        "question.generated",
        "生成题目",
        "结合检索片段生成题目、参考答案和 Rubric。",
    ),
    WorkflowNodeSpec(
        "wait_for_answer",
        "workflow.interrupted",
        "等待回答",
        "工作流暂停，等待用户输入。",
    ),
    WorkflowNodeSpec("persist_answer", "answer.persisted", "保存答案", "使用幂等键保存用户答案。"),
    WorkflowNodeSpec(
        "generate_follow_up",
        "follow_up.generated",
        "生成追问",
        "基于用户回答决定是否生成一次受控追问。",
    ),
    WorkflowNodeSpec(
        "persist_follow_up",
        "follow_up.persisted",
        "保存追问回答",
        "使用幂等键保存追问答案，然后回到确定性状态机推进。",
    ),
    WorkflowNodeSpec(
        "advance_question",
        "workflow.advanced",
        "推进题目",
        "进入下一题生成与等待节点。",
    ),
    WorkflowNodeSpec(
        "finish_interview",
        "workflow.completed",
        "完成面试",
        "所有题目已回答，进入评分报告阶段。",
    ),
)
WORKFLOW_NODE_BY_NAME = {spec.name: spec for spec in WORKFLOW_NODE_SPECS}


def workflow_node_spec(node: str) -> WorkflowNodeSpec:
    return WORKFLOW_NODE_BY_NAME.get(
        node,
        WorkflowNodeSpec(node, "workflow.checkpoint_saved", node, "自定义工作流节点。"),
    )


def checkpoint_summary(state: dict[str, object]) -> tuple[str, str]:
    node = str(state.get("current_node", "unknown"))
    current = state.get("current_question_index", 0)
    total = state.get("question_count", 0)
    waiting = bool(state.get("waiting_for_answer", False))
    input_summary = f"question_index={current}/{total}"
    output_summary = (
        "等待用户回答，可刷新后恢复" if waiting else workflow_node_spec(node).description
    )
    return input_summary, output_summary


def load_profile(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="load_profile",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def plan_interview(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="plan_interview",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def generate_question(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="generate_question",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def wait_for_answer(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="wait_for_answer",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=True,
    )


def persist_answer(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="persist_answer",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def advance_question(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="advance_question",
        current_question_index=state.current_question_index + 1,
        question_count=state.question_count,
        waiting_for_answer=False,
    )


def finish_interview(state: InterviewWorkflowState) -> InterviewWorkflowState:
    return InterviewWorkflowState(
        session_id=state.session_id,
        thread_id=state.thread_id,
        current_node="finish_interview",
        current_question_index=state.current_question_index,
        question_count=state.question_count,
        waiting_for_answer=False,
    )

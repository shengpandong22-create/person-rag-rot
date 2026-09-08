from __future__ import annotations

from agent_mentor.application.demo_readiness_service import DemoReadinessService, ReadinessCheck


def test_demo_readiness_status_thresholds() -> None:
    service = object.__new__(DemoReadinessService)

    assert service._status(100) == "ready"  # pyright: ignore[reportPrivateUsage]
    assert service._status(50) == "partial"  # pyright: ignore[reportPrivateUsage]
    assert service._status(49) == "not_ready"  # pyright: ignore[reportPrivateUsage]


def test_demo_readiness_next_action_points_to_first_missing_step() -> None:
    service = object.__new__(DemoReadinessService)
    checks = (
        ReadinessCheck("knowledge_base", "知识库", True, "已创建 1 个知识库"),
        ReadinessCheck("ready_documents", "可检索资料", False, "READY 文档 0 份"),
        ReadinessCheck("workflow_trace", "工作流轨迹", False, "checkpoint 0 条"),
    )

    action = service._next_action(checks)  # pyright: ignore[reportPrivateUsage]

    assert action == "上传至少一份学习资料并等待索引完成。"


def test_demo_readiness_signals_explain_runtime_and_engineering_boundaries() -> None:
    service = object.__new__(DemoReadinessService)

    signals = service._signals(  # pyright: ignore[reportPrivateUsage]
        ready_document_count=2,
        completed_interview_count=3,
        checkpoint_count=9,
    )
    boundaries = service._enterprise_boundaries()  # pyright: ignore[reportPrivateUsage]

    assert [signal.key for signal in signals] == [
        "runtime_scope",
        "rag_trust",
        "workflow_control",
        "interview_quality",
    ]
    assert "READY 文档 2 份" in signals[1].detail
    assert "checkpoint 9 条" in signals[2].detail
    assert any("多租户" in item for item in boundaries)

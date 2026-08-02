BEGIN;

DO $repair$
DECLARE
    target_event_count integer;
    all_agent_event_count integer;
    agent_profile_count integer;
    agent_error_count integer;
    agent_task_count integer;
BEGIN
    SELECT count(*) INTO target_event_count
    FROM profile_update_events pe
    JOIN evaluations e ON e.id = pe.evaluation_id
    JOIN interview_questions q ON q.id = e.question_id
    WHERE q.session_id IN (
        'aa793ea4-2f80-4ed9-aa02-7111a7b0ec73',
        '706108cb-1728-4b77-b01b-6bc67bf4b678'
    )
      AND pe.changes->>'topic' = 'agent_engineering';

    SELECT count(*) INTO all_agent_event_count
    FROM profile_update_events
    WHERE changes->>'topic' = 'agent_engineering'
      AND applied IS TRUE;

    SELECT count(*) INTO agent_profile_count
    FROM ability_profiles
    WHERE topic_key = 'agent_engineering';

    SELECT count(*) INTO agent_error_count
    FROM error_patterns
    WHERE topic_key = 'agent_engineering';

    SELECT count(*) INTO agent_task_count
    FROM review_tasks
    WHERE topic_key = 'agent_engineering';

    IF target_event_count <> 6 OR all_agent_event_count <> 6 THEN
        RAISE EXCEPTION 'Routing repair stopped: expected exactly six isolated target events.';
    END IF;
    IF agent_profile_count <> 3 OR agent_error_count <> 0 OR agent_task_count <> 0 THEN
        RAISE EXCEPTION 'Routing repair stopped: derived profile state is not isolated.';
    END IF;
END
$repair$;

UPDATE profile_update_events pe
SET applied = FALSE,
    decision = 'routing_mismatch',
    changes = pe.changes || jsonb_build_object(
        'repair_reason',
        '专项训练丢失父主题，且实际题目未验证 RAG 评估与可靠性；撤销错误画像更新。',
        'repaired_at',
        '2026-08-02T00:00:00Z'
    )
FROM evaluations e
JOIN interview_questions q ON q.id = e.question_id
WHERE pe.evaluation_id = e.id
  AND q.session_id IN (
      'aa793ea4-2f80-4ed9-aa02-7111a7b0ec73',
      '706108cb-1728-4b77-b01b-6bc67bf4b678'
  );

DELETE FROM ability_profiles
WHERE topic_key = 'agent_engineering';

UPDATE interview_sessions
SET topic = '评估与可靠性（历史路由异常，不计入画像）'
WHERE id IN (
    'aa793ea4-2f80-4ed9-aa02-7111a7b0ec73',
    '706108cb-1728-4b77-b01b-6bc67bf4b678'
)
  AND topic = '评估与可靠性';

COMMIT;

"""Validate complete status-event chains in SQL, never invent legacy timestamps."""

from sqlalchemy import text

# JSON keys are trusted schema names, values remain untrusted historical data.
# Tied status timestamps are excluded because UUID ordering is not event ordering.
RESOLUTION_SQL = """
WITH cohort AS (
 SELECT id, created_at, status FROM tickets
 WHERE workspace_id=:workspace AND created_at>=:start AND created_at<:end
 AND created_at<=:observed AND status IN ('resolved','closed')
), events AS (
 SELECT a.ticket_id, a.created_at, a.details->>'from' AS old_status,
        a.details->>'to' AS new_status,
        lag(a.details->>'to', 1, 'open') OVER
          (PARTITION BY a.ticket_id ORDER BY a.created_at,a.id) AS expected_status,
        count(*) OVER (PARTITION BY a.ticket_id,a.created_at) AS tied,
        row_number() OVER (PARTITION BY a.ticket_id ORDER BY a.created_at DESC,a.id DESC) AS last
 FROM ticket_activities a JOIN cohort t ON t.id=a.ticket_id
 WHERE a.workspace_id=:workspace AND a.action='status_changed'
), histories AS (
 SELECT t.id, t.created_at, t.status,
        max(e.created_at) FILTER (WHERE e.new_status='resolved') AS resolved_at,
        max(e.created_at) FILTER (WHERE e.new_status IN
          ('open','in_progress','waiting_for_approval')) AS reopened_at,
        min(e.created_at) AS first_status_at,
        (SELECT min(c.created_at) FROM ticket_activities c WHERE c.workspace_id=:workspace
           AND c.ticket_id=t.id AND c.action='created') AS creation_event_at,
        bool_and(COALESCE(e.old_status=e.expected_status
          AND e.old_status IN ('open','in_progress','waiting_for_approval','resolved','closed')
          AND e.new_status IN ('open','in_progress','waiting_for_approval','resolved','closed')
          AND e.old_status<>e.new_status AND e.tied=1
          AND e.created_at>=t.created_at AND e.created_at<=:observed, false)) AS valid,
        max(e.new_status) FILTER (WHERE e.last=1) AS last_status,
        (SELECT count(*) FROM ticket_activities c WHERE c.workspace_id=:workspace
           AND c.ticket_id=t.id AND c.action='created') AS creation_events
 FROM cohort t LEFT JOIN events e ON e.ticket_id=t.id
 GROUP BY t.id,t.created_at,t.status
), eligible AS (
 SELECT *, extract(epoch FROM resolved_at-created_at) AS seconds
 FROM histories WHERE valid AND creation_events=1 AND last_status=status::text
 AND resolved_at IS NOT NULL AND creation_event_at>=created_at
 AND creation_event_at<=first_status_at
 AND (reopened_at IS NULL OR resolved_at>=reopened_at)
)
SELECT count(*) AS samples, avg(seconds) AS average,
 percentile_cont(0.5) WITHIN GROUP (ORDER BY seconds) AS median,
 (SELECT count(*) FROM histories)-(SELECT count(*) FROM eligible) AS excluded,
 COALESCE((SELECT json_agg(x) FROM (
   SELECT (resolved_at AT TIME ZONE 'UTC')::date AS day, count(*) AS count
   FROM eligible WHERE resolved_at>=:start AND resolved_at<:end GROUP BY 1 ORDER BY 1
 ) x), '[]'::json) AS trend
FROM eligible
"""


def resolution(db, workspace, start, end, observed):
    return (
        db.execute(
            text(RESOLUTION_SQL), dict(workspace=workspace, start=start, end=end, observed=observed)
        )
        .mappings()
        .one()
    )

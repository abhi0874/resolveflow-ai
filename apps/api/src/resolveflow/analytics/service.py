"""One read-only snapshot per authorized dashboard response."""

from sqlalchemy import text

from resolveflow.analytics.queries import overview
from resolveflow.services.authorization import Permission, access


def report(db, user, workspace_id, dates):
    # Authentication has already read the session. Begin a fresh consistent snapshot,
    # then recheck current workspace permissions inside it.
    db.rollback()
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    db.execute(text("SET LOCAL statement_timeout = '1500ms'"))
    access(db, user, workspace_id, Permission.ANALYTICS)
    return overview(db, workspace_id, dates)

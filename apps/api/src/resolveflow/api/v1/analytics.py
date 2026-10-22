import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from resolveflow.analytics.schemas import DateRange, Overview
from resolveflow.analytics.service import report as analytics_report
from resolveflow.services.auth import DB, CurrentUser

router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["analytics"])


@router.get("/overview", response_model=Overview)
def report(
    request: Request,
    workspace_id: uuid.UUID,
    dates: Annotated[DateRange, Query()],
    db: DB,
    user: CurrentUser,
):
    if any(len(request.query_params.getlist(key)) > 1 for key in request.query_params):
        raise HTTPException(422)
    return analytics_report(db, user, workspace_id, dates)

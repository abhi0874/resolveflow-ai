from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["resolveflow-api"] = "resolveflow-api"


class InfoResponse(BaseModel):
    name: str
    version: str
    description: str


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    service: Literal["resolveflow-api"] = "resolveflow-api"
    database: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail

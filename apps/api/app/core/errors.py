from typing import Any

from pydantic import BaseModel, Field


class AppError(Exception):
    """Domain error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None
    requestId: str = Field(..., serialization_alias="requestId")

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    error: ErrorBody

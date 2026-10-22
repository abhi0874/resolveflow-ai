import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from resolveflow.db.models import MembershipRole


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class LoginInput(InputModel):
    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RegisterInput(LoginInput):
    password: SecretStr = Field(min_length=15, max_length=128)
    password_confirmation: SecretStr = Field(min_length=15, max_length=128)

    @model_validator(mode="after")
    def matching_passwords(self):
        if self.password != self.password_confirmation:
            raise ValueError("Passwords must match")
        if not self.password.get_secret_value().strip():
            raise ValueError("Password cannot be blank")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    created_at: datetime
    email_verified: bool = False


class CsrfResponse(BaseModel):
    csrf_token: str


class WorkspaceInput(InputModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError("Workspace name cannot be blank")
        return value.strip()


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: MembershipRole
    permissions: list[str]


class MemberInput(InputModel):
    email: EmailStr = Field(max_length=320)
    role: MembershipRole = MembershipRole.VIEWER

    @field_validator("email", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class RoleInput(InputModel):
    role: MembershipRole


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: MembershipRole

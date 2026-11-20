import unicodedata

from pydantic import BaseModel, Field, SecretStr, field_validator

from resolveflow.schemas.auth import (
    AcceptInvitationInput,
    IdentityEmailInput,
    InputModel,
    NewPasswordInput,
)


class ProfileUpdate(InputModel):
    display_name: str = Field(max_length=80)
    avatar_pixels: str | None = Field(default=None, min_length=12544, max_length=12544)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if any(unicodedata.category(char) in {"Cc", "Cs", "Cf"} for char in value):
            raise ValueError("Invalid display name")
        return value.strip()


class ProfileResponse(BaseModel):
    display_name: str | None
    avatar: str | None
    email: str
    email_verified: bool
    password_enabled: bool
    google_linked: bool


class EmailChange(IdentityEmailInput):
    current_password: SecretStr | None = Field(default=None, min_length=1, max_length=128)


class PasswordChange(NewPasswordInput):
    current_password: SecretStr = Field(min_length=1, max_length=128)


class EmailProof(AcceptInvitationInput):
    action: str = Field(pattern=r"^(approve|confirm)$")

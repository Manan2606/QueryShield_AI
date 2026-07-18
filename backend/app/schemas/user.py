from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(char.islower() for char in value):
            raise ValueError("Password must include a lowercase letter")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include an uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a number")
        if not any(not char.isalnum() for char in value):
            raise ValueError("Password must include a symbol")
        return value


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool

    model_config = {"from_attributes": True}

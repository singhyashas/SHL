from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        return cleaned


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[Message] = Field(..., min_length=1)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    recommendations: list[Recommendation]
    end_of_conversation: bool


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]

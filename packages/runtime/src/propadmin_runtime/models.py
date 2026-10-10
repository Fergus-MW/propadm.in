"""The public input schema is shared by REST and inline MCP tools."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    password: str = Field(min_length=1, max_length=1000)


class EntityCreate(Input):
    type: str
    name: str = Field(min_length=1, max_length=500)
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    fields: dict[str, Any] = Field(default_factory=dict)
    external_ids: dict[str, str] = Field(default_factory=dict)
    reason: str = "Created in admin panel"


class EntityUpdate(Input):
    version: int = Field(ge=1)
    name: str | None = None
    description: str | None = None
    description_pinned: bool | None = None
    aliases: list[str] | None = None
    fields: dict[str, Any] | None = None
    reason: str = "Updated in admin panel"


class Merge(Input):
    target_id: str
    version: int = Field(ge=1)
    target_version: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1)


class Search(Input):
    query: str = Field(min_length=1, max_length=4000)
    types: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=100)
    expand: bool = True


class Upload(Input):
    filename: str = Field(min_length=1, max_length=500)
    mime: str = "text/plain"
    origin: str = "upload"
    text: str | None = Field(default=None, max_length=2_000_000)
    content_base64: str | None = Field(default=None, max_length=7_000_000)
    source_type: str | None = None
    parsed: bool = False
    records: list[dict[str, Any]] = Field(default_factory=list)
    extractor_version: str | None = None


class Rule(Input):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    relation: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source_type: str
    target_type: str
    kind: Literal[
        "field_match", "field_overlap", "expression", "co_occurrence", "similarity", "llm_judge"
    ]
    params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = False
    version: int | None = None
    prompt: str = ""


class Compile(Input):
    prompt: str = Field(min_length=1, max_length=8000)

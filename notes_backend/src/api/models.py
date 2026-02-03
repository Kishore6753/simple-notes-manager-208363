from typing import Optional

from pydantic import BaseModel, Field, field_validator


class NoteBase(BaseModel):
    """Shared fields for note create/update."""

    title: str = Field(..., min_length=1, max_length=200, description="Short title for the note (1-200 chars).")
    content: str = Field(..., min_length=1, max_length=10_000, description="Note body content (1-10,000 chars).")

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v

    @field_validator("content")
    @classmethod
    def _strip_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content must not be blank")
        return v


class NoteCreate(NoteBase):
    """Payload to create a new note."""


class NoteUpdate(BaseModel):
    """Payload to update an existing note (partial update)."""

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=200, description="Updated title for the note (1-200 chars)."
    )
    content: Optional[str] = Field(
        default=None, min_length=1, max_length=10_000, description="Updated note body content (1-10,000 chars)."
    )

    @field_validator("title")
    @classmethod
    def _strip_optional_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v

    @field_validator("content")
    @classmethod
    def _strip_optional_content(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("content must not be blank")
        return v

    @field_validator("content", mode="after")
    @classmethod
    def _at_least_one_field_present(cls, v, info):
        # This validator is a trick to ensure at least one field is present; we check on model level below.
        return v

    def model_post_init(self, __context) -> None:
        if self.title is None and self.content is None:
            raise ValueError("At least one of 'title' or 'content' must be provided.")


class Note(NoteBase):
    """A persisted note entity."""

    id: int = Field(..., description="Unique numeric identifier of the note.")
    created_at: str = Field(..., description="UTC ISO timestamp when the note was created.")
    updated_at: str = Field(..., description="UTC ISO timestamp when the note was last updated.")

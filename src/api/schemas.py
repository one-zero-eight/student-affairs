"""
Lean Pydantic models for request bodies and responses exposed to portal clients.
Raw Omnidesk responses (dict) are passed through where reshaping isn't needed.
"""

from typing import Any, Optional

from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────────────────────

class CreateCaseRequest(BaseModel):
    subject: str
    content: str
    content_html: Optional[str] = None
    user_full_name: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str
    content_html: Optional[str] = None


# ── Responses (pass-through shapes matching Omnidesk) ─────────────────────────

class Attachment(BaseModel):
    file_id: int
    file_name: str
    file_size: int
    mime_type: str
    url: str


class CaseSummary(BaseModel):
    case_id: int
    case_number: str
    subject: str
    status: str
    priority: str
    channel: str
    created_at: str
    updated_at: str
    user_id: int


class Message(BaseModel):
    message_id: int
    user_id: int
    staff_id: int
    content: str
    content_html: str
    attachments: list[Attachment]
    note: bool
    created_at: str
    full_name: Optional[str] = None


class CaseListResponse(BaseModel):
    cases: list[CaseSummary]
    total_count: int


class MessagesResponse(BaseModel):
    messages: list[Message]
    total_count: int


class CreateCaseResponse(BaseModel):
    case: CaseSummary


class SendMessageResponse(BaseModel):
    message: Message


class OmnideskRaw(BaseModel):
    """Generic pass-through for Omnidesk responses we don't reshape."""
    data: Any

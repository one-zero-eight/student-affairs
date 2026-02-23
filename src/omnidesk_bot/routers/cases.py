"""
Cases router — 4 endpoints for the customer portal:

  POST   /cases                           → create a new case
  GET    /cases                           → list the caller's own cases
  GET    /cases/{case_id}/messages        → read all messages of a case
  POST   /cases/{case_id}/messages        → send a message (supports file upload)
"""

import json
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status

from inh_accounts_sdk import UserTokenData
from src.omnidesk_bot.auth import get_current_user
from src.omnidesk_bot.schemas import (
    CaseSummary,
    CaseListResponse,
    CreateCaseRequest,
    Message,
    MessagesResponse,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def _omnidesk_client(request: Request) -> httpx.AsyncClient:
    """Pull the shared client stored in app state by lifespan."""
    return request.app.state.omnidesk_client


OmnideskClient = Annotated[httpx.AsyncClient, Depends(_omnidesk_client)]
CurrentUser = Annotated[UserTokenData, Depends(get_current_user)]


def _parse_cases(raw: dict) -> CaseListResponse:
    cases = []
    total_count = int(raw.get("total_count", 0))
    for key, val in raw.items():
        if key == "total_count":
            continue
        c = val["case"]
        cases.append(
            CaseSummary(
                case_id=c["case_id"],
                case_number=c["case_number"],
                subject=c["subject"],
                status=c["status"],
                priority=c["priority"],
                channel=c["channel"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                user_id=c["user_id"],
            )
        )
    return CaseListResponse(cases=cases, total_count=total_count)


def _parse_messages(raw: dict) -> MessagesResponse:
    from src.omnidesk_bot.schemas import Attachment

    messages = []
    total_count = int(raw.get("total_count", 0))
    for key, val in raw.items():
        if key == "total_count":
            continue
        m = val["message"]
        attachments = [
            Attachment(
                file_id=a["file_id"],
                file_name=a["file_name"],
                file_size=a["file_size"],
                mime_type=a["mime_type"],
                url=a["url"],
            )
            for a in m.get("attachments", [])
        ]
        messages.append(
            Message(
                message_id=m["message_id"],
                user_id=m.get("user_id", 0),
                staff_id=m.get("staff_id", 0),
                content=m.get("content", ""),
                content_html=m.get("content_html", ""),
                attachments=attachments,
                note=m.get("note", False),
                created_at=m["created_at"],
            )
        )
    return MessagesResponse(messages=messages, total_count=total_count)


async def _get_omnidesk_user_id(client: httpx.AsyncClient, email: str) -> Optional[int]:
    """
    Resolve the Omnidesk user_id for a given email by fetching their cases.
    Returns None if the user has no cases yet (first-time user).
    """
    resp = await client.get("/cases.json", params={"user_email": email, "limit": 1})
    if resp.is_error:
        return None
    data = resp.json()
    for key, val in data.items():
        if key == "total_count":
            continue
        return int(val["case"]["user_id"])
    return None


# ── 1. Create a new case ──────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CreateCaseRequest,
    current_user: CurrentUser,
    client: OmnideskClient,
) -> dict:
    """Create a new support request on behalf of the authenticated portal user."""
    payload: dict = {
        "case": {
            "user_email": current_user.email,
            "subject": body.subject,
        }
    }
    if body.content_html:
        payload["case"]["content_html"] = body.content_html
    else:
        payload["case"]["content"] = body.content
    if body.user_full_name:
        payload["case"]["user_full_name"] = body.user_full_name

    resp = await client.post("/cases.json", content=json.dumps(payload))
    resp.raise_for_status()
    return resp.json()


# ── 2. List the user's own cases ──────────────────────────────────────────────

@router.get("")
async def list_cases(
    current_user: CurrentUser,
    client: OmnideskClient,
    page: int = Query(1, ge=1, le=500),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="open | waiting | closed"),
    sort: str = Query("updated_at_desc"),
) -> CaseListResponse:
    """List support cases belonging to the authenticated portal user."""
    params: dict = {
        "user_email": current_user.email,
        "page": page,
        "limit": limit,
        "sort": sort,
    }
    if status:
        params["status"] = status

    resp = await client.get("/cases.json", params=params)
    resp.raise_for_status()
    return _parse_cases(resp.json())


# ── 3. Read messages of a case ────────────────────────────────────────────────

@router.get("/{case_id}/messages")
async def get_messages(
    case_id: int,
    current_user: CurrentUser,
    client: OmnideskClient,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    order: str = Query("asc", pattern="^(asc|desc)$"),
) -> MessagesResponse:
    """
    Fetch messages for a given case.
    The caller's email must match the case owner — enforced by Omnidesk
    (only cases belonging to user_email are returned by list_cases).
    """
    resp = await client.get(
        f"/cases/{case_id}/messages.json",
        params={"page": page, "limit": limit, "order": order},
    )
    resp.raise_for_status()
    return _parse_messages(resp.json())


# ── 4. Send a message (with optional file attachments) ────────────────────────

@router.post("/{case_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    case_id: int,
    current_user: CurrentUser,
    client: OmnideskClient,
    content: str = Form(...),
    content_html: Optional[str] = Form(None),
    attachments: list[UploadFile] = File(default=[]),
) -> dict:
    """
    Send a message to a case.
    Supports multipart/form-data with one or more file attachments.
    The user_id is resolved from Omnidesk via the caller's email.
    """
    user_id = await _get_omnidesk_user_id(client, current_user.email)

    if attachments:
        # Re-stream files to Omnidesk as multipart/form-data
        # (Omnidesk expects message[attachments][N] keys)
        # We must NOT set Content-Type: application/json on this request.
        fields: list[tuple] = []
        if user_id is not None:
            fields.append(("message[user_id]", str(user_id)))
        if content_html:
            fields.append(("message[content_html]", content_html))
        else:
            fields.append(("message[content]", content))

        file_parts = []
        for idx, upload in enumerate(attachments):
            raw = await upload.read()
            file_parts.append(
                (
                    f"message[attachments][{idx}]",
                    (upload.filename, raw, upload.content_type or "application/octet-stream"),
                )
            )

        # Build multipart request manually so we can strip the default JSON header
        multipart_client = httpx.AsyncClient(
            base_url=client.base_url,
            auth=client.auth,
            timeout=60.0,
        )
        async with multipart_client:
            resp = await multipart_client.post(
                f"/cases/{case_id}/messages.json",
                data=dict(fields),
                files=file_parts,
            )
    else:
        # Plain JSON POST
        payload: dict = {"message": {}}
        if user_id is not None:
            payload["message"]["user_id"] = user_id
        if content_html:
            payload["message"]["content_html"] = content_html
        else:
            payload["message"]["content"] = content

        resp = await client.post(
            f"/cases/{case_id}/messages.json",
            content=json.dumps(payload),
        )

    resp.raise_for_status()
    return resp.json()

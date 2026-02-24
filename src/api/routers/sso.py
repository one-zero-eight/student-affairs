import datetime
import urllib.parse
from typing import Annotated

import httpx
from authlib.jose import jwt
from fastapi import APIRouter, Depends

from src.api.auth import get_current_user

from src.config import settings
from src.inh_accounts_sdk import UserTokenData, inh_accounts

router = APIRouter(prefix="/sso", tags=["sso"])
CurrentUser = Annotated[UserTokenData, Depends(get_current_user)]


@router.post("/generate-link")
async def generate_signin_link(
    current_user: CurrentUser,
    return_to: str | None = None,
) -> str:
    """
    Create a link for user authentication.
    https://support.omnidesk.ru/knowledge_base/item/54180?b_from_widget=1%3Fsid%3D2
    """

    # Get user info
    accounts_user = await inh_accounts.get_user(innohassle_id=current_user.innohassle_id)

    # Build JWT
    issued_at = datetime.datetime.now(datetime.UTC)
    expire = issued_at + datetime.timedelta(minutes=30)
    payload: dict = {
        "iat": issued_at,
        "exp": expire,
        "email": current_user.email,
        "name": accounts_user.innopolis_info.name,
        "external_id": current_user.innohassle_id,  # Should we add this?
    }
    encoded_jwt = jwt.encode({"alg": "HS256"}, payload, settings.omnidesk.jwt_marker.get_secret_value())

    # Build endpoint for getting redirect link
    query_params = {
        "jwt": encoded_jwt,
        "return_to": return_to or settings.omnidesk.default_redirect_to,
    }
    endpoint = f"{settings.omnidesk.jwt_access_base_url}?{urllib.parse.urlencode(query_params)}"

    # Receive redirect link
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(endpoint)
        resp.raise_for_status()
        redirect_url = resp.text
        return redirect_url

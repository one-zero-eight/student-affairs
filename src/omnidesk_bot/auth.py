from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from inh_accounts_sdk import UserTokenData, inh_accounts

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserTokenData:
    """
    FastAPI dependency that validates the InNoHassle JWT and returns the
    decoded token payload. Raises HTTP 401 on any auth failure.
    """
    user = inh_accounts.decode_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

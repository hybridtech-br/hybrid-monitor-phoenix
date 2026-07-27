"""Authentication endpoints for API version 1."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hybrid_monitor.api.dependencies import (
    get_authentication_service,
    get_current_user,
)
from hybrid_monitor.api.responses import success_response
from hybrid_monitor.domain.identity.models import User
from hybrid_monitor.domain.identity.schemas import (
    AuthenticatedSessionResponse,
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
)
from hybrid_monitor.domain.identity.services import (
    AuthenticationService,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> dict[str, Any]:
    """Authenticate credentials and issue access/refresh tokens."""
    try:
        session = await service.authenticate(
            payload.email,
            payload.password.get_secret_value(),
        )
    except InvalidCredentialsError as exc:
        raise _authentication_error("Invalid email or password") from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        ) from exc

    data = AuthenticatedSessionResponse.from_session(session).model_dump(mode="json")
    return success_response(request, data)


@router.post("/refresh")
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> dict[str, Any]:
    """Rotate a refresh token and issue a replacement token pair."""
    try:
        session = await service.refresh(payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise _authentication_error("Refresh token is invalid") from exc

    data = AuthenticatedSessionResponse.from_session(session).model_dump(mode="json")
    return success_response(request, data)


@router.get("/me")
async def current_session(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return the active user and effective authorization context."""
    data = CurrentUserResponse.from_user(user).model_dump(mode="json")
    return success_response(request, data)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.database import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.audit_service import create_audit_log
from app.services.auth_rate_limit_service import (
    AuthRateLimitExceeded,
    auth_rate_limiter,
)
from app.services.user_service import authenticate_user, create_user, get_user_by_email


router = APIRouter(prefix="/auth", tags=["auth"])


def _client_host(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _rate_limit_key(request: Request, email: str) -> str:
    return f"{_client_host(request)}:{email.lower()}"


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def signup(
    user_in: UserCreate, request: Request, db: Session = Depends(get_db)
) -> UserResponse:
    rate_limit_key = _rate_limit_key(request, user_in.email)
    try:
        auth_rate_limiter.check(rate_limit_key)
    except AuthRateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc

    existing_user = get_user_by_email(db, user_in.email.lower())
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = create_user(db, user_in)
    create_audit_log(
        db,
        user.id,
        "auth.signup_succeeded",
        "user",
        str(user.id),
        {"email": user.email},
    )
    db.commit()
    auth_rate_limiter.reset(rate_limit_key)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    rate_limit_key = _rate_limit_key(request, form_data.username)
    try:
        auth_rate_limiter.check(rate_limit_key)
    except AuthRateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc

    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        existing_user = get_user_by_email(db, form_data.username.lower())
        if existing_user is not None:
            create_audit_log(
                db,
                existing_user.id,
                "auth.login_failed",
                "user",
                str(existing_user.id),
                {"email": existing_user.email},
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    create_audit_log(
        db, user.id, "auth.login_succeeded", "user", str(user.id), {"email": user.email}
    )
    db.commit()
    auth_rate_limiter.reset(rate_limit_key)
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")

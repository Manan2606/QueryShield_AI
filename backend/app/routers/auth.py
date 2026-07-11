from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.database import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.audit_service import create_audit_log
from app.services.user_service import authenticate_user, create_user, get_user_by_email


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    existing_user = get_user_by_email(db, user_in.email.lower())
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = create_user(db, user_in)
    create_audit_log(db, user.id, "auth.signup_succeeded", "user", str(user.id), {"email": user.email})
    db.commit()
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        existing_user = get_user_by_email(db, form_data.username.lower())
        if existing_user is not None:
            create_audit_log(db, existing_user.id, "auth.login_failed", "user", str(existing_user.id), {"email": existing_user.email})
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    create_audit_log(db, user.id, "auth.login_succeeded", "user", str(user.id), {"email": user.email})
    db.commit()
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")

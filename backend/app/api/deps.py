from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.user_service import get_user_by_email


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, TypeError, ValueError) as exc:
        raise credentials_exception from exc

    if token_data.sub is None:
        raise credentials_exception

    if token_data.sub.isdigit():
        user = db.get(User, int(token_data.sub))
    else:
        user = get_user_by_email(db, token_data.sub)

    if user is None or not user.is_active:
        raise credentials_exception

    return user

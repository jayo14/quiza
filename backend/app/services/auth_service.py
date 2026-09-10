from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import AuthResponse, SignInRequest, SignUpRequest, TokenResponse


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def sign_up(db: Session, payload: SignUpRequest) -> AuthResponse:
    if get_user_by_email(db, payload.email):
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(user=user, tokens=_issue_tokens(user))


def sign_in(db: Session, payload: SignInRequest) -> AuthResponse:
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password.")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")

    return AuthResponse(user=user, tokens=_issue_tokens(user))


def request_password_reset(db: Session, email: str, background_tasks) -> str | None:
    from app.core.config import settings
    from app.services.email_service import send_password_reset_email


    user = get_user_by_email(db, email)
    if not user:
        return None
    token = create_password_reset_token(user.id)
    reset_link = f"{settings.frontend_url}/reset-password?token={token}"
    background_tasks.add_task(send_password_reset_email, user.email, reset_link)

    return token


def reset_password(db: Session, token: str, new_password: str) -> None:
    from app.core.security import InvalidTokenError

    try:
        user_id = decode_token(token, TokenType.PASSWORD_RESET)
    except InvalidTokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user = get_user_by_id(db, user_id)
    if not user:
        raise UnauthorizedError("Invalid reset token.")

    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()

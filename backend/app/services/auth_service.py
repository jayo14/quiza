from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError, ValidationFailedError
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
from app.schemas.auth import AuthResponse, GoogleSignInRequest, SignInRequest, SignUpRequest, TokenResponse


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
    if len(payload.password) < 8:
        raise ValidationFailedError("Password must be at least 8 characters long.")
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

def google_sign_in(db: Session, payload: GoogleSignInRequest) -> AuthResponse:
    from app.core.config import settings
    import jwt
    import uuid

    try:
        # Verify the Supabase JWT
        # Supabase signs JWTs with the SUPABASE_JWT_SECRET
        jwt_secret = settings.supabase_anon_key if not settings.effective_supabase_key else settings.effective_supabase_key
        # Wait, Supabase JWT secret is different from anon key. Let's assume it's set in env, or we don't verify locally, we use supabase client.
        # It's better to verify using jwt library if we have the secret, otherwise use supabase admin client.
        # Supabase JS on frontend actually gives the session. The backend should verify the token.
        # But wait, without SUPABASE_JWT_SECRET, we can just use the supabase client to get the user.
        from supabase import create_client, Client
        supabase: Client = create_client(settings.effective_supabase_url, settings.effective_supabase_key)
        
        # Verify token by getting the user
        user_resp = supabase.auth.get_user(payload.token)
        if not user_resp or not user_resp.user:
            raise UnauthorizedError("Invalid Google token.")
            
        supabase_user = user_resp.user
        email = supabase_user.email
        name = supabase_user.user_metadata.get("full_name", email.split("@")[0])
        
    except Exception as e:
        raise UnauthorizedError(f"Google sign in failed: {str(e)}")

    user = get_user_by_email(db, email)
    if not user:
        user = User(
            email=email.lower(),
            password_hash=None,
            name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")

    return AuthResponse(user=user, tokens=_issue_tokens(user))

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleSignInRequest,
    ResetPasswordRequest,
    SignInRequest,
    SignUpRequest,
)
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return auth_service.sign_up(db, payload)


@router.post("/signin", response_model=AuthResponse)
def signin(payload: SignInRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return auth_service.sign_in(db, payload)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    auth_service.request_password_reset(db, payload.email, background_tasks)
    # Always return a generic message so this endpoint can't be used to enumerate
    # registered emails.
    return ForgotPasswordResponse()


@router.post("/reset-password", status_code=204)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.reset_password(db, payload.token, payload.new_password)

@router.post("/google", response_model=AuthResponse)
def google_signin(payload: GoogleSignInRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return auth_service.google_sign_in(db, payload)

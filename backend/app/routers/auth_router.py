from datetime import datetime, timedelta, timezone

import jwt
from fastapi import (
    APIRouter, Depends, HTTPException, Request, Response, status
)
from sqlalchemy.orm import Session

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth import exceptions as google_exceptions

from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import GoogleAuthRequest, CurrentUserResponse
from app.config.auth import (
    GOOGLE_CLIENT_ID,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE,
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


def verify_google_token(token: str, client_id: str) -> dict:
    """
    Verify Google ID token and return payload.

    Uses google.oauth2.id_token.verify_oauth2_token() which:
    - Validates signature against Google's public keys
    - Checks aud matches client_id
    - Checks iss is accounts.google.com
    - Checks token not expired (with optional clock_skew_in_seconds)

    Returns: dict with sub, email, email_verified, name, picture, etc.
    Raises: ValueError or GoogleAuthError on failure
    """
    request = google_requests.Request()

    idinfo = id_token.verify_oauth2_token(
        id_token=token,
        request=request,
        audience=client_id,
        clock_skew_in_seconds=10,
    )

    return idinfo


def create_session_jwt(user: User) -> str:
    """Create a platform JWT for the authenticated user."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@router.post("/google")
def google_auth(
    payload: GoogleAuthRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Verify Google ID token and issue platform session.

    1. Verify the ID token using Google's public keys
    2. Extract user info (sub, email, name, picture)
    3. Check if email exists in DB (invite-only model)
    4. Issue platform JWT in httpOnly cookie
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )

    try:
        idinfo = verify_google_token(payload.token, GOOGLE_CLIENT_ID)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except google_exceptions.GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )

    # Extract user info from token
    google_sub = idinfo.get("sub")
    email = idinfo.get("email")
    email_verified = idinfo.get("email_verified", False)
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified with Google",
        )

    # Look up user by email (invite-only model)
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not_registered",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="inactive",
        )

    # Update user with Google info
    now = datetime.now(timezone.utc)
    if not user.google_sub:
        user.google_sub = google_sub
        user.first_login_at = now
    user.display_name = name
    user.avatar_url = picture
    user.last_login_at = now

    # Log the login event
    audit_log = AuditLog(
        actor_id=user.id,
        action="LOGIN",
        entity_type="user",
        entity_id=str(user.id),
    )
    db.add(audit_log)
    db.commit()
    db.refresh(user)

    # Create session JWT
    session_token = create_session_jwt(user)

    # Set httpOnly cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=JWT_EXPIRY_HOURS * 3600,
        path="/",
    )

    return {
        "message": "Authentication successful",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
        },
    }


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_info(request: Request, db: Session = Depends(get_db)):
    """Return current authenticated user info from session cookie."""
    from app.dependencies.auth import get_current_user_from_cookie

    user = get_current_user_from_cookie(request, db)
    return user


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )
    return {"message": "Logged out successfully"}

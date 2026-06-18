import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas import user as schemas
from app.dependencies.auth import RoleChecker, get_current_user
from app.mail import EmailService

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(RoleChecker(["Admin"]))],
)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    db_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    ).hex()
    return f"{salt}:{db_hash}"


@router.post(
    "",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User with email '{user.email}' already exists.",
        )

    password_hash = None
    if user.password:
        password_hash = hash_password(user.password)

    db_user = User(
        email=user.email,
        role=user.role,
        organization=user.organization,
        password_hash=password_hash,
        is_active=user.is_active,
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


async def send_invite_email_task(
    email: str, role: str, invited_by: str, login_url: str
):
    """Background task to send invite email."""
    try:
        email_service = EmailService()
        await email_service.send_invite_email(
            to=email,
            role=role,
            invited_by=invited_by,
            login_url=login_url,
        )
    except Exception as e:
        # Log error but don't fail - user was already created
        print(f"Failed to send invite email to {email}: {e}")


@router.post(
    "/invite",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_user(
    invite: schemas.UserInviteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Invite a new user to the platform.

    Creates a user record with the specified email and role.
    The user can then log in via Google SSO if their email matches.
    An invitation email will be sent to the user.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == invite.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User with email '{invite.email}' already exists.",
        )

    db_user = User(
        email=invite.email,
        role=invite.role,
        organization=invite.organization,
        is_active=True,
        invited_at=datetime.now(timezone.utc),
        invited_by_id=current_user.id,
    )

    try:
        db.add(db_user)
        db.flush()

        # Log the invite action
        audit_log = AuditLog(
            actor_id=current_user.id,
            action="INVITE_USER",
            entity_type="user",
            entity_id=str(db_user.id),
        )
        db.add(audit_log)
        db.commit()
        db.refresh(db_user)

        # Queue invite email to be sent in background
        inviter_name = current_user.display_name or current_user.email
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        background_tasks.add_task(
            send_invite_email_task,
            email=invite.email,
            role=invite.role,
            invited_by=inviter_name,
            login_url=f"{frontend_url}/login",
        )

        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[schemas.UserResponse])
def list_users(email: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if email:
        query = query.filter(User.email == email)
    return query.all()


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID '{user_id}' not found.",
        )
    return db_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: UUID,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID '{user_id}' not found.",
        )

    old_role = db_user.role
    role_changed = False

    if user.email is not None:
        # Check uniqueness if email changed
        if user.email != db_user.email:
            existing = db.query(User).filter(User.email == user.email).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"User with email '{user.email}' already exists.",
                )
        db_user.email = user.email

    if user.role is not None and user.role != old_role:
        db_user.role = user.role
        role_changed = True
    if user.organization is not None:
        db_user.organization = user.organization
    if user.is_active is not None:
        db_user.is_active = user.is_active
    if user.password is not None:
        db_user.password_hash = hash_password(user.password)

    try:
        # Log role change if applicable
        if role_changed:
            audit_log = AuditLog(
                actor_id=current_user.id,
                action="UPDATE_ROLE",
                entity_type="user",
                entity_id=str(db_user.id),
            )
            db.add(audit_log)

        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

import hashlib
import secrets
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import user as schemas

router = APIRouter(prefix="/api/v1/users", tags=["users"])


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
    user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID '{user_id}' not found.",
        )

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

    if user.role is not None:
        db_user.role = user.role
    if user.organization is not None:
        db_user.organization = user.organization
    if user.is_active is not None:
        db_user.is_active = user.is_active
    if user.password is not None:
        db_user.password_hash = hash_password(user.password)

    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

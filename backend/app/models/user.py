import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), nullable=False)  # 'Admin', 'Reviewer'
    organization = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # SSO fields
    google_sub = Column(String(255), unique=True, nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)

    # Invite tracking
    invited_at = Column(DateTime, nullable=True)
    invited_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    first_login_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    # Relationship for invited_by
    invited_by = relationship(
        "User", remote_side=[id], foreign_keys=[invited_by_id]
    )

    @classmethod
    def get_or_create_system_user(cls, db) -> "User":
        system_email = "system@nbd-wetland.org"  # TODO:: Need to updated (env)
        system_user = db.query(cls).filter(cls.email == system_email).first()
        if not system_user:
            system_user = cls(
                email=system_email,
                role="Admin",
                organization="System Watchdog",
                is_active=True,
            )
            db.add(system_user)
            db.commit()
            db.refresh(system_user)
        return system_user

import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), nullable=False)  # 'Admin', 'Reviewer', 'Partner'
    organization = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

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

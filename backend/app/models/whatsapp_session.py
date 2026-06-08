from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(
        String(20),
        nullable=False,
        index=True,
        comment="E.164 formatted number",
    )
    state = Column(
        String(30),
        nullable=False,
        default="CONSENT",
        comment="Current conversation state",
    )
    incident_type = Column(
        String(50), nullable=True, comment="Selected incident category code"
    )
    option_text = Column(
        Text,
        nullable=True,
        comment="Human readable option text selected by user",
    )
    media_url = Column(
        String(255),
        nullable=True,
        comment="Temporary Meta media URL (expires rapidly)",
    )
    location = Column(
        String(255),
        nullable=True,
        comment="User provided location identifier or coordinates",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<WhatsAppSession id={self.id} "
            f"phone={self.phone_number} state={self.state}>"
        )

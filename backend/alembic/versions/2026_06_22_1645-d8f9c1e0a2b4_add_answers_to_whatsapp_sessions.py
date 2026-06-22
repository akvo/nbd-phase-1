"""add answers to whatsapp sessions

Revision ID: d8f9c1e0a2b4
Revises: c8b3d7a4f6b8
Create Date: 2026-06-22 16:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d8f9c1e0a2b4"
down_revision: Union[str, None] = "c8b3d7a4f6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_sessions",
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Dynamic form question responses",
        ),
    )
    op.add_column(
        "whatsapp_sessions",
        sa.Column(
            "current_question_id",
            sa.Integer(),
            nullable=True,
            comment="Current question ID user is answering",
        ),
    )


def downgrade() -> None:
    op.drop_column("whatsapp_sessions", "current_question_id")
    op.drop_column("whatsapp_sessions", "answers")

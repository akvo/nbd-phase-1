"""add translations JSONB and language columns

Revision ID: b7d23a41c2c3
Revises: e6a7c36a461b
Create Date: 2026-06-10 08:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b7d23a41c2c3"
down_revision: Union[str, None] = "e6a7c36a461b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("form", sa.Column("translations", JSONB(), nullable=True))
    op.add_column("form", sa.Column("languages", JSONB(), nullable=True))
    op.add_column(
        "question_group", sa.Column("translations", JSONB(), nullable=True)
    )
    op.add_column(
        "question", sa.Column("translations", JSONB(), nullable=True)
    )
    op.add_column("option", sa.Column("translations", JSONB(), nullable=True))
    op.add_column(
        "whatsapp_sessions",
        sa.Column(
            "language",
            sa.String(length=5),
            nullable=False,
            server_default="en",
            comment="Selected locale code (e.g. en, sw)",
        ),
    )


def downgrade() -> None:
    op.drop_column("whatsapp_sessions", "language")
    op.drop_column("option", "translations")
    op.drop_column("question", "translations")
    op.drop_column("question_group", "translations")
    op.drop_column("form", "languages")
    op.drop_column("form", "translations")

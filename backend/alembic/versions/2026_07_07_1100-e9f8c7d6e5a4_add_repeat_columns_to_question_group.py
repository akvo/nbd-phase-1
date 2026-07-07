"""add repeat columns to question group and question

Revision ID: e9f8c7d6e5a4
Revises: d8f9c1e0a2b4
Create Date: 2026-07-07 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9f8c7d6e5a4"
down_revision: Union[str, None] = "d8f9c1e0a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "question_group",
        sa.Column(
            "repeat_button_placement",
            sa.String(length=255),
            nullable=True,
            comment="Placement of the repeat button",
        ),
    )
    op.add_column(
        "question_group",
        sa.Column(
            "leading_question",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Is this group the leading question group",
        ),
    )
    op.add_column(
        "question_group",
        sa.Column(
            "show_repeat_in_question_level",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Show repeat option in question level",
        ),
    )
    op.add_column(
        "question",
        sa.Column(
            "is_repeat_identifier",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Is this question the repeat identifier",
        ),
    )


def downgrade() -> None:
    op.drop_column("question", "is_repeat_identifier")
    op.drop_column("question_group", "show_repeat_in_question_level")
    op.drop_column("question_group", "leading_question")
    op.drop_column("question_group", "repeat_button_placement")

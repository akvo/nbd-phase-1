"""change leading question to fk

Revision ID: a8b7c6d5e4f3
Revises: e9f8c7d6e5a4
Create Date: 2026-07-07 11:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b7c6d5e4f3"
down_revision: Union[str, None] = "e9f8c7d6e5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop server default and allow nulls
    op.alter_column(
        "question_group",
        "leading_question",
        server_default=None,
        nullable=True,
    )
    # 2. Alter column type using cast (mapping boolean false/true to NULL)
    op.execute(
        "ALTER TABLE question_group ALTER COLUMN leading_question "
        "TYPE integer USING NULL::integer"
    )
    # 3. Add foreign key
    op.create_foreign_key(
        "fk_question_group_leading_question",
        "question_group",
        "question",
        ["leading_question"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # 1. Drop foreign key
    op.drop_constraint(
        "fk_question_group_leading_question",
        "question_group",
        type_="foreignkey",
    )
    # 2. Alter column type back to boolean using cast
    op.execute(
        "ALTER TABLE question_group ALTER COLUMN leading_question "
        "TYPE boolean USING (CASE WHEN leading_question IS NOT NULL THEN true ELSE false END)"  # noqa
    )
    # 3. Set server default back
    op.alter_column(
        "question_group",
        "leading_question",
        server_default=sa.text("false"),
    )

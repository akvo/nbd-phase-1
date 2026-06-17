"""add kobo_asset_id to form

Revision ID: e6a7c36a461b
Revises: d3f7a1f5922c
Create Date: 2026-06-09 07:45:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6a7c36a461b"
down_revision: Union[str, None] = "d3f7a1f5922c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add kobo_asset_id to form table
    op.add_column(
        "form",
        sa.Column("kobo_asset_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_form_kobo_asset_id", "form", ["kobo_asset_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_form_kobo_asset_id", table_name="form")
    op.drop_column("form", "kobo_asset_id")

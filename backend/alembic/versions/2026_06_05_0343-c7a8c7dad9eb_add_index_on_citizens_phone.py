"""add_index_on_citizens_phone

Revision ID: c7a8c7dad9eb
Revises: 384a4835396a
Create Date: 2026-06-05 03:43:40.150239

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c7a8c7dad9eb"
down_revision: Union[str, None] = "384a4835396a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_citizens_phone", "citizens", ["phone_number"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_citizens_phone", table_name="citizens")

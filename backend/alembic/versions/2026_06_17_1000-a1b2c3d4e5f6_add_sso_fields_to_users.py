"""add_sso_fields_to_users

Revision ID: a1b2c3d4e5f6
Revises: df362444cf35
Create Date: 2026-06-17 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "df362444cf35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add SSO fields
    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("display_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
    )

    # Add invite tracking fields
    op.add_column(
        "users",
        sa.Column("invited_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "invited_by_id",
            sa.UUID(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("first_login_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )

    # Create unique index on google_sub
    op.create_index(
        op.f("ix_users_google_sub"),
        "users",
        ["google_sub"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "first_login_at")
    op.drop_column("users", "invited_by_id")
    op.drop_column("users", "invited_at")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "display_name")
    op.drop_column("users", "google_sub")

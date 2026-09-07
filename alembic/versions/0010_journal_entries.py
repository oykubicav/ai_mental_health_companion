"""journal_entries tablosu

Günlük: kullanıcının her gün doldurabildiği kısa kayıt. Gün başına tek
satır — aynı güne tekrar yazmak üstüne yazar.

Revision ID: 0010_journal_entries
Revises: 0009_exercise_entries
"""
from alembic import op
import sqlalchemy as sa

from api.db.models import GUID, PortableJSON


revision = "0010_journal_entries"
down_revision = "0009_exercise_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=True),
        sa.Column("did", sa.Text(), nullable=True),
        sa.Column("thoughts", sa.Text(), nullable=True),
        sa.Column("good", sa.Text(), nullable=True),
        sa.Column("tags", PortableJSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "entry_date", name="uq_journal_user_date"),
    )
    op.create_index("idx_journal_user_date", "journal_entries", ["user_id", "entry_date"])


def downgrade() -> None:
    op.drop_index("idx_journal_user_date", table_name="journal_entries")
    op.drop_table("journal_entries")

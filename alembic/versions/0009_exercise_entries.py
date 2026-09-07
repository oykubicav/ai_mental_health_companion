"""exercise_entries tablosu

Düşünce kaydı, küçük adım planı gibi araçlarda kullanıcının yazdıkları.
Hesaba bağlı, kullanıcı silene kadar durur; LLM'e gönderilmez.

Revision ID: 0009_exercise_entries
Revises: 0008_therapy_experience
"""
from alembic import op
import sqlalchemy as sa

from api.db.models import GUID, PortableJSON


revision = "0009_exercise_entries"
down_revision = "0008_therapy_experience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exercise_entries",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("payload", PortableJSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_exercise_entries_user_created", "exercise_entries", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_exercise_entries_user_created", table_name="exercise_entries")
    op.drop_table("exercise_entries")

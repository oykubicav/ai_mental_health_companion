"""users.therapy_experience

Onboarding'de sorulan "daha önce böyle bir şey denedin mi" cevabı.
Bir uzmanla görüşen kullanıcıya karşılamada Neva'nın terapinin yerine
değil yanına konduğu söylenir.

Revision ID: 0008_therapy_experience
Revises: 0007_refresh_tokens
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_therapy_experience"
down_revision = "0007_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("therapy_experience", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "therapy_experience")

"""assessments.session_id artık boş bırakılabilir

Ölçüm sohbetten bağımsız: hesabı olan kullanıcı hiç konuşmadan da
yapabiliyor. Kolon zorunlu olduğu için, sırf ölçümün tutunacağı bir
satır olsun diye mesajsız ChatSession'lar açılıyordu; bunlar
"Sohbetlerim" listesinde 0 mesajlı sahte sohbetler olarak görünüyordu.

Revision ID: 0012_assessment_session_optional
Revises: 0011_assessment_user_backfill
"""
from alembic import op
import sqlalchemy as sa

from api.db.models import GUID


revision = "0012_assessment_session_optional"
down_revision = "0011_assessment_user_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "assessments", "session_id",
        existing_type=GUID(), nullable=True,
    )
    # Ölçüm için açılmış, hiç mesaj yazılmamış oturumları temizle.
    # Ölçümlerin session_id'si NULL'a düşüyor (FK ondelete=CASCADE
    # değil, önce bağı koparıyoruz).
    op.execute(
        """
        UPDATE assessments
        SET session_id = NULL
        WHERE user_id IS NOT NULL
          AND session_id IN (
            SELECT s.id FROM sessions s
            LEFT JOIN turns t ON t.session_id = s.id
            WHERE t.id IS NULL
          )
        """
    )
    op.execute(
        """
        DELETE FROM sessions
        WHERE user_id IS NOT NULL
          AND id NOT IN (SELECT session_id FROM turns)
          AND id NOT IN (
            SELECT session_id FROM assessments WHERE session_id IS NOT NULL
          )
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM assessments WHERE session_id IS NULL")
    op.alter_column(
        "assessments", "session_id",
        existing_type=GUID(), nullable=False,
    )

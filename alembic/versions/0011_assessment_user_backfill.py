"""assessments.user_id geriye dönük doldurma

Ölçüm kaydedilirken user_id yazılmıyordu; kayıtlar yalnızca oturuma
bağlıydı. Kullanıcı yeni bir sohbet açtığında grafiği sıfırdan başlıyor,
"ilk ölçüm" kilometre taşı hiç tetiklenmiyordu.

Kod düzeltildi; bu migration mevcut kayıtları oturumun sahibinden
dolduruyor. Anonim oturumların kayıtları NULL kalıyor.

Revision ID: 0011_assessment_user_backfill
Revises: 0010_journal_entries
"""
from alembic import op


revision = "0011_assessment_user_backfill"
down_revision = "0010_journal_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE assessments
        SET user_id = (
            SELECT s.user_id FROM sessions s WHERE s.id = assessments.session_id
        )
        WHERE user_id IS NULL
        """
    )


def downgrade() -> None:
    # Geri alınmıyor: doldurulan değer zaten oturumdan türetilebilir.
    pass

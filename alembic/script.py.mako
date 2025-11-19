"""마이그레이션 스크립트 템플릿

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """업그레이드"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """다운그레이드"""
    ${downgrades if downgrades else "pass"}

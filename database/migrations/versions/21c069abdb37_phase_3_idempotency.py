"""Phase 3 idempotency

Revision ID: 21c069abdb37
Revises: 9366124a5a51
Create Date: 2026-09-03 18:31:34.514690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21c069abdb37'
down_revision: Union[str, None] = '9366124a5a51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('idempotency_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_idempotency_keys_key'), 'idempotency_keys', ['key'], unique=False)
    op.create_index(op.f('ix_idempotency_keys_tenant_id'), 'idempotency_keys', ['tenant_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_idempotency_keys_tenant_id'), table_name='idempotency_keys')
    op.drop_index(op.f('ix_idempotency_keys_key'), table_name='idempotency_keys')
    op.drop_table('idempotency_keys')

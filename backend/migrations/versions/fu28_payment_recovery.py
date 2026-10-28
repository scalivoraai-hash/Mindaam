"""Add payment settlement state; preserve existing payments and immutable ledger."""
from alembic import op
import sqlalchemy as sa
revision = 'fu28_payment_recovery'
down_revision = 'ft28_event_venue_mode'
branch_labels = None
depends_on = None
def upgrade():
    op.add_column('payments', sa.Column('intent_id', sa.String(), nullable=True))
    op.create_index('ix_payments_intent_id', 'payments', ['intent_id'], unique=True)
    for name in ('refunded_pence', 'reversed_credits', 'dispute_pence'):
        op.add_column('payments', sa.Column(name, sa.Integer(), nullable=False, server_default='0'))
    op.add_column('payments', sa.Column('dispute_status', sa.String(), nullable=True))
    op.add_column('payments', sa.Column('dispute_updated', sa.Float(), nullable=False, server_default='0'))
def downgrade():
    op.drop_index('ix_payments_intent_id', table_name='payments')
    for name in ('intent_id', 'refunded_pence', 'reversed_credits', 'dispute_pence', 'dispute_status', 'dispute_updated'):
        op.drop_column('payments', name)

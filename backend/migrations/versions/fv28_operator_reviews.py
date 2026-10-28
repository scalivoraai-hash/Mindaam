"""Add two-person wallet reviews without changing existing ledger or user data."""
from alembic import op
import sqlalchemy as sa
revision='fv28_operator_reviews'
down_revision='fu28_payment_recovery'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('operator_adjustment_reviews',sa.Column('id',sa.String(36),primary_key=True),sa.Column('requester_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('target_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('currency',sa.String(10),nullable=False),sa.Column('amount',sa.Integer(),nullable=False),sa.Column('purpose',sa.String(30),nullable=False),sa.Column('reason',sa.String(500),nullable=False),sa.Column('state',sa.String(20),nullable=False),sa.Column('reviewer_id',sa.String(36),sa.ForeignKey('users.id')),sa.Column('transaction_id',sa.String(36),sa.ForeignKey('wallet_transactions.id')),sa.Column('created_at',sa.Float(),nullable=False))
 for key in ('requester_id','target_id'):op.create_index('ix_operator_adjustment_reviews_'+key,'operator_adjustment_reviews',[key])
def downgrade():
 raise RuntimeError('Preserve financial review evidence; this additive migration is forward-only')

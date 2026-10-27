"""Add arena ticket entitlements and programme metadata; preserve old events and ledgers."""
from alembic import op
import sqlalchemy as sa
revision='fq27_grand_arena'
down_revision='fp30_rotating_collectibles'
branch_labels=None
depends_on=None
def upgrade():
 op.add_column('events',sa.Column('ticket_price',sa.Integer(),nullable=False,server_default='0'))
 op.add_column('events',sa.Column('programme',sa.JSON(),nullable=False,server_default='{}'))
 op.create_table('event_tickets',sa.Column('id',sa.String(36),primary_key=True),sa.Column('event_id',sa.String(36),sa.ForeignKey('events.id'),nullable=False),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('request_id',sa.String(36),nullable=False),sa.Column('cost',sa.Integer(),nullable=False),sa.Column('ledger_id',sa.String(36),sa.ForeignKey('wallet_transactions.id'),nullable=False),sa.Column('refunded_at',sa.Float(),nullable=True),sa.Column('created_at',sa.Float(),nullable=False),sa.UniqueConstraint('event_id','user_id'),sa.UniqueConstraint('user_id','request_id'))
 op.create_index('ix_event_tickets_event_id','event_tickets',['event_id'])
 op.create_index('ix_event_tickets_user_id','event_tickets',['user_id'])
def downgrade():
 op.drop_table('event_tickets')
 op.drop_column('events','programme')
 op.drop_column('events','ticket_price')

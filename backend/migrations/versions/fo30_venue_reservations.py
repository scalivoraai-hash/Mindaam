"""Add purchased-credit venue reservations. No existing wallet rows are changed."""
from alembic import op
import sqlalchemy as sa
revision='fo30_venue_reservations'
down_revision='fn30_event_presentation'
branch_labels=None
depends_on=None

def upgrade():
 op.create_table('venue_bookings',
  sa.Column('id',sa.String(36),primary_key=True),sa.Column('request_id',sa.String(36),nullable=False),
  sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
  sa.Column('event_id',sa.String(36),sa.ForeignKey('events.id'),nullable=False,unique=True),
  sa.Column('city',sa.String(80),nullable=False),sa.Column('starts_at',sa.Float(),nullable=False),sa.Column('ends_at',sa.Float(),nullable=False),
  sa.Column('hours',sa.Integer(),nullable=False),sa.Column('cost',sa.Integer(),nullable=False),
  sa.Column('ledger_id',sa.String(36),sa.ForeignKey('wallet_transactions.id'),nullable=False),sa.Column('created_at',sa.Float(),nullable=False),
  sa.UniqueConstraint('user_id','request_id'))
 for name in ['user_id','city','starts_at']:op.create_index('ix_venue_bookings_'+name,'venue_bookings',[name])

def downgrade():op.drop_table('venue_bookings')

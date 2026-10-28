"""Add explicit venue choice; NULL preserves legacy interpretation and reservations."""
from alembic import op
import sqlalchemy as sa
revision='ft28_event_venue_mode'
down_revision='fs27_approved_venue_prices'
branch_labels=None
depends_on=None
def upgrade():
 op.add_column('events',sa.Column('venue_mode',sa.String(30),nullable=True))
def downgrade():
 op.drop_column('events','venue_mode')

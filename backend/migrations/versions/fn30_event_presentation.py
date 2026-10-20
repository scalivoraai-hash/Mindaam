"""Add event presentation/lighting permissions. Existing events and ledgers are untouched."""
from alembic import op
import sqlalchemy as sa
revision='fn30_event_presentation'
down_revision='fm25_world_movement'
branch_labels=None
depends_on=None

def upgrade():
 op.add_column('events',sa.Column('presentation',sa.JSON(),nullable=False,server_default='{}'))
 op.add_column('events',sa.Column('lighting',sa.JSON(),nullable=False,server_default='{}'))
 op.add_column('event_attendees',sa.Column('share_state',sa.String(20),nullable=False,server_default='none'))
 op.add_column('event_attendees',sa.Column('permission_revision',sa.Integer(),nullable=False,server_default='0'))

def downgrade():
 op.drop_column('event_attendees','permission_revision')
 op.drop_column('event_attendees','share_state')
 op.drop_column('events','lighting')
 op.drop_column('events','presentation')

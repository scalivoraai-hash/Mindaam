"""Authoritative pedestrian acceleration; preserve all access and reward history."""
from alembic import op
import sqlalchemy as sa
revision='fm25_world_movement'
down_revision='fl25_world_access_correction'
branch_labels=None
depends_on=None

def upgrade():
 op.add_column('user_presence',sa.Column('motion_speed',sa.Float(),nullable=False,server_default='0'))

def downgrade():
 op.drop_column('user_presence','motion_speed')

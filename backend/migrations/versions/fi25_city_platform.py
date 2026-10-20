"""Additive city platform extensions; existing accounts, messages and ledgers preserved."""
from alembic import op
import sqlalchemy as sa
revision='fi25_city_platform'
down_revision='fh24_world_growth'
branch_labels=None
depends_on=None
def upgrade():
 op.add_column('users',sa.Column('must_change_password',sa.Boolean(),nullable=False,server_default=sa.false()))
 op.add_column('user_presence',sa.Column('zone_id',sa.String(100),nullable=False,server_default='world'))
 op.add_column('user_presence',sa.Column('return_position',sa.JSON(),nullable=False,server_default='{}'))
 op.create_index('ix_user_presence_zone_id','user_presence',['zone_id'])
 op.add_column('media_sessions',sa.Column('max_participants',sa.Integer(),nullable=False,server_default='6'))
 op.add_column('media_sessions',sa.Column('distance_policy',sa.String(20),nullable=False,server_default='proximity'))
 op.add_column('events',sa.Column('venue_experience_type',sa.String(30),nullable=False,server_default='standard'))
 op.add_column('events',sa.Column('chat_enabled',sa.Boolean(),nullable=False,server_default=sa.true()))
 from backend.api.transit import Route,Stop,Vehicle,Hail,Ticket
 from backend.api.civic import PublicBuilding,InteriorVisit
 from backend.api.operations import AdBoard,Creative,AdCampaign,AdEnquiry,AdInteraction,UserActivity,OnlineSample
 for model in [Route,Stop,Vehicle,Hail,Ticket,PublicBuilding,InteriorVisit,AdBoard,Creative,AdCampaign,AdEnquiry,AdInteraction,UserActivity,OnlineSample]:model.__table__.create(op.get_bind())
def downgrade():raise RuntimeError('Forward-only: preserve tickets, enquiries and world access. Roll back application only with compatible columns.')

"""Extend existing events and attendees for hosted social media."""
from alembic import op
import sqlalchemy as sa
revision='fg21_social_events'
down_revision='ff21_conversation_moderators'
branch_labels=None
depends_on=None
def upgrade():
 for name,typ,default in [('event_type',sa.String(30),'Social Hangout'),('communication_mode',sa.String(20),'text'),('visibility',sa.String(20),'public'),('status',sa.String(20),'scheduled'),('zone_id',sa.String(80),'')]:op.add_column('events',sa.Column(name,typ,nullable=False,server_default=default))
 for name,typ in [('ends_at',sa.Float()),('session_id',sa.String(36)),('x',sa.Float()),('z',sa.Float())]:op.add_column('events',sa.Column(name,typ,nullable=True))
 op.add_column('events',sa.Column('created_at',sa.Float(),nullable=False,server_default='0'))
 op.add_column('events',sa.Column('reminded',sa.Boolean(),nullable=False,server_default=sa.false()))
 op.execute('UPDATE events SET created_at=starts_at')
 for name,typ,default in [('state',sa.String(20),'active'),('role',sa.String(20),'audience')]:op.add_column('event_attendees',sa.Column(name,typ,nullable=False,server_default=default))
 for name in ['joined_at','last_seen']:op.add_column('event_attendees',sa.Column(name,sa.Float(),nullable=False,server_default='0'))
 op.add_column('event_attendees',sa.Column('permission_dirty',sa.Boolean(),nullable=False,server_default=sa.false()))
 op.add_column('event_attendees',sa.Column('hand',sa.Boolean(),nullable=False,server_default=sa.false()))
 op.add_column('media_sessions',sa.Column('event_id',sa.String(36),nullable=True))
 op.create_index('ix_media_sessions_event_id','media_sessions',['event_id'])
 op.execute("INSERT INTO event_attendees (event_id,user_id,state,role,joined_at,last_seen,hand) SELECT e.id,e.host_id,'active','host',e.starts_at,e.starts_at,false FROM events e WHERE NOT EXISTS (SELECT 1 FROM event_attendees a WHERE a.event_id=e.id AND a.user_id=e.host_id)")
 op.execute("UPDATE event_attendees SET role='host' WHERE EXISTS (SELECT 1 FROM events e WHERE e.id=event_attendees.event_id AND e.host_id=event_attendees.user_id)")
def downgrade():raise RuntimeError('Forward-only; preserve event records')

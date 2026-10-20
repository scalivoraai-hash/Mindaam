"""Extend existing consent sessions with additive membership and join requests."""
from alembic import op
import sqlalchemy as sa
revision='fe21_conversation_members'
down_revision='fd21_profile_display'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('media_sessions',sa.Column('conversation_id',sa.String(36),nullable=True))
    op.create_index('ix_media_sessions_conversation_id','media_sessions',['conversation_id'])
    op.add_column('media_sessions',sa.Column('join_policy',sa.String(30),nullable=False,server_default='approval'))
    op.add_column('media_sessions',sa.Column('end_reason',sa.String(60),nullable=True))
    op.create_table('conversation_members',sa.Column('session_id',sa.String(36),sa.ForeignKey('media_sessions.id'),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),sa.Column('state',sa.String(20),nullable=False),sa.Column('joined_at',sa.Float(),nullable=False),sa.Column('left_at',sa.Float()),sa.Column('out_since',sa.Float()),sa.Column('warning',sa.Boolean(),nullable=False),sa.Column('reason',sa.String(60)))
    op.create_table('conversation_join_requests',sa.Column('session_id',sa.String(36),sa.ForeignKey('media_sessions.id'),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),sa.Column('state',sa.String(20),nullable=False),sa.Column('created_at',sa.Float(),nullable=False),sa.Column('decided_by',sa.String(36),sa.ForeignKey('users.id')))
    op.execute("INSERT INTO conversation_members (session_id,user_id,state,joined_at,warning) SELECT id,requester,'active',created_at,false FROM media_sessions WHERE state='accepted'")
    op.execute("INSERT INTO conversation_members (session_id,user_id,state,joined_at,warning) SELECT id,target,'active',created_at,false FROM media_sessions WHERE state='accepted'")

def downgrade():
    raise RuntimeError('Forward-only; preserve conversation history')

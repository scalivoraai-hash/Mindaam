"""Original co-moderators and removed-member rejoin cooldown."""
from alembic import op
import sqlalchemy as sa
revision='ff21_conversation_moderators'
down_revision='fe21_conversation_members'
branch_labels=None
depends_on=None
def upgrade():
 op.add_column('conversation_members',sa.Column('role',sa.String(30),nullable=False,server_default='JOINED_PARTICIPANT'))
 op.add_column('conversation_members',sa.Column('rejoin_after',sa.Float(),nullable=True))
 op.execute("UPDATE conversation_members SET role='ORIGINAL_MODERATOR' WHERE EXISTS (SELECT 1 FROM media_sessions s WHERE s.id=conversation_members.session_id AND (s.requester=conversation_members.user_id OR s.target=conversation_members.user_id))")
def downgrade():raise RuntimeError('Forward-only migration')

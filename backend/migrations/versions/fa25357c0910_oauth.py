"""Provider identity and single-use OAuth state."""
from alembic import op
import sqlalchemy as sa
revision='fa25357c0910'
down_revision='f924d59ca201'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('oauth_flows',sa.Column('id',sa.String(64),primary_key=True),sa.Column('provider',sa.String(20),nullable=False),sa.Column('nonce',sa.String(100),nullable=False),sa.Column('verifier',sa.String(100),nullable=False),sa.Column('user_id',sa.String(),sa.ForeignKey('users.id')),sa.Column('expires_at',sa.Float(),nullable=False))
 op.create_table('oauth_identities',sa.Column('provider',sa.String(20),primary_key=True),sa.Column('subject',sa.String(255),primary_key=True),sa.Column('user_id',sa.String(),sa.ForeignKey('users.id'),nullable=False))
def downgrade():
 raise RuntimeError('Preserve linked authentication identities')

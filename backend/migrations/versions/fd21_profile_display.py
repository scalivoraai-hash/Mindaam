"""Add optional identity and descriptive display profile, private by default."""
from alembic import op
import sqlalchemy as sa
revision = 'fd21_profile_display'
down_revision = 'fc20_release_auth'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('profile', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

def downgrade():
    raise RuntimeError('Forward-only: preserve profile data')

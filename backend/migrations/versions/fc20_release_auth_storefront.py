"""Add case-insensitive usernames and merchant-owned storefront configuration."""
from alembic import op
import sqlalchemy as sa
revision='fc20_release_auth'
down_revision='fb3418c65a20'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('businesses',sa.Column('signage',sa.JSON(),nullable=False,server_default=sa.text("'{}'")))
    op.create_index('uq_users_username_normalized','users',[sa.text('lower(trim(username))')],unique=True)

def downgrade():
    raise RuntimeError('Forward-only additive release; preserve account and merchant data')

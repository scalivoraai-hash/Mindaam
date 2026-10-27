"""Add bounded, owner-scoped profile photos; no existing account changes."""
from alembic import op
import sqlalchemy as sa
revision='fr27_profile_photos'
down_revision='fq27_grand_arena'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('profile_photos',
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('kind',sa.String(10),primary_key=True),
        sa.Column('data',sa.LargeBinary(),nullable=False),
        sa.Column('updated_at',sa.Float(),nullable=False))

def downgrade():
    op.drop_table('profile_photos')

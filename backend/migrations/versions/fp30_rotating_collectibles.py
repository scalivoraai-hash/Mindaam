"""Mark generated instances; old collectibles and every claim remain unchanged."""
from alembic import op
import sqlalchemy as sa
revision='fp30_rotating_collectibles'
down_revision='fo30_venue_reservations'
branch_labels=None
depends_on=None

def upgrade():op.add_column('collectible_instances',sa.Column('origin',sa.String(16),nullable=False,server_default='authored'))
def downgrade():op.drop_column('collectible_instances','origin')

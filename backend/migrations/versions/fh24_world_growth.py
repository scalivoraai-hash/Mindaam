"""Permanent world access; grandfather all destinations available before this gate."""
from alembic import op
import sqlalchemy as sa
revision='fh24_world_growth'
down_revision='fg21_social_events'
branch_labels=None
depends_on=None
LEGACY=['milton-keynes','milton-keynes-centre','milton-keynes-willen','london','birmingham','manchester','liverpool','leeds','bristol','oxford','cambridge','york','brighton','newcastle','nottingham','cardiff','edinburgh']
def upgrade():
 from backend.api.growth import WorldAccess,ShareInvite,ShareAction,GrowthEvent
 for table in [WorldAccess.__table__,ShareInvite.__table__,ShareAction.__table__,GrowthEvent.__table__]:table.create(op.get_bind())
 # All pre-existing accounts could access every then-enabled district. Retain ALL 17.
 for city in LEGACY:
  op.get_bind().execute(sa.text("INSERT INTO world_access (user_id,destination_id,source,created_at) SELECT id,:city,'legacy',created_at FROM users"),{'city':city})
def downgrade():raise RuntimeError('Forward-only: never revoke permanent user access')

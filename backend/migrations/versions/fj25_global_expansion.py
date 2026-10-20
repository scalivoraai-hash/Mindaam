"""Persistent global catalogue and independent city demand; no access reset."""
from alembic import op
import sqlalchemy as sa
revision='fj25_global_expansion'
down_revision='fi25_city_platform'
branch_labels=None
depends_on=None

def upgrade():
 op.add_column('city_interests',sa.Column('source',sa.String(60),nullable=False,server_default='legacy'))
 op.add_column('city_interests',sa.Column('invite_code',sa.String(40),nullable=False,server_default=''))
 from backend.api.expansion import Destination,DemandShare,DemandShareAction,seed_catalog
 for model in [Destination,DemandShare,DemandShareAction]:model.__table__.create(op.get_bind())
 from sqlalchemy.orm import Session
 with Session(bind=op.get_bind()) as db:
  seed_catalog(db);db.flush()

def downgrade():
 raise RuntimeError('Forward-only: preserve destination demand and existing world entitlements.')

"""Additive rentals, attributed business profiles, gifts. Preserve existing ownership/ledger."""
from alembic import op
import sqlalchemy as sa
revision='fk25_social_mobility'
down_revision='fj25_global_expansion'
branch_labels=None
depends_on=None

def upgrade():
 # Allow unclaimed, attributed map listings without inventing merchant accounts.
 args={'table_args':(sa.CheckConstraint('funds >= 0'),)} if op.get_bind().dialect.name=='sqlite' else {}
 with op.batch_alter_table('businesses',**args) as batch:batch.alter_column('owner_id',existing_type=sa.String(),nullable=True)
 from backend.api.mobility import RentalAsset,WaterZone,RentalLease,RentalConsent
 from backend.api.business_spatial import BusinessSpatial,BusinessMember,BusinessInteraction
 from backend.api.gifts import GiftDelivery,Reaction
 for model in [GiftDelivery,Reaction,RentalAsset,WaterZone,RentalLease,RentalConsent,BusinessSpatial,BusinessMember,BusinessInteraction]:model.__table__.create(op.get_bind(),checkfirst=True)

def downgrade():raise RuntimeError('Forward-only: preserve rentals, policies, merchant identities and transaction history.')

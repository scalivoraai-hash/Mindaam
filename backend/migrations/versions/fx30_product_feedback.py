"""Add private product feedback; preserve all existing records."""
from alembic import op
revision='fx30_product_feedback'
down_revision='fw28_admin_reporting_indexes'
branch_labels=None
depends_on=None
def upgrade():
 from backend.api.feedback import ProductFeedback
 ProductFeedback.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():
 op.drop_table('product_feedback')

"""Index operator time windows; no ledger or account data is changed."""
from alembic import op
from sqlalchemy import inspect
revision='fw28_admin_reporting_indexes'
down_revision='fv28_operator_reviews'
branch_labels=None
depends_on=None
TABLES=('users','events','wallet_transactions','payments')
def upgrade():
 # Earlier additive migrations may create tables from current metadata on a fresh DB.
 for table,column in [(t,'created_at') for t in TABLES]+[('user_activity_days','day')]:
  name='ix_'+table+'_'+column
  if name not in {i['name'] for i in inspect(op.get_bind()).get_indexes(table)}:op.create_index(name,table,[column])
def downgrade():
 op.drop_index('ix_user_activity_days_day',table_name='user_activity_days')
 for table in TABLES:op.drop_index('ix_'+table+'_created_at',table_name=table)

"""Activate installed launch worlds; retain identities, votes and earned access."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
revision='fl25_world_access_correction'
down_revision='fk25_social_mobility'
branch_labels=None
depends_on=None

def upgrade():
 from backend.api.expansion import INTERNATIONAL,Destination,map_ready,seed_catalog
 from backend.api.models import Audit
 with Session(bind=op.get_bind()) as db:
  seed_catalog(db)
  for id,*_ in INTERNATIONAL:
   if not map_ready(id):raise RuntimeError('Launch map validation required: '+id)
   d=db.get(Destination,id)
   old=d.status
   d.status='ACTIVE';d.public=True;d.joinable=True
   db.add(Audit(action='destination.launch_corrected',target=id,details={'previous_status':old,'status':'ACTIVE','migration':revision}))
  db.flush()
 # Four previously valid shares now qualify. No actions, votes, entitlements or
 # referral/economic records are deleted, reset, or repurposed.
 op.get_bind().execute(sa.text("""
  INSERT INTO world_access (user_id,destination_id,source,created_at)
  SELECT s.user_id,s.destination_id,'share',MAX(s.created_at)
  FROM world_share_actions s
  WHERE NOT EXISTS (SELECT 1 FROM world_access a WHERE a.user_id=s.user_id AND a.destination_id=s.destination_id)
  GROUP BY s.user_id,s.destination_id HAVING COUNT(*) >= 4
 """))

def downgrade():raise RuntimeError('Forward-only: never revoke permanent world access or reset interest history.')

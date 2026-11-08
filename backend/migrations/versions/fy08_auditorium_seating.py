"""Add chair occupancy without changing existing events or user records."""
from alembic import op
revision='fy08_auditorium_seating'
down_revision='fy06_virtual_property'
branch_labels=None
depends_on=None

def upgrade():
    from backend.api.auditorium_seating import Seat
    Seat.__table__.create(op.get_bind(),checkfirst=True)

def downgrade():
    raise RuntimeError('Review active venue occupancy before an explicit rollback migration')

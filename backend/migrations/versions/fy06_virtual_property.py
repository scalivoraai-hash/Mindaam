"""Add virtual property inventory, pricing, offers and transfer receipts."""

from alembic import op

revision = "fy06_virtual_property"
down_revision = "fx30_product_feedback"
branch_labels = None
depends_on = None


def upgrade():
    from backend.api.property_economy import Property, Price, Offer, Trade, Reversal

    for model in (Property, Price, Offer, Trade, Reversal):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError(
        "Virtual ownership and trade receipts require an explicit retention procedure"
    )

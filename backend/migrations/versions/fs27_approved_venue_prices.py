"""Owner-approved 2h/10h prices; preserve configured overrides and booking history."""
from alembic import op
import sqlalchemy as sa
revision='fs27_approved_venue_prices'
down_revision='fr27_profile_photos'
branch_labels=None
depends_on=None

def upgrade():
    catalog=sa.table('configuration_versions',sa.column('key',sa.String),sa.column('value',sa.JSON))
    connection=op.get_bind()
    value=connection.execute(sa.select(catalog.c.value).where(catalog.c.key=='venue_rental_catalog')).scalar_one_or_none()
    if value is not None:
        value=dict(value)
        prices=dict(value.get('prices',{}))
        prices.setdefault('2',180)
        prices.setdefault('10',700)
        value['prices']=prices
        connection.execute(catalog.update().where(catalog.c.key=='venue_rental_catalog').values(value=value))

def downgrade():
    # Prices are durable business configuration. Never overwrite later admin
    # edits or rewrite charges while rolling back application schema versions.
    pass

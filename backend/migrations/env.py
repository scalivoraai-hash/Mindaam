from alembic import context
from backend.api.db import Base, engine, DATABASE_URL
from backend.api import models, commerce, identity, discovery, gameplay, subscriptions, talk, oauth, growth, transit, civic, operations, expansion, mobility, business_spatial, gifts, venue_rentals

config = context.config
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        from backend.migrations.inspection import application_filters
        include_name, include_object = application_filters(connection)
        # End read-only inspection before Alembic owns its migration transaction.
        connection.commit()
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True,
            include_name=include_name, include_object=include_object
        )
        with context.begin_transaction():
            context.run_migrations()

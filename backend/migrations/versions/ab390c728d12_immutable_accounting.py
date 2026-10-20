"""Protect ledger/audit data from application-level UPDATE and DELETE."""

from alembic import op

revision = "ab390c728d12"
down_revision = "7173fbacc1cb"
branch_labels = None
depends_on = None
TABLES = [
    "wallet_transactions",
    "funding_ledger",
    "audit_logs",
    "commerce_audit",
    "payment_events",
]


def upgrade():
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "CREATE FUNCTION pulseworld_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Immutable accounting/audit record'; END; $$"
        )
        for table in TABLES:
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION pulseworld_immutable()"
            )
    elif dialect == "sqlite":
        for table in TABLES:
            for action in ["UPDATE", "DELETE"]:
                op.execute(
                    f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'Immutable accounting/audit record'); END"
                )


def downgrade():
    dialect = op.get_bind().dialect.name
    for table in TABLES:
        if dialect == "postgresql":
            op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
        else:
            for action in ["update", "delete"]:
                op.execute(f"DROP TRIGGER IF EXISTS {table}_no_{action}")
    if dialect == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS pulseworld_immutable()")

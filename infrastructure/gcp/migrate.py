"""One Cloud Run Job owns migrations. Runtime credentials have DML rights only."""
import os
import subprocess
import sys
from urllib.parse import urlsplit, unquote
import psycopg
from psycopg import sql


def main():
    if os.environ.get("APP_ENV") not in ("staging", "production"):
        raise RuntimeError("Migration job requires an explicit environment")
    admin = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    runtime = urlsplit(os.environ["RUNTIME_DATABASE_URL"])
    user, password = unquote(runtime.username), unquote(runtime.password)
    database = runtime.path.lstrip("/")
    if user != "mindaam_" + os.environ["APP_ENV"] or database != user:
        raise RuntimeError("Migration/runtime environment mismatch")
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(2052011102)")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (user,)).fetchone():
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 12").format(sql.Identifier(user), sql.Literal(password)))
        role = conn.execute("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=%s", (user,)).fetchone()
        if any(role):
            raise RuntimeError("Runtime role has unexpected administrative privileges")
        conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {} CONNECTION LIMIT 12").format(sql.Identifier(user), sql.Literal(password)))
        conn.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(user)))
        conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], check=True)
        subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "check"], check=True)
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(user)))
        conn.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(user)))
        conn.execute(sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(user)))
        conn.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(sql.Identifier(user)))
        conn.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {}").format(sql.Identifier(user)))
        # Do not print URLs, passwords or query parameters.
    print("Migration and runtime grant checks completed.")


if __name__ == "__main__":
    main()

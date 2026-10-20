"""Runs only against disposable CI PostgreSQL, never a cloud database."""
import psycopg

url='postgresql://mindaam_staging:runtime-ci-only@127.0.0.1:5432/mindaam_staging'
with psycopg.connect(url,autocommit=True) as conn:
    assert conn.execute('SELECT version_num FROM alembic_version').fetchone()
    assert conn.execute('SELECT PostGIS_Version()').fetchone()
    assert not any(conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone())
    assert conn.execute("SELECT has_table_privilege(current_user,'users','INSERT,UPDATE,DELETE,SELECT')").fetchone()[0]
    try:
        conn.execute('CREATE TABLE public.unexpected_runtime_ddl (id integer)')
    except psycopg.errors.InsufficientPrivilege:
        pass
    else:
        raise AssertionError('Runtime credentials unexpectedly permit schema creation')
print('Migration schema, PostGIS and runtime DML-only isolation verified on disposable CI database.')

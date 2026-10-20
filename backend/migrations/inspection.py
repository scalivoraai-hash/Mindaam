"""Keep autogeneration scoped to application objects without hiding schema drift."""
import re


def equivalent_username_index(index, other):
    # PostgreSQL deparses SQL TRIM as btrim / TRIM(BOTH FROM ...). This is the
    # existing immutable username constraint, not a new normalization rule.
    if other is None or index.name != 'uq_users_username_normalized' or other.name != index.name:
        return False
    if index.table.name != 'users' or other.table.name != 'users' or not index.unique or not other.unique:
        return False
    def expression(value):
        if len(value.expressions) != 1:
            return False
        sql = str(value.expressions[0]).lower().replace('"', '').replace('users.', '')
        sql = re.sub(r'\s+', '', sql).replace('::text', '').replace('btrim(', 'trim(').replace('trim(bothfrom', 'trim(')
        # Parenthesized cast operands are emitted by some supported PG versions.
        return sql in {'lower(trim(username))', 'lower(trim((username)))'}
    return expression(index) and expression(other)


def application_filters(connection):
    extension_tables = set()
    if connection.dialect.name == 'postgresql':
        from sqlalchemy import text
        extension_tables = set(connection.scalars(text("""
            SELECT c.relname FROM pg_class c JOIN pg_depend d ON d.objid=c.oid
            WHERE d.classid='pg_class'::regclass AND d.deptype='e'
              AND c.relkind IN ('r','p','v','m','f') AND pg_table_is_visible(c.oid)
        """)))
    def include_name(name, type_, parents):
        return not (type_ == 'table' and name in extension_tables)
    def include_object(obj, name, type_, reflected, compare_to):
        return not (type_ == 'index' and equivalent_username_index(obj, compare_to))
    return include_name, include_object

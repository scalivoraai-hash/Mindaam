from sqlalchemy import MetaData, Table, Column, String, Index, text
from backend.migrations.inspection import equivalent_username_index


def index(expression, unique=True, name='uq_users_username_normalized'):
    table=Table('users',MetaData(),Column('username',String(40)))
    return Index(name,text(expression),unique=unique,_table=table)


def test_postgres_trim_spelling_is_equivalent():
    model=index('lower(trim(users.username))')
    assert equivalent_username_index(model,index('lower(btrim((username)::text))'))
    assert equivalent_username_index(model,index('lower(TRIM(BOTH FROM username))'))


def test_real_index_drift_is_not_ignored():
    model=index('lower(trim(users.username))')
    assert not equivalent_username_index(model,None)
    assert not equivalent_username_index(model,index('lower(username)'))
    assert not equivalent_username_index(model,index('lower(trim(username))',unique=False))
    assert not equivalent_username_index(model,index('lower(trim(username))',name='another_index'))

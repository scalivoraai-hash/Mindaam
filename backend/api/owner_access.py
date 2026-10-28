"""Read-only owner inspection in the existing staging migration job.

Never prints credentials, email addresses, session hashes or other users' data.
This command cannot create users, grant roles or change passwords.
"""
import json
import os
from sqlalchemy import select, func, text
from .db import SessionLocal
from .models import User


def inspect(db, email):
    owners = list(db.scalars(select(User).where(User.role == 'super_admin')))
    target = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    return {
        'super_admin_count': len(owners),
        'requested_identity_exists': target is not None,
        'requested_identity_is_super_admin': bool(target and target.role == 'super_admin'),
        'requested_identity_verified': bool(target and target.verified),
        'requested_identity_suspended': bool(target and target.suspended),
        'requested_identity_requires_password_change': bool(target and target.must_change_password),
        'sole_owner_matches_requested_identity': bool(len(owners) == 1 and target and owners[0].id == target.id),
    }


def main():
    if os.getenv('APP_ENV') != 'staging':
        raise RuntimeError('Owner inspection is restricted to staging')
    with SessionLocal() as db:
        db.execute(text('SET TRANSACTION READ ONLY'))
        result = inspect(db, 'scalivoraai@gmail.com')
    print('MINDAAM_OWNER_INSPECTION ' + json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()

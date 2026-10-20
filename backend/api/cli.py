import argparse
import getpass
import os
from sqlalchemy import select
from .db import Base, engine, SessionLocal, APP_ENV
from .models import User, Collectible, Mission, Config
from . import commerce, identity, discovery, gameplay, subscriptions
from .auth import hash_password


def seed(db):
    if APP_ENV not in {"local", "test"}:
        raise RuntimeError("Seed prohibited outside local/test")
    from .core import CITIES
    from .expansion import seed_catalog
    seed_catalog(db)

    for city in CITIES:
        for i, (kind, x, z) in enumerate(
            [
                ("fruit", 0, -3),
                ("fruit", 4, -7),
                ("fruit", -4, -9),
                ("gem", 0, -12),
                ("fruit", 0, -20),
                ("gem", 0, -30),
                ("fruit", 8, 0),
                ("fruit", 18, 0),
                ("gem", 30, 0),
            ]
        ):
            id = city["id"] + "-local-" + str(i)
            if not db.get(Collectible, id):
                db.add(
                    Collectible(
                        id=id,
                        city=city["id"],
                        title=("Apple" if kind == "fruit" else "City Gem")
                        + " · local seed",
                        kind=kind,
                        x=x,
                        z=z,
                    )
                )
        id = city["id"] + "-first-harvest"
        if not db.get(Mission, id):
            db.add(
                Mission(
                    id=id,
                    city=city["id"],
                    title="First Harvest · local mission",
                    description="Collect 3 fruit and 1 gem in this simulated district.",
                    requirements={"fruit": 3, "gem": 1},
                    credits=30,
                    xp=50,
                )
            )
    defaults = {
        "welcome_pack": {"credits": 50, "xp": 20, "bike_days": 7},
        "daily_rewards": {"schedule": [10, 15, 20, 25, 30, 40, 75]},
        "vehicle_prices": {"bike": 10, "scooter": 20, "car": 30},
    }
    for key, value in defaults.items():
        if not db.get(Config, key):
            db.add(Config(key=key, value=value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["seed", "create-admin", "init-local", "mail-worker"]
    )
    parser.add_argument("--email")
    args = parser.parse_args()
    if args.command == "mail-worker":
        print(identity.drain_outbox(limit=20))
    elif args.command == "init-local":
        if APP_ENV not in {"local", "test"}:
            raise RuntimeError("Use Alembic migrations outside local/test")
        Base.metadata.create_all(engine)
    elif args.command == "seed":
        with SessionLocal.begin() as db:
            seed(db)
        print(
            "Local seed objects created. No human users or merchant performance fabricated."
        )
    else:
        if not args.email:
            parser.error("--email required")
        password = getpass.getpass("New administrator password (12+ characters): ")
        if len(password) < 12:
            raise ValueError("Use at least 12 characters")
        with SessionLocal.begin() as db:
            if db.scalar(select(User).where(User.email == args.email.lower())):
                raise ValueError("Account exists; refusing silent privilege escalation")
            db.add(
                User(
                    email=args.email.lower(),
                    username="admin-" + os.urandom(4).hex(),
                    password_hash=hash_password(password),
                    role="admin",
                    verified=True,
                )
            )
        print(
            "Administrator created. Sign in normally; complete onboarding then open /admin."
        )


if __name__ == "__main__":
    main()

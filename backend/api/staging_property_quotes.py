"""Scope two short-lived operator price overrides to a real public staging acceptance run.

This command has no HTTP route. The existing staging Cloud Run job invokes it
under GCP IAM. It never creates users, grants XP or writes an entitlement.
"""

import os
import re
import sys
import time
from sqlalchemy import select, text


def main(action, run_id, *ids):
    if os.environ.get("APP_ENV") != "staging" or not re.fullmatch(
        r"[0-9]{1,18}", run_id
    ):
        raise RuntimeError("Staging acceptance execution required")
    if len(ids) != 2 or {key.partition(":")[0] for key in ids} != {
        "london",
        "milton-keynes",
    }:
        raise RuntimeError("Expected one mapped building in each acceptance district")
    from sqlalchemy.engine import make_url

    url = make_url(os.environ["RUNTIME_DATABASE_URL"])
    if url.username != "mindaam_staging" or url.database != "mindaam_staging":
        raise RuntimeError("Unexpected staging runtime identity")
    os.environ["DATABASE_URL"] = os.environ["RUNTIME_DATABASE_URL"]
    from .db import SessionLocal
    from .property_economy import Price, Property
    from .models import Audit

    if action not in ("prepare", "restore"):
        raise ValueError("Unknown operation")
    with SessionLocal.begin() as db:
        if tuple(db.execute(text("SELECT current_database(),current_user")).one()) != (
            "mindaam_staging",
            "mindaam_staging",
        ):
            raise RuntimeError("PostgreSQL identity mismatch")
        for key in ids:
            p = db.scalar(select(Property).where(Property.id == key).with_for_update())
            if not p or p.category == "venue":
                raise RuntimeError("Mapped building required")
            old = db.get(Price, (p.id, p.category))
            marker = db.scalar(
                select(Audit)
                .where(Audit.action == "property.qa_quote", Audit.target == key)
                .order_by(Audit.created_at.desc())
                .limit(1)
            )
            if action == "prepare":
                if p.owner or old:
                    raise RuntimeError(
                        "Owner or price override already exists; refusing to overwrite"
                    )
                expires = time.time() + 900
                db.add(
                    Price(
                        scope=p.id,
                        category=p.category,
                        xp=5,
                        enabled=True,
                        expires=expires,
                    )
                )
                db.add(
                    Audit(
                        action="property.qa_quote",
                        target=key,
                        details={"run": run_id, "expires": expires, "xp": 5},
                    )
                )
            elif (
                marker
                and marker.details["run"] == run_id
                and old
                and old.expires == marker.details["expires"]
                and old.xp == 5
            ):
                db.delete(old)
                db.add(
                    Audit(
                        action="property.qa_quote_restored",
                        target=key,
                        details={"run": run_id},
                    )
                )
    print("Staging property quote operation completed.")


if __name__ == "__main__":
    main(*sys.argv[1:])

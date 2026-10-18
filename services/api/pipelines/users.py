"""`make seed-users`: demo accounts for the prototype (D30).

Passwords come from DEMO_PASSWORD_* environment variables, with documented demo defaults (see .env.example).
Re-running resets the passwords to the configured values.
"""

import os

from sqlalchemy import Connection, text

from app.core.db import get_engine
from app.core.passwords import hash_password

PLANTS = ["THAR1", "KGL-P2"]
ACCOUNTS = [
    # username, display name, role, env var, demo default
    ("engineer", "Performance Engineer", "engineer", "DEMO_PASSWORD_ENGINEER", "thar1-engineer"),
    ("operations", "O&M Manager", "operations", "DEMO_PASSWORD_OPERATIONS", "thar1-operations"),
    ("cfo", "Chief Financial Officer", "cfo", "DEMO_PASSWORD_CFO", "thar1-cfo"),
    ("presenter", "Presenter (all views)", "presenter", "DEMO_PASSWORD_PRESENTER", "thar1-presenter"),
]


def seed(conn: Connection) -> list[str]:
    for username, name, role, env, default in ACCOUNTS:
        conn.execute(
            text(
                "INSERT INTO app_user (username, display_name, role, plants, password_hash) "
                "VALUES (:u, :n, :r, :p, :h) ON CONFLICT (username) DO UPDATE SET "
                "display_name = EXCLUDED.display_name, role = EXCLUDED.role, plants = EXCLUDED.plants, "
                "password_hash = EXCLUDED.password_hash, active = true"
            ),
            {"u": username, "n": name, "r": role, "p": PLANTS, "h": hash_password(os.environ.get(env, default))},
        )
    return [a[0] for a in ACCOUNTS]


def run(_args=None) -> None:
    with get_engine().begin() as conn:
        users = seed(conn)
    print(f"seeded users: {', '.join(users)} (passwords from DEMO_PASSWORD_* or the demo defaults)")

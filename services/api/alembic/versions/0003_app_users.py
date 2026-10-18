"""Prototype login: app_user table with scrypt password hashes (D30). Role and plant scope live here and go into the
JWT; the API reads the role only from the token.

Revision ID: 0003_app_users
Revises: 0002_timeseries_engines
Create Date: 2026-10-18
"""

from alembic import op

revision = "0003_app_users"
down_revision = "0002_timeseries_engines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE app_user (
  username      text PRIMARY KEY,
  display_name  text NOT NULL,
  role          text NOT NULL CHECK (role IN ('engineer','operations','cfo','presenter')),
  plants        text[] NOT NULL,
  password_hash text NOT NULL,
  active        boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz
);
""")


def downgrade() -> None:
    op.execute("DROP TABLE app_user;")

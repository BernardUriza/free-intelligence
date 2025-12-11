#!/usr/bin/env python3
"""Migration: Add auth0_user_id and clinic_role to doctors table.

This migration adds the following columns to the doctors table:
- auth0_user_id: Links a doctor record to an Auth0 user
- email: Cached email from Auth0 for display
- clinic_role: Role within the clinic (owner, admin, doctor, staff)

Usage:
    python -m backend.scripts.migrate_doctor_auth0

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from backend.database import engine


def migrate() -> None:
    """Add auth0_user_id, email, and clinic_role columns to doctors table."""
    print("🔄 Running migration: Add auth0 linking to doctors table...")

    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'doctors' AND column_name = 'auth0_user_id'
            """)
        )
        if result.fetchone():
            print("✅ Column auth0_user_id already exists, skipping...")
            return

        # Create the clinic_role enum type if it doesn't exist
        print("   Creating clinic_role enum type...")
        conn.execute(
            text("""
                DO $$ BEGIN
                    CREATE TYPE clinicrole AS ENUM ('owner', 'admin', 'doctor', 'staff');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
        )
        conn.commit()

        # Add columns one by one with commits
        print("   Adding auth0_user_id column...")
        conn.execute(
            text("""
                ALTER TABLE doctors
                ADD COLUMN IF NOT EXISTS auth0_user_id VARCHAR(255) UNIQUE
            """)
        )
        conn.commit()

        print("   Adding email column...")
        conn.execute(
            text("""
                ALTER TABLE doctors
                ADD COLUMN IF NOT EXISTS email VARCHAR(255)
            """)
        )
        conn.commit()

        print("   Adding clinic_role column...")
        conn.execute(
            text("""
                ALTER TABLE doctors
                ADD COLUMN IF NOT EXISTS clinic_role clinicrole DEFAULT 'doctor'
            """)
        )
        conn.commit()

        # Create index on auth0_user_id
        print("   Creating index on auth0_user_id...")
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_doctors_auth0_user_id
                ON doctors (auth0_user_id)
            """)
        )
        conn.commit()

    print("✅ Migration completed successfully!")
    print("   - Added: auth0_user_id (VARCHAR(255), UNIQUE)")
    print("   - Added: email (VARCHAR(255))")
    print("   - Added: clinic_role (ENUM: owner, admin, doctor, staff)")


def rollback() -> None:
    """Remove auth0_user_id, email, and clinic_role columns from doctors table."""
    print("🔄 Rolling back migration...")

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE doctors DROP COLUMN IF EXISTS auth0_user_id"))
        conn.execute(text("ALTER TABLE doctors DROP COLUMN IF EXISTS email"))
        conn.execute(text("ALTER TABLE doctors DROP COLUMN IF EXISTS clinic_role"))
        conn.execute(text("DROP TYPE IF EXISTS clinicrole"))
        conn.commit()

    print("✅ Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate doctors table for Auth0 linking")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()

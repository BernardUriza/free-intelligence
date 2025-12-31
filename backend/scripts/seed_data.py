"""Seed data script for production database.

Creates initial demo data for Aurity:
- Demo clinic with basic settings
- Demo doctor associated with the clinic

Usage:
    PYTHONPATH=/opt/free-intelligence DATABASE_URL=sqlite:///./data/aurity.db \
        python3 -m backend.scripts.seed_data

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import os
from backend.models.checkin_models import Clinic, ClinicRole, Doctor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Constants for demo data
DEMO_CLINIC_ID = "11111111-1111-1111-1111-111111111111"
DEMO_DOCTOR_ID = "22222222-2222-2222-2222-222222222222"


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    print(f"📦 Using database: {url}")
    return url


def seed_demo_clinic(session) -> Clinic:
    """Create or update demo clinic."""
    existing = session.query(Clinic).filter_by(clinic_id=DEMO_CLINIC_ID).first()

    if existing:
        print(f"✅ Demo clinic already exists: {existing.name}")
        return existing

    clinic = Clinic(
        clinic_id=DEMO_CLINIC_ID,
        name="Clínica Demo AURITY",
        specialty="General",
        timezone="America/Mexico_City",
        primary_color="#6366f1",
        welcome_message="Bienvenido a la Clínica Demo de AURITY. Este es un entorno de demostración.",
        checkin_qr_enabled=True,
        chat_enabled=True,
        payments_enabled=False,
        whatsapp_enabled=False,
        subscription_plan="professional",
        subscription_valid_until=datetime.now(timezone.utc) + timedelta(days=365),  # noqa: UP017
        is_active=True,
    )

    session.add(clinic)
    print(f"🏥 Created demo clinic: {clinic.name}")
    return clinic


def seed_demo_doctor(session, clinic: Clinic) -> Doctor:
    """Create or update demo doctor."""
    existing = session.query(Doctor).filter_by(doctor_id=DEMO_DOCTOR_ID).first()

    if existing:
        # Use getattr for safe attribute access
        name = getattr(existing, "nombre", "") or ""
        surname = getattr(existing, "apellido", "") or ""
        print(f"✅ Demo doctor already exists: {name} {surname}".strip())
        return existing

    doctor = Doctor(
        doctor_id=DEMO_DOCTOR_ID,
        clinic_id=clinic.clinic_id,
        nombre="María",
        apellido="García Demo",
        email="demo@aurity.io",
        clinic_role=ClinicRole.OWNER,
        especialidad="Medicina General",
        display_name="Dra. García",
        cedula_profesional="DEMO123456",
        avg_consultation_minutes=30,
        work_start_time="09:00",
        work_end_time="18:00",
        working_hours={
            "monday": {"start": "09:00", "end": "18:00"},
            "tuesday": {"start": "09:00", "end": "18:00"},
            "wednesday": {"start": "09:00", "end": "18:00"},
            "thursday": {"start": "09:00", "end": "18:00"},
            "friday": {"start": "09:00", "end": "14:00"},
        },
        is_active=True,
    )

    session.add(doctor)
    print(f"👨‍⚕️ Created demo doctor: {doctor.display_name}")
    return doctor


def run_seed() -> None:
    """Run all seed operations."""
    print("🌱 Starting seed data script...")
    print("=" * 50)

    database_url = get_database_url()
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # Create demo data
        clinic = seed_demo_clinic(session)
        _doctor = seed_demo_doctor(session, clinic)

        session.commit()
        print("=" * 50)
        print("✅ Seed data completed successfully!")
        print(f"   Clinic ID: {DEMO_CLINIC_ID}")
        print(f"   Doctor ID: {DEMO_DOCTOR_ID}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error during seed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()

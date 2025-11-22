#!/usr/bin/env python3
"""Initialize Check-in database tables and seed demo data.

Creates all tables for FI Receptionist and optionally seeds demo data
for testing the check-in flow.

Usage:
    python -m backend.scripts.init_checkin_db [--seed]

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-001
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal, engine
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    Clinic,
    Doctor,
    PendingAction,
    PendingActionType,
)
from backend.models.db_models import Base, Patient


def create_tables() -> None:
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")

    # List tables
    tables = list(Base.metadata.tables.keys())
    print(f"   Tables: {', '.join(tables)}")


def seed_demo_data() -> None:
    """Seed demo data for testing."""
    print("\nSeeding demo data...")

    db = SessionLocal()
    try:
        # Check if demo clinic already exists
        existing = db.query(Clinic).filter(Clinic.name == "Clínica Demo AURITY").first()
        if existing:
            print("⚠️  Demo data already exists. Skipping seed.")
            return

        # 1. Create demo clinic
        clinic = Clinic(
            name="Clínica Demo AURITY",
            specialty="general",
            timezone="America/Mexico_City",
            welcome_message="¡Bienvenido a Clínica Demo!",
            primary_color="#6366f1",
            checkin_qr_enabled=True,
            chat_enabled=True,
            payments_enabled=True,
            subscription_plan="professional",
        )
        db.add(clinic)
        db.flush()  # Get clinic_id
        print(f"   ✅ Clinic: {clinic.name} ({clinic.clinic_id})")

        # 2. Create demo doctors
        doctors = [
            Doctor(
                clinic_id=clinic.clinic_id,
                nombre="Carlos",
                apellido="López Hernández",
                display_name="Dr. López",
                especialidad="Medicina General",
                cedula_profesional="12345678",
                avg_consultation_minutes=20,
            ),
            Doctor(
                clinic_id=clinic.clinic_id,
                nombre="Ana",
                apellido="García Martínez",
                display_name="Dra. García",
                especialidad="Pediatría",
                cedula_profesional="87654321",
                avg_consultation_minutes=25,
            ),
        ]
        for doc in doctors:
            db.add(doc)
        db.flush()
        print(f"   ✅ Doctors: {len(doctors)} created")

        # 3. Create demo patients
        patients = [
            Patient(
                nombre="María",
                apellido="González Ramírez",
                fecha_nacimiento=datetime(1985, 3, 15),
                curp="GORM850315MDFRML09",
            ),
            Patient(
                nombre="Juan",
                apellido="Pérez Sánchez",
                fecha_nacimiento=datetime(1990, 7, 22),
                curp="PESJ900722HDFRNN01",
            ),
            Patient(
                nombre="Carmen",
                apellido="Rodríguez López",
                fecha_nacimiento=datetime(1978, 11, 8),
                curp="ROLC781108MDFDRR05",
            ),
        ]
        for p in patients:
            db.add(p)
        db.flush()
        print(f"   ✅ Patients: {len(patients)} created")

        # 4. Create demo appointments for today
        now = datetime.now(UTC)
        today_10am = now.replace(hour=10, minute=0, second=0, microsecond=0)
        today_11am = now.replace(hour=11, minute=0, second=0, microsecond=0)
        today_12pm = now.replace(hour=12, minute=0, second=0, microsecond=0)

        appointments = [
            Appointment(
                clinic_id=clinic.clinic_id,
                patient_id=patients[0].patient_id,
                doctor_id=doctors[0].doctor_id,
                scheduled_at=today_10am,
                appointment_type=AppointmentType.FOLLOW_UP,
                status=AppointmentStatus.SCHEDULED,
                checkin_code="123456",
                checkin_code_expires_at=now.replace(hour=23, minute=59),
                reason="Control de presión arterial",
            ),
            Appointment(
                clinic_id=clinic.clinic_id,
                patient_id=patients[1].patient_id,
                doctor_id=doctors[1].doctor_id,
                scheduled_at=today_11am,
                appointment_type=AppointmentType.FIRST_VISIT,
                status=AppointmentStatus.SCHEDULED,
                checkin_code="234567",
                checkin_code_expires_at=now.replace(hour=23, minute=59),
                reason="Primera consulta pediátrica",
            ),
            Appointment(
                clinic_id=clinic.clinic_id,
                patient_id=patients[2].patient_id,
                doctor_id=doctors[0].doctor_id,
                scheduled_at=today_12pm,
                appointment_type=AppointmentType.PROCEDURE,
                status=AppointmentStatus.CONFIRMED,
                checkin_code="345678",
                checkin_code_expires_at=now.replace(hour=23, minute=59),
                reason="Aplicación de vacuna",
            ),
        ]
        for appt in appointments:
            db.add(appt)
        db.flush()
        print(f"   ✅ Appointments: {len(appointments)} created for today")

        # 5. Create pending actions for appointments
        actions = [
            # María - needs to pay copay and sign consent
            PendingAction(
                appointment_id=appointments[0].appointment_id,
                action_type=PendingActionType.PAY_COPAY,
                title="Pagar copago",
                description="Copago de consulta de seguimiento",
                icon="💳",
                is_required=True,
                is_blocking=True,
                amount=150.00,
                currency="MXN",
            ),
            PendingAction(
                appointment_id=appointments[0].appointment_id,
                action_type=PendingActionType.SIGN_CONSENT,
                title="Firmar consentimiento",
                description="Consentimiento informado para procedimiento",
                icon="✍️",
                is_required=True,
                is_blocking=False,
                document_url="/documents/consent-general.pdf",
            ),
            # Juan - first visit, needs to fill questionnaire
            PendingAction(
                appointment_id=appointments[1].appointment_id,
                action_type=PendingActionType.FILL_QUESTIONNAIRE,
                title="Cuestionario inicial",
                description="Historial médico del paciente",
                icon="📋",
                is_required=True,
                is_blocking=False,
            ),
            PendingAction(
                appointment_id=appointments[1].appointment_id,
                action_type=PendingActionType.SIGN_PRIVACY,
                title="Aviso de privacidad",
                description="Firmar aviso de privacidad",
                icon="🔒",
                is_required=True,
                is_blocking=False,
                document_url="/documents/privacy-notice.pdf",
            ),
            # Carmen - needs to upload lab results
            PendingAction(
                appointment_id=appointments[2].appointment_id,
                action_type=PendingActionType.UPLOAD_LABS,
                title="Subir laboratorios",
                description="Resultados de análisis de sangre",
                icon="🧪",
                is_required=False,
                is_blocking=False,
            ),
        ]
        for action in actions:
            db.add(action)
        print(f"   ✅ Pending Actions: {len(actions)} created")

        db.commit()
        print("\n✅ Demo data seeded successfully!")

        # Print summary for testing
        print("\n" + "=" * 50)
        print("DEMO CHECK-IN CODES (valid today):")
        print("=" * 50)
        for i, appt in enumerate(appointments):
            patient = patients[i]
            print(f"  {patient.nombre} {patient.apellido}: {appt.checkin_code}")
        print("\nCURP for testing:")
        for p in patients:
            print(f"  {p.nombre}: {p.curp}")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Check-in database tables and seed demo data"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed demo data for testing",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating (DANGEROUS!)",
    )
    args = parser.parse_args()

    if args.drop:
        confirm = input("⚠️  This will DELETE ALL DATA. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            print("Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            print("✅ Tables dropped.")
        else:
            print("Cancelled.")
            return

    create_tables()

    if args.seed:
        seed_demo_data()


if __name__ == "__main__":
    main()

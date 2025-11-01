#!/usr/bin/env python3
"""
Free Intelligence — Outreach Email Tool (Mail-Merge)
Card: FI-GTM-STR-027
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# Email Templates
EMAIL_TEMPLATES = {
    "initial_outreach": {
        "subject": "FI-Entry: Piloto 60 días para documentación clínica local (sin PHI)",
        "body": """Estimado/a {{contact_name}},

Mi nombre es {{sender_name}} de Free Intelligence. Me permito contactarle porque {{company_name}} podría beneficiarse de nuestra solución FI-Entry para mejorar la gestión de documentación clínica.

**¿Qué es FI-Entry?**
Piloto de 60 días para ingestión local de documentos no sensibles (cartas, referencias, estudios) con métricas de rendimiento en tiempo real.

**Diferenciadores clave:**
• 100% on-premise (sin internet después de instalación)
• Instalación en hardware existente (DELL, HP, Synology)
• $3,000 USD flat fee (10x más barato que EMR tradicional)
• Sin contrato multi-año (solo 60 días piloto)
• Instalación en 1 semana vs 3-6 meses de EMR

**¿Por qué {{company_name}}?**
{{notes}}

**Próximo paso:**
¿Tendría disponibilidad para una llamada de 15 minutos esta semana? Puedo compartir demos y responder preguntas.

Calendario: {{calendar_link}}
O responda este email con su disponibilidad.

Saludos cordiales,
{{sender_name}}
{{sender_title}}
Free Intelligence
{{sender_email}}
{{sender_phone}}

P.D. Adjunto: One-pager con detalles técnicos y pricing.
""",
    },
    "follow_up": {
        "subject": "Re: FI-Entry piloto — ¿Tuvo oportunidad de revisar?",
        "body": """Estimado/a {{contact_name}},

Le escribí hace {{days_since_last}} días sobre FI-Entry, nuestro piloto de 60 días para documentación clínica local.

Entiendo que está ocupado/a, así que seré breve:

**FI-Entry en 3 puntos:**
1. Instalación en 1 semana en servidor local ({{company_name}} proporciona hardware)
2. Dashboard con métricas de rendimiento en tiempo real
3. $3,000 USD flat fee (sin costos recurrentes)

**¿Le interesa una demo de 15 minutos?**
Calendario: {{calendar_link}}

Si no es un buen momento, ¿me podría referir a quien sea responsable de IT/operaciones?

Saludos,
{{sender_name}}
Free Intelligence
""",
    },
    "demo_scheduled": {
        "subject": "Confirmación: Demo FI-Entry el {{demo_date}}",
        "body": """Estimado/a {{contact_name}},

Confirmando nuestra demo de FI-Entry:

**Fecha:** {{demo_date}}
**Hora:** {{demo_time}}
**Duración:** 30 minutos
**Formato:** Videollamada (Zoom/Google Meet)
**Link:** {{demo_link}}

**Agenda:**
1. Overview FI-Entry (5 min)
2. Demo en vivo (15 min)
   • Dashboard con métricas
   • Ingestión de documentos
   • Export con SHA256 verification
3. Q&A (10 min)

**Preparación (opcional):**
Si desea, puede revisar el one-pager adjunto antes de la llamada.

**¿Necesita algo más?**
Por favor confirme asistencia respondiendo este email.

Nos vemos el {{demo_date}},
{{sender_name}}
Free Intelligence
{{sender_email}}
{{sender_phone}}
""",
    },
}


def load_leads(csv_path: Path) -> list[dict]:
    """Load leads from CSV file."""
    leads = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    return leads


def generate_email(
    template_name: str, lead: dict, sender_config: dict, extra_vars: dict = None
) -> dict:
    """Generate personalized email from template."""
    if template_name not in EMAIL_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")

    template = EMAIL_TEMPLATES[template_name]

    # Merge variables
    variables = {
        **lead,
        **sender_config,
        **(extra_vars or {}),
    }

    # Replace placeholders
    subject = template["subject"]
    body = template["body"]

    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value))
        body = body.replace(placeholder, str(value))

    return {
        "to": lead["email"],
        "subject": subject,
        "body": body,
        "lead_id": lead["lead_id"],
        "company_name": lead["company_name"],
    }


def filter_leads(leads: list[dict], status: str = None, limit: int = None) -> list[dict]:
    """Filter leads by status and limit."""
    filtered = leads

    if status:
        filtered = [lead for lead in filtered if lead["status"] == status]

    if limit:
        filtered = filtered[:limit]

    return filtered


def save_emails(emails: list[dict], output_path: Path):
    """Save generated emails to file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Generated Emails - {datetime.now().isoformat()}\n")
        f.write(f"# Total: {len(emails)}\n\n")

        for i, email in enumerate(emails, 1):
            f.write(f"## Email {i}/{len(emails)}\n")
            f.write(f"**Lead ID:** {email['lead_id']}\n")
            f.write(f"**Company:** {email['company_name']}\n")
            f.write(f"**To:** {email['to']}\n")
            f.write(f"**Subject:** {email['subject']}\n\n")
            f.write("**Body:**\n")
            f.write(email["body"])
            f.write("\n\n")
            f.write("-" * 80)
            f.write("\n\n")


def print_summary(emails: list[dict]):
    """Print summary of generated emails."""
    print("=" * 80)
    print("Free Intelligence — Outreach Email Summary")
    print("=" * 80)
    print()
    print(f"📧 Total emails generated: {len(emails)}")
    print()
    print("Recipients:")
    for i, email in enumerate(emails, 1):
        print(f"  {i}. {email['company_name']} ({email['to']})")
    print()
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate personalized outreach emails")
    parser.add_argument(
        "--template",
        choices=["initial_outreach", "follow_up", "demo_scheduled"],
        required=True,
        help="Email template to use",
    )
    parser.add_argument(
        "--leads",
        type=Path,
        default=Path("sales/entry/leads.csv"),
        help="Path to leads CSV file",
    )
    parser.add_argument(
        "--status",
        choices=["new", "contacted", "demo_scheduled", "qualified", "lost"],
        help="Filter leads by status",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of emails to generate",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sales/entry/generated_emails.txt"),
        help="Output file for generated emails",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview emails without saving",
    )

    args = parser.parse_args()

    # Sender configuration (would come from config file in production)
    sender_config = {
        "sender_name": "Bernard Uriza",
        "sender_title": "CEO",
        "sender_email": "bernard@free-intelligence.com",
        "sender_phone": "+52 55 1234 5678",
        "calendar_link": "https://calendly.com/free-intelligence/15min",
    }

    # Extra variables for specific templates
    extra_vars = {}
    if args.template == "follow_up":
        extra_vars["days_since_last"] = "7"
    elif args.template == "demo_scheduled":
        extra_vars["demo_date"] = "2025-11-20"
        extra_vars["demo_time"] = "10:00 AM"
        extra_vars["demo_link"] = "https://meet.google.com/abc-defg-hij"

    # Load leads
    print(f"Loading leads from: {args.leads}")
    leads = load_leads(args.leads)
    print(f"✅ Loaded {len(leads)} leads")

    # Filter leads
    filtered_leads = filter_leads(leads, status=args.status, limit=args.limit)
    print(f"✅ Filtered to {len(filtered_leads)} leads")

    if len(filtered_leads) == 0:
        print("⚠️  No leads match filters. Exiting.")
        return 1

    # Generate emails
    emails = []
    for lead in filtered_leads:
        email = generate_email(args.template, lead, sender_config, extra_vars)
        emails.append(email)

    # Print summary
    print_summary(emails)

    # Save or preview
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - Emails not saved")
        print(f"Would save to: {args.output}")
    else:
        save_emails(emails, args.output)
        print(f"\n💾 Emails saved to: {args.output}")
        print("\n✅ Next steps:")
        print("  1. Review generated emails")
        print("  2. Copy-paste into email client (or use SMTP in production)")
        print("  3. Update leads.csv status after sending")

    return 0


if __name__ == "__main__":
    sys.exit(main())

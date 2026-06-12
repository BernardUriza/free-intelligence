"""Tests for guild_setup: fact classifier, cyberpunk formatter, channel posting."""

from personas.insult.core.guild_setup import (
    filter_safe_facts,
    format_fact_logged,
    format_reminder_delivered,
    format_reminder_set,
    is_fact_safe,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fact Sensitivity Classifier
# ═══════════════════════════════════════════════════════════════════════════


class TestFactSensitivity:
    def test_safe_categories_always_pass(self):
        """Non-personal categories are always safe."""
        for cat in ("identity", "profession", "location", "interests", "technical", "preferences"):
            fact = {"fact": "Some random fact", "category": cat}
            assert is_fact_safe(fact) is True

    def test_personal_safe_content(self):
        """Personal facts without sensitive keywords are safe."""
        fact = {"fact": "Tiene un gato llamado Michi", "category": "personal"}
        assert is_fact_safe(fact) is True

    def test_health_filtered(self):
        """Health-related facts are filtered."""
        cases = [
            {"fact": "Tiene cita con el doctor el viernes", "category": "personal"},
            {"fact": "Sufre de ansiedad", "category": "personal"},
            {"fact": "Va al psicólogo cada semana", "category": "personal"},
            {"fact": "Le recetaron medicamento nuevo", "category": "personal"},
            {"fact": "Tiene cita con el gastro", "category": "personal"},
        ]
        for fact in cases:
            assert is_fact_safe(fact) is False, f"Should be sensitive: {fact['fact']}"

    def test_finance_filtered(self):
        """Finance-related facts are filtered."""
        cases = [
            {"fact": "Tiene deudas con el banco", "category": "personal"},
            {"fact": "Lo despidieron del trabajo", "category": "personal"},
            {"fact": "Su salario es de 50k", "category": "personal"},
        ]
        for fact in cases:
            assert is_fact_safe(fact) is False, f"Should be sensitive: {fact['fact']}"

    def test_relationship_filtered(self):
        """Relationship/sexuality facts are filtered."""
        cases = [
            {"fact": "Tiene novia nueva", "category": "personal"},
            {"fact": "Se divorció hace poco", "category": "personal"},
        ]
        for fact in cases:
            assert is_fact_safe(fact) is False, f"Should be sensitive: {fact['fact']}"

    def test_beliefs_filtered(self):
        """Political/religious beliefs are filtered."""
        cases = [
            {"fact": "Es ateo declarado", "category": "personal"},
            {"fact": "Va a la iglesia los domingos", "category": "personal"},
        ]
        for fact in cases:
            assert is_fact_safe(fact) is False, f"Should be sensitive: {fact['fact']}"

    def test_emotional_distress_filtered(self):
        """Emotional distress facts are filtered."""
        fact = {"fact": "Mencionó que tiene trauma de la infancia", "category": "personal"}
        assert is_fact_safe(fact) is False

    def test_general_safe_content(self):
        """General category with safe content passes."""
        fact = {"fact": "Le gusta el café con leche", "category": "general"}
        assert is_fact_safe(fact) is True

    def test_general_sensitive_content(self):
        """General category with sensitive content is filtered."""
        fact = {"fact": "Fue al hospital ayer", "category": "general"}
        assert is_fact_safe(fact) is False

    def test_filter_safe_facts_mixed(self):
        """filter_safe_facts returns only safe facts from a mixed list."""
        facts = [
            {"fact": "Es programador", "category": "profession"},
            {"fact": "Tiene cita con el doctor", "category": "personal"},
            {"fact": "Le gusta Python", "category": "technical"},
            {"fact": "Sufre de ansiedad", "category": "personal"},
            {"fact": "Vive en CDMX", "category": "location"},
        ]
        safe = filter_safe_facts(facts)
        assert len(safe) == 3
        assert all(f["fact"] in ("Es programador", "Le gusta Python", "Vive en CDMX") for f in safe)


# ═══════════════════════════════════════════════════════════════════════════
# Cyberpunk Formatter
# ═══════════════════════════════════════════════════════════════════════════


class TestCyberpunkFormatter:
    def test_format_fact_logged(self):
        """Fact log message has cyberpunk formatting."""
        facts = [{"fact": "Le gusta Python", "category": "technical"}]
        msg = format_fact_logged("bernard2389", facts, "general")
        assert "░▒▓ FACT LOGGED ▓▒░" in msg
        assert "bernard2389" in msg
        assert "Le gusta Python" in msg
        assert "#general" in msg
        assert "╚" in msg

    def test_format_fact_logged_multiple(self):
        """Multiple facts in one message."""
        facts = [
            {"fact": "Es programador", "category": "profession"},
            {"fact": "Vive en CDMX", "category": "location"},
        ]
        msg = format_fact_logged("alex", facts)
        assert msg.count("║") >= 3  # subject + 2 facts + timestamp

    def test_format_reminder_set(self):
        """Reminder set message has cyberpunk formatting."""
        msg = format_reminder_set(
            "ir al gym",
            "vie 18/04 · 14:30 CST",
            user_mentions="<@123>",
            recurring="none",
            reminder_id=42,
        )
        assert "░▒▓ REMINDER SET ▓▒░" in msg
        assert "#42" in msg
        assert "<@123>" in msg
        assert "ir al gym" in msg
        assert "recurring" not in msg  # none should not show

    def test_format_reminder_set_recurring(self):
        """Recurring reminders show the recurrence type."""
        msg = format_reminder_set("standup", "09:00 CST", recurring="daily")
        assert "recurring: daily" in msg

    def test_format_reminder_delivered(self):
        """Delivered reminder message has cyberpunk formatting."""
        msg = format_reminder_delivered("ir al gym", user_mentions="<@123>", reminder_id=42)
        assert "▓▒░ DELIVERED ░▒▓" in msg
        assert "ir al gym" in msg
        assert "SENT ✓" in msg
        assert "#42" in msg

    def test_format_reminder_delivered_no_mention(self):
        """Delivered without mentions still formats correctly."""
        msg = format_reminder_delivered("hacer tarea")
        assert "▓▒░ DELIVERED ░▒▓" in msg
        assert "hacer tarea" in msg

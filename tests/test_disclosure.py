"""Tests for insult.cogs.chat.disclosure — pre-LLM disclosure detection."""

from insult.cogs.chat.disclosure import scan_disclosure


class TestScanDisclosure:
    """Test the regex-based disclosure scanner."""

    # --- No disclosure ---

    def test_no_disclosure(self):
        result = scan_disclosure("hola que tal, como estas")
        assert result.detected is False
        assert result.category == "none"
        assert result.severity == 0
        assert result.signals == []
        assert result.should_override_preset is False

    # --- Health ---

    def test_health_diagnosis(self):
        result = scan_disclosure("me diagnosticaron VIH en 2019")
        assert result.detected is True
        assert result.category == "health"
        assert result.severity >= 3
        assert any("diagnosis" in s for s in result.signals)

    def test_health_medication(self):
        result = scan_disclosure("tomo sertralina y quetiapina")
        assert result.detected is True
        assert result.category == "health"
        assert result.severity >= 2
        assert any("medication" in s or "sertralina" in s or "specific" in s for s in result.signals)

    def test_medication_names(self):
        """Specific medication names trigger health category."""
        for med in ["sertralina", "quetiapina", "fluoxetina", "clonazepam", "escitalopram"]:
            result = scan_disclosure(f"estoy tomando {med}")
            assert result.detected is True, f"Failed for {med}"
            assert any("specific_medication" in s for s in result.signals), f"No med signal for {med}"

    # --- Crisis ---

    def test_crisis_suicidal(self):
        result = scan_disclosure("me quiero morir")
        assert result.detected is True
        assert result.category == "crisis"
        assert result.severity == 5
        assert result.should_override_preset is True

    def test_crisis_acute(self):
        result = scan_disclosure("estuve al borde del internamiento")
        assert result.detected is True
        assert result.category == "crisis"
        assert result.severity >= 4
        assert result.should_override_preset is True

    # --- Identity ---

    def test_identity_coming_out(self):
        result = scan_disclosure("soy bisexual")
        assert result.detected is True
        assert result.category == "identity"
        assert result.severity == 2
        assert any("coming_out" in s for s in result.signals)

    # --- Abuse ---

    def test_abuse_domestic(self):
        result = scan_disclosure("mi pareja me golpea")
        assert result.detected is True
        assert result.category == "abuse"
        assert result.severity >= 3
        assert result.should_override_preset is True

    # --- Grief ---

    def test_grief_recent(self):
        result = scan_disclosure("mi abuela acaba de morir")
        assert result.detected is True
        assert result.category == "grief"
        assert result.severity >= 3

    # --- Override logic ---

    def test_severity_override(self):
        """Severity >= 3 sets should_override_preset=True."""
        result = scan_disclosure("me quiero morir, ya no puedo mas")
        assert result.severity >= 3
        assert result.should_override_preset is True

    def test_severity_low(self):
        """Severity 1-2 does NOT override preset."""
        result = scan_disclosure("soy gay")
        assert result.detected is True
        assert result.severity <= 2
        assert result.should_override_preset is False

    # --- English patterns ---

    def test_english_patterns(self):
        result = scan_disclosure("I was diagnosed with depression")
        assert result.detected is True
        assert result.category == "health"
        assert result.severity >= 2

    # --- Multiple categories ---

    def test_multiple_categories(self):
        """When multiple categories match, highest severity wins."""
        result = scan_disclosure("soy bisexual y me quiero morir")
        assert result.detected is True
        # Crisis (severity 5) should win over identity (severity 2)
        assert result.category == "crisis"
        assert result.severity == 5
        assert result.should_override_preset is True
        # Both signals should be present
        assert len(result.signals) >= 2

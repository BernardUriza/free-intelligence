"""Example of using the unified prompt system that combines both new templates and YAML presets."""

from backend.src.fi_prompts import get_enhanced_prompt


def example_usage():
    """Example of how to use the unified prompt provider."""
    
    print("Example 1: Using new template-based prompt")
    medical_prompt = get_enhanced_prompt(
        "medical_consultation",
        demographics="45-year-old female",
        chief_complaint="Headache and dizziness",
        medications="Ibuprofen as needed, Lisinopril 10mg",
        allergies="Sulfa drugs (rash)",
    )
    print(medical_prompt)
    print("\n" + "="*70 + "\n")
    
    print("Example 2: Using YAML preset (intake_coach)")
    intake_prompt = get_enhanced_prompt(
        "intake_coach",
        patient_input="I have chest pain",
        urgency_level="MODERATE"
    )
    print(intake_prompt[:500] + "...")  # Truncate for display
    print("\n" + "="*70 + "\n")
    
    print("Example 3: Using SOAP generator YAML preset")
    soap_prompt = get_enhanced_prompt(
        "soap_generator",
        chief_complaint="Annual wellness exam",
        history="Patient reports feeling well, no new concerns"
    )
    print(soap_prompt[:500] + "...")  # Truncate for display


if __name__ == "__main__":
    example_usage()
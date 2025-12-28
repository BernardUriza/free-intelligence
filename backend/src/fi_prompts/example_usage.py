"""Example usage of the prompt provider in an application context."""

from backend.src.fi_prompts.prompt_provider import get_available_prompts, get_prompt


def example_usage():
    """Example of how to use the prompt provider in application code."""

    # Print available prompts
    print("Available prompts:")
    for prompt_type in get_available_prompts():
        print(f"  - {prompt_type}")
    print()

    # Example 1: Get a medical consultation prompt with parameters
    print("Example 1: Medical Consultation Prompt")
    medical_prompt = get_prompt(
        "medical_consultation",
        demographics="45-year-old female",
        chief_complaint="Headache and dizziness",
        medications="Ibuprofen as needed, Lisinopril 10mg",
        allergies="Sulfa drugs (rash)",
    )
    print(medical_prompt)
    print("\n" + "=" * 50 + "\n")

    # Example 2: Get a patient intake prompt
    print("Example 2: Patient Intake Prompt")
    intake_prompt = get_prompt(
        "patient_intake",
        name="Jane Smith",
        age="34",
        gender="Female",
        contact="555-0123",
        chief_complaint="Sore throat",
        duration="3 days",
        medications="None",
        allergies="None known",
        symptoms="Sore throat, mild fever, difficulty swallowing",
        severity="Moderate",
    )
    print(intake_prompt)
    print("\n" + "=" * 50 + "\n")

    # Example 3: Get a SOAP note prompt
    print("Example 3: SOAP Note Prompt")
    soap_prompt = get_prompt(
        "soap_note",
        chief_complaint="Annual wellness exam",
        history="Patient reports feeling well, no new concerns",
        ros="All other systems negative",
        vitals="BP: 120/80, HR: 72, Temp: 98.6",
        examination="General: Well-appearing female in no acute distress",
        results="HbA1c: 5.8, Lipid panel within normal limits",
        primary_diagnosis="Wellness exam",
        differential_diagnoses="None",
        severity="Stable",
        treatments="None",
        medications="None",
        follow_up="Annual exam in 1 year",
        education="Continue healthy lifestyle",
    )
    print(soap_prompt)


if __name__ == "__main__":
    example_usage()

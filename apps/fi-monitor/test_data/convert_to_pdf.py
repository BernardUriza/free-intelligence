#!/usr/bin/env python3.14
"""
Convert sample medical note text to PDF.
Requires: pip install reportlab
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_pdf():
    """Convert sample_medical_note.txt to PDF."""
    input_file = "sample_medical_note.txt"
    output_file = "sample_medical_note.pdf"

    # Read text
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Create PDF
    c = canvas.Canvas(output_file, pagesize=letter)
    width, height = letter

    # Starting position
    y = height - 50

    # Write text line by line
    for line in text.split('\n'):
        if y < 50:  # New page if running out of space
            c.showPage()
            y = height - 50

        c.drawString(50, y, line)
        y -= 15

    c.save()
    print(f"✅ PDF created: {output_file}")

if __name__ == "__main__":
    try:
        create_pdf()
    except ImportError:
        print("⚠️  reportlab not installed. Install with:")
        print("   pip install reportlab")
        print("\nAlternatively, use the .txt file directly for testing")

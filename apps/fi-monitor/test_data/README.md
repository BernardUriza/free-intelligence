# Test Data Directory

Sample files for RAG Testing Tool.

---

## Files

### sample_medical_note.txt
Spanish medical consultation note with standard SOAP structure:
- Patient demographics
- Chief complaint (motivo de consulta)
- History (historia)
- Physical exam (exploración física)
- Diagnosis (diagnóstico)
- Treatment plan (tratamiento)
- Prognosis (pronóstico)

**Use case:** Test semantic search with medical terminology in Spanish.

---

## Converting to PDF

**Option 1: Using convert_to_pdf.py**

```bash
# Install reportlab
pip install reportlab

# Convert
python convert_to_pdf.py
# Output: sample_medical_note.pdf
```

**Option 2: Manual conversion (macOS)**

```bash
# Use built-in textutil
textutil -convert pdf sample_medical_note.txt -output sample_medical_note.pdf
```

**Option 3: Online converter**
- Copy text from `sample_medical_note.txt`
- Visit https://www.ilovepdf.com/txt_to_pdf
- Paste and download

---

## Using Your Own PDFs

Replace with real medical notes (anonymized):

```bash
# Add your PDFs here
cp ~/Documents/patient_notes/*.pdf test_data/

# Test with RAG UI
python ../test_rag_ui.py
```

**Privacy Note:** Ensure PHI is removed before testing.

---

## Sample Test Questions

After uploading `sample_medical_note.pdf`, test these queries:

| Spanish Query | English Query | Expected Result |
|---------------|---------------|-----------------|
| ¿Cuál es el diagnóstico? | What is the diagnosis? | Migraña sin aura |
| ¿Qué tratamiento se prescribió? | What treatment was prescribed? | Ibuprofeno 400mg |
| ¿Cuáles eran los signos vitales? | What were the vital signs? | TA: 130/85, FC: 78 |
| ¿Quién es el médico? | Who is the doctor? | Dr. María González Rodríguez |
| ¿Cuál es el pronóstico? | What is the prognosis? | Favorable |

---

**Created:** 2026-01-28

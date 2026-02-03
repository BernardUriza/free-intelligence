"""Prescriptions Domain - Medication catalog, interactions, and allergies.

Endpoints:
- GET  /catalog/search - Search medication catalog
- GET  /catalog/autocomplete - Autocomplete medication names
- GET  /catalog/{id} - Get medication details
- POST /interactions/check - Check drug interactions
- POST /allergies/check - Check allergy interactions
- GET  /templates - List prescription templates
- POST / - Create prescription
- GET  /{id}/export - Export prescription

Migrated from: backend/api/routers/prescription/public/prescriptions.py
"""

from __future__ import annotations

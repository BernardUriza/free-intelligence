#!/usr/bin/env python3
"""
Example Evidence Pack Creation Script
FI-DATA-RES-021

Creates an example evidence pack from simulated clinical documents
(representing 5 PDFs worth of clinical data).
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.fi_common.infrastructure.evidence_pack import (
    ClinicalSource,
    EvidencePackBuilder,
)


def create_example_clinical_sources():
    """
    Create 5 example clinical sources simulating data from PDFs.
    These would normally be extracted from actual PDF files.
    """
    sources = []

    # Document 1: Lab Results (simulating lab_results_2025_11_15.pdf)
    sources.append(
        ClinicalSource(
            source_id="lab_20251115_001",
            tipo_doc="lab_result",
            fecha="2025-11-15",
            paciente_id="PAT2025FI001_HASH",
            hallazgo="Glucosa en ayunas: 145 mg/dL (elevada); HbA1c: 7.8% (elevada)",
            severidad="moderado",
            raw_text="""
        LABORATORIO CLÍNICO CENTRAL
        Fecha: 2025-11-15
        Paciente ID: PAT2025FI001

        PANEL METABÓLICO COMPLETO:
        - Glucosa en ayunas: 145 mg/dL (Ref: 70-100) **ELEVADO**
        - Hemoglobina A1c: 7.8% (Ref: <5.7%) **ELEVADO**
        - Creatinina: 0.9 mg/dL (Ref: 0.7-1.3) NORMAL
        - BUN: 18 mg/dL (Ref: 7-20) NORMAL
        - Colesterol total: 235 mg/dL (Ref: <200) **ELEVADO**
        - HDL: 42 mg/dL (Ref: >40) NORMAL
        - LDL: 158 mg/dL (Ref: <100) **ELEVADO**
        - Triglicéridos: 175 mg/dL (Ref: <150) **ELEVADO**

        Interpretación: Valores consistentes con diabetes mellitus tipo 2
        y dislipidemia. Se recomienda control médico.
        """,
        )
    )

    # Document 2: Clinical Note (simulating clinical_note_2025_11_16.pdf)
    sources.append(
        ClinicalSource(
            source_id="clinic_20251116_002",
            tipo_doc="clinical_note",
            fecha="2025-11-16",
            paciente_id="PAT2025FI001_HASH",
            hallazgo="Presión arterial: 148/92 mmHg; IMC: 31.2 kg/m2 (obesidad grado I)",
            severidad="moderado",
            raw_text="""
        NOTA DE EVOLUCIÓN CLÍNICA
        Fecha: 2025-11-16
        Servicio: Medicina Interna

        SIGNOS VITALES:
        - PA: 148/92 mmHg (elevada)
        - FC: 82 lpm
        - FR: 18 rpm
        - Temp: 36.8°C
        - Peso: 92 kg
        - Talla: 1.72 m
        - IMC: 31.2 kg/m2 (obesidad grado I)

        SUBJETIVO:
        Paciente refiere poliuria y polidipsia de 3 meses de evolución.
        Fatiga frecuente. Visión borrosa ocasional. Niega dolor torácico.

        OBJETIVO:
        Paciente consciente, orientado. Mucosas semihidratadas.
        Cardiopulmonar sin alteraciones agudas. Abdomen globoso.
        Acantosis nigricans en cuello.

        EVALUACIÓN:
        1. Diabetes mellitus tipo 2 descontrolada
        2. Hipertensión arterial estadio 2
        3. Obesidad grado I
        4. Dislipidemia mixta
        """,
        )
    )

    # Document 3: Previous Lab Results (simulating lab_results_2025_10_15.pdf)
    sources.append(
        ClinicalSource(
            source_id="lab_20251015_003",
            tipo_doc="lab_result",
            fecha="2025-10-15",
            paciente_id="PAT2025FI001_HASH",
            hallazgo="Glucosa en ayunas: 132 mg/dL (elevada); HbA1c: 7.2% (elevada)",
            severidad="moderado",
            raw_text="""
        LABORATORIO CLÍNICO CENTRAL
        Fecha: 2025-10-15

        RESULTADOS PREVIOS (hace 1 mes):
        - Glucosa en ayunas: 132 mg/dL **ELEVADO**
        - Hemoglobina A1c: 7.2% **ELEVADO**
        - Creatinina: 0.8 mg/dL NORMAL
        - Microalbuminuria: 28 mg/g (Ref: <30) NORMAL-ALTO

        Nota: Valores muestran progresión en comparación con
        estudios de hace 3 meses. Requiere ajuste terapéutico.
        """,
        )
    )

    # Document 4: Prescription (simulating prescription_2025_11_16.pdf)
    sources.append(
        ClinicalSource(
            source_id="rx_20251116_004",
            tipo_doc="prescription",
            fecha="2025-11-16",
            paciente_id="PAT2025FI001_HASH",
            hallazgo="Metformina 850mg c/12h; Lisinopril 10mg c/24h; Atorvastatina 20mg c/24h",
            raw_text="""
        RECETA MÉDICA
        Fecha: 2025-11-16

        PRESCRIPCIÓN:
        1. Metformina 850 mg
           Tomar 1 tableta cada 12 horas con alimentos
           Cantidad: 60 tabletas (30 días)

        2. Lisinopril 10 mg
           Tomar 1 tableta cada 24 horas por la mañana
           Cantidad: 30 tabletas (30 días)

        3. Atorvastatina 20 mg
           Tomar 1 tableta cada 24 horas por la noche
           Cantidad: 30 tabletas (30 días)

        INDICACIONES:
        - Dieta baja en carbohidratos simples
        - Ejercicio aeróbico 30 min/día, 5 días/semana
        - Monitoreo de glucosa capilar 2 veces/semana
        - Control en 1 mes con nuevos laboratorios
        """,
        )
    )

    # Document 5: Imaging Report (simulating chest_xray_2025_11_14.pdf)
    sources.append(
        ClinicalSource(
            source_id="img_20251114_005",
            tipo_doc="imaging",
            fecha="2025-11-14",
            paciente_id="PAT2025FI001_HASH",
            hallazgo="Radiografía de tórax: Cardiomegalia leve; sin infiltrados pulmonares",
            severidad="leve",
            raw_text="""
        INFORME RADIOLÓGICO
        Fecha: 2025-11-14
        Estudio: Radiografía de Tórax PA y Lateral

        TÉCNICA:
        Proyecciones posteroanterior y lateral de tórax.

        HALLAZGOS:
        - Índice cardiotorácico: 0.54 (cardiomegalia leve)
        - Campos pulmonares: Sin infiltrados ni consolidaciones
        - Senos costofrénicos: Libres
        - Mediastino: Centrado, sin ensanchamiento
        - Estructuras óseas: Sin alteraciones

        IMPRESIÓN:
        1. Cardiomegalia leve, probablemente relacionada con
           hipertensión arterial sistémica
        2. No evidencia de proceso agudo pulmonar
        3. No derrame pleural

        Correlacionar con clínica y ecocardiograma si está indicado.
        """,
        )
    )

    return sources


def main():
    """Create and export an example evidence pack."""
    print("Creating example evidence pack from 5 simulated clinical documents...\n")

    # Create builder
    builder = EvidencePackBuilder()

    # Set clinical question
    consulta = (
        "¿Cuál es el estado metabólico actual del paciente y qué tratamiento está recibiendo?"
    )
    builder.set_consulta(consulta)
    print(f"Consulta: {consulta}\n")

    # Add clinical sources
    sources = create_example_clinical_sources()
    print(f"Processing {len(sources)} clinical documents:")

    for i, source in enumerate(sources, 1):
        print(f"  {i}. {source.tipo_doc}: {source.fecha} - {source.source_id[:12]}...")
        builder.add_source(source)

    # Build evidence pack
    print("\nBuilding evidence pack...")
    pack = builder.build(session_id="session_example_20251117", policy_version="v1.0_2025")

    print(f"✓ Pack created: {pack.pack_id}")
    print(f"✓ Total sources: {len(pack.sources)}")
    print(f"✓ Total citations: {len(pack.citations) if pack.citations else 0}")
    print(f"✓ Extraction confidence: {pack.metadata.get('extraction_confidence', 0):.0%}")

    # Export to file
    export_dir = Path("export/evidence")
    export_dir.mkdir(parents=True, exist_ok=True)

    file_path = builder.export_to_file(pack, str(export_dir))
    print(f"\n✓ Evidence pack exported to: {file_path}")

    # Display Q&A response
    print("\n" + "=" * 60)
    print("GENERATED RESPONSE (with citations only, no diagnosis):")
    print("=" * 60)
    print(pack.response)

    # Display summary
    print("\n" + "=" * 60)
    print("EVIDENCE PACK SUMMARY:")
    print("=" * 60)

    pack_dict = builder.to_dict(pack)
    summary = {
        "pack_id": pack_dict["pack_id"],
        "consulta": pack_dict.get("consulta", ""),
        "source_count": pack_dict["metadata"]["source_count"],
        "document_types": pack_dict["metadata"]["document_types"],
        "total_citations": pack_dict["metadata"].get("total_citations", 0),
        "confidence": f"{pack_dict['metadata'].get('extraction_confidence', 0):.0%}",
        "source_hashes": [h[:12] + "..." for h in pack_dict["source_hashes"][:3]] + ["..."],
        "export_file": str(file_path),
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\n✅ Example evidence pack created successfully!")
    print(f"   View at: /evidence/{pack.pack_id}")

    return pack


if __name__ == "__main__":
    pack = main()

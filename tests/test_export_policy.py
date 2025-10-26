"""
Tests para Export Policy

Cobertura:
- Creación de ExportManifest
- Validación de schema
- Validación de data hash
- Load/save de manifests
- CLI operations

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Task: FI-SEC-FEAT-004
"""

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

from backend.export_policy import (
    ExportManifest,
    validate_manifest_schema,
    compute_file_hash,
    validate_export,
    create_export_manifest,
    load_manifest,
    InvalidManifest,
    ExportPolicyViolation
)


class TestExportManifest(unittest.TestCase):
    """Tests para dataclass ExportManifest."""

    def test_create_manifest(self):
        """Debe crear manifest con campos requeridos."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,  # SHA256 mock
            format="markdown",
            purpose="personal_review"
        )

        self.assertIsNotNone(manifest.export_id)
        self.assertEqual(manifest.format, "markdown")
        self.assertEqual(manifest.purpose, "personal_review")

    def test_to_dict(self):
        """Debe convertir a dict correctamente."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="json",
            purpose="backup"
        )

        data = manifest.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['format'], 'json')
        self.assertEqual(data['purpose'], 'backup')

    def test_to_json(self):
        """Debe serializar a JSON string."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="personal_review"
        )

        json_str = manifest.to_json()
        self.assertIsInstance(json_str, str)

        # Debe ser JSON válido
        parsed = json.loads(json_str)
        self.assertEqual(parsed['format'], 'markdown')

    def test_save_manifest(self):
        """Debe guardar manifest a archivo."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="personal_review"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = Path(f.name)

        manifest.save(filepath)

        # Verificar que existe
        self.assertTrue(filepath.exists())

        # Verificar contenido
        saved_data = json.loads(filepath.read_text())
        self.assertEqual(saved_data['format'], 'markdown')

        filepath.unlink()


class TestValidateManifestSchema(unittest.TestCase):
    """Tests para validación de schema."""

    def test_validate_valid_manifest(self):
        """Debe pasar manifest válido."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="personal_review"
        )

        # No debe raise exception
        result = validate_manifest_schema(manifest)
        self.assertTrue(result)

    def test_invalid_export_id(self):
        """Debe fallar con export_id inválido."""
        manifest = ExportManifest(
            export_id="not-a-uuid",
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="personal_review"
        )

        with self.assertRaises(InvalidManifest) as cm:
            validate_manifest_schema(manifest)

        self.assertIn("UUID", str(cm.exception))

    def test_invalid_timestamp(self):
        """Debe fallar con timestamp inválido."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp="not-iso-8601",
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="personal_review"
        )

        with self.assertRaises(InvalidManifest) as cm:
            validate_manifest_schema(manifest)

        self.assertIn("ISO 8601", str(cm.exception))

    def test_invalid_format(self):
        """Debe fallar con format inválido."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="invalid_format",
            purpose="personal_review"
        )

        with self.assertRaises(InvalidManifest) as cm:
            validate_manifest_schema(manifest)

        self.assertIn("format must be one of", str(cm.exception))

    def test_invalid_purpose(self):
        """Debe fallar con purpose inválido."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="invalid_purpose"
        )

        with self.assertRaises(InvalidManifest) as cm:
            validate_manifest_schema(manifest)

        self.assertIn("purpose must be one of", str(cm.exception))

    def test_invalid_data_hash(self):
        """Debe fallar con data_hash inválido."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="short_hash",
            format="markdown",
            purpose="personal_review"
        )

        with self.assertRaises(InvalidManifest) as cm:
            validate_manifest_schema(manifest)

        self.assertIn("SHA256", str(cm.exception))


class TestComputeFileHash(unittest.TestCase):
    """Tests para cómputo de hash."""

    def test_compute_hash_of_file(self):
        """Debe computar SHA256 de archivo."""
        content = "test content"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        file_hash = compute_file_hash(filepath)

        # Debe ser SHA256 (64 hex chars)
        self.assertEqual(len(file_hash), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in file_hash))

        filepath.unlink()

    def test_same_content_same_hash(self):
        """Mismo contenido debe dar mismo hash."""
        content = "identical content"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write(content)
            f1.flush()
            filepath1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write(content)
            f2.flush()
            filepath2 = Path(f2.name)

        hash1 = compute_file_hash(filepath1)
        hash2 = compute_file_hash(filepath2)

        self.assertEqual(hash1, hash2)

        filepath1.unlink()
        filepath2.unlink()

    def test_different_content_different_hash(self):
        """Contenido diferente debe dar hash diferente."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write("content A")
            f1.flush()
            filepath1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write("content B")
            f2.flush()
            filepath2 = Path(f2.name)

        hash1 = compute_file_hash(filepath1)
        hash2 = compute_file_hash(filepath2)

        self.assertNotEqual(hash1, hash2)

        filepath1.unlink()
        filepath2.unlink()


class TestValidateExport(unittest.TestCase):
    """Tests para validación completa de export."""

    def test_validate_valid_export(self):
        """Debe pasar export válido."""
        content = "export data"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        # Compute hash real
        data_hash = compute_file_hash(filepath)

        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash=data_hash,
            format="markdown",
            purpose="personal_review"
        )

        # No debe raise exception
        result = validate_export(manifest, filepath)
        self.assertTrue(result)

        filepath.unlink()

    def test_validate_hash_mismatch(self):
        """Debe fallar con hash mismatch."""
        content = "export data"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        # Hash incorrecto (no match)
        wrong_hash = "a" * 64

        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash=wrong_hash,
            format="markdown",
            purpose="personal_review"
        )

        with self.assertRaises(ExportPolicyViolation) as cm:
            validate_export(manifest, filepath)

        self.assertIn("hash mismatch", str(cm.exception))

        filepath.unlink()

    def test_validate_file_not_exists(self):
        """Debe fallar si archivo no existe."""
        manifest = ExportManifest(
            export_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exported_by="user123",
            data_source="/interactions/",
            data_hash="a" * 64,
            format="markdown",
            purpose="personal_review"
        )

        non_existent = Path("/tmp/non_existent_file.txt")

        with self.assertRaises(ExportPolicyViolation) as cm:
            validate_export(manifest, non_existent)

        self.assertIn("does not exist", str(cm.exception))


class TestCreateExportManifest(unittest.TestCase):
    """Tests para creación de manifest."""

    def test_create_manifest_auto_fields(self):
        """Debe crear manifest con campos auto-generados."""
        content = "test data"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        manifest = create_export_manifest(
            exported_by="user123",
            data_source="/interactions/",
            export_filepath=filepath,
            format="markdown",
            purpose="personal_review"
        )

        # Verificar campos auto-generados
        self.assertIsNotNone(manifest.export_id)
        self.assertIsNotNone(manifest.timestamp)
        self.assertIsNotNone(manifest.data_hash)
        self.assertEqual(len(manifest.data_hash), 64)

        # Verificar campos pasados
        self.assertEqual(manifest.exported_by, "user123")
        self.assertEqual(manifest.format, "markdown")

        filepath.unlink()

    def test_create_manifest_with_optional_fields(self):
        """Debe crear manifest con campos opcionales."""
        content = "test data"

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        manifest = create_export_manifest(
            exported_by="user123",
            data_source="/interactions/",
            export_filepath=filepath,
            format="json",
            purpose="backup",
            retention_days=90,
            includes_pii=False,
            metadata={"notes": "test export"}
        )

        self.assertEqual(manifest.retention_days, 90)
        self.assertFalse(manifest.includes_pii)
        self.assertEqual(manifest.metadata['notes'], "test export")

        filepath.unlink()


class TestLoadManifest(unittest.TestCase):
    """Tests para carga de manifest."""

    def test_load_valid_manifest(self):
        """Debe cargar manifest válido."""
        manifest_data = {
            "export_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exported_by": "user123",
            "data_source": "/interactions/",
            "data_hash": "a" * 64,
            "format": "markdown",
            "purpose": "personal_review"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f)
            f.flush()
            filepath = Path(f.name)

        manifest = load_manifest(filepath)

        self.assertEqual(manifest.format, "markdown")
        self.assertEqual(manifest.purpose, "personal_review")

        filepath.unlink()

    def test_load_manifest_file_not_found(self):
        """Debe fallar si archivo no existe."""
        non_existent = Path("/tmp/non_existent_manifest.json")

        with self.assertRaises(FileNotFoundError):
            load_manifest(non_existent)

    def test_load_invalid_manifest(self):
        """Debe fallar con manifest inválido."""
        manifest_data = {
            "export_id": "not-a-uuid",  # Invalid
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exported_by": "user123",
            "data_source": "/interactions/",
            "data_hash": "a" * 64,
            "format": "markdown",
            "purpose": "personal_review"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f)
            f.flush()
            filepath = Path(f.name)

        with self.assertRaises(InvalidManifest):
            load_manifest(filepath)

        filepath.unlink()


if __name__ == '__main__':
    unittest.main()

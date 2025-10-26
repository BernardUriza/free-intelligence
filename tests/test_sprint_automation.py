"""
Tests para Sprint Automation (sprint-close.sh)

Cobertura:
- Dry run execution (no side effects)
- Version increment logic
- Release notes generation
- Bundle creation
- SHA256 validation
- Retention policy

Autor: Bernard Uriza Orozco
Fecha: 2025-10-26
Task: FI-CICD-FEAT-002
"""

import unittest
import subprocess
import os
import re
from pathlib import Path


class TestSprintAutomation(unittest.TestCase):
    """Tests para validación de sprint-close.sh."""

    @classmethod
    def setUpClass(cls):
        """Setup común para todos los tests."""
        cls.repo_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            text=True
        ).strip()
        cls.script_path = os.path.join(cls.repo_root, 'scripts', 'sprint-close.sh')
        cls.backup_dir = os.path.join(cls.repo_root, 'backups')

    def test_script_exists(self):
        """Debe existir script sprint-close.sh."""
        self.assertTrue(
            os.path.exists(self.script_path),
            f"Script not found: {self.script_path}"
        )

    def test_script_is_executable(self):
        """Debe ser ejecutable."""
        self.assertTrue(
            os.access(self.script_path, os.X_OK),
            "Script is not executable"
        )

    def test_dry_run_no_side_effects(self):
        """Dry run no debe crear tags ni bundles."""
        # Get current tags
        before_tags = subprocess.check_output(
            ['git', 'tag', '-l'],
            text=True
        ).strip().split('\n')

        # Get current bundles
        before_bundles = list(Path(self.backup_dir).glob('*.bundle')) if os.path.exists(self.backup_dir) else []

        # Run dry run
        subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
            check=True
        )

        # Verify no new tags
        after_tags = subprocess.check_output(
            ['git', 'tag', '-l'],
            text=True
        ).strip().split('\n')

        self.assertEqual(
            set(before_tags),
            set(after_tags),
            "DRY_RUN should not create tags"
        )

        # Verify no new bundles
        after_bundles = list(Path(self.backup_dir).glob('*.bundle')) if os.path.exists(self.backup_dir) else []

        self.assertEqual(
            len(before_bundles),
            len(after_bundles),
            "DRY_RUN should not create bundles"
        )

    def test_dry_run_output_format(self):
        """Dry run debe producir output con formato esperado."""
        result = subprocess.run(
            [self.script_path, 'SPR-2025W44', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        output = result.stdout

        # Verificar secciones clave
        self.assertIn('🎯 Sprint Close', output)
        self.assertIn('Mode: DRY_RUN', output)
        self.assertIn('Step 1: Determinando versión', output)
        self.assertIn('Step 2: Generando notas de versión', output)
        self.assertIn('Step 3:', output)  # Tag step
        self.assertIn('Step 4: Generando bundle backup', output)
        self.assertIn('Step 5: Aplicando retención', output)
        self.assertIn('Step 6: Actualizando claude.md', output)
        self.assertIn('RESUMEN FINAL', output)

    def test_dry_run_warns_about_mode(self):
        """Dry run debe advertir que es simulación."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        self.assertIn('MODO DRY_RUN', result.stdout)
        self.assertIn('No se aplicaron cambios', result.stdout)
        self.assertIn('SIMULADO', result.stdout)

    def test_version_increment_detection(self):
        """Debe detectar último tag y calcular nueva versión."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        output = result.stdout

        # Debe mostrar último tag
        self.assertRegex(output, r'Último tag: v\d+\.\d+\.\d+')

        # Debe mostrar commits desde tag
        self.assertRegex(output, r'Commits desde tag: \d+')

        # Debe mostrar nueva versión
        self.assertRegex(output, r'Nueva versión: v\d+\.\d+\.\d+')

    def test_release_notes_generation(self):
        """Debe generar archivo de release notes."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        # Extraer path de release notes del output
        match = re.search(r'Notas guardadas en: (.+)', result.stdout)
        self.assertIsNotNone(match, "Release notes path not found in output")

        notes_path = match.group(1).strip()
        self.assertTrue(
            os.path.exists(notes_path),
            f"Release notes file should exist: {notes_path}"
        )

        # Verificar contenido
        with open(notes_path, 'r') as f:
            content = f.read()

        self.assertIn('# Release Notes', content)
        self.assertIn('Sprint', content)
        self.assertIn('Fecha', content)
        self.assertIn('Commits', content)

    def test_sprint_label_validation(self):
        """Debe aceptar diferentes formatos de sprint label."""
        valid_labels = [
            'SPR-2025W44',
            'SPR-TEST',
            'SPR-2025W01',
        ]

        for label in valid_labels:
            result = subprocess.run(
                [self.script_path, label, 'DRY_RUN'],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )

            self.assertEqual(
                result.returncode,
                0,
                f"Should accept sprint label: {label}"
            )
            self.assertIn(label, result.stdout)

    def test_backup_directory_path(self):
        """Debe usar directorio backups/ correcto."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        # Verificar que menciona backups/
        self.assertIn('backups/', result.stdout)

        # Verificar path absoluto correcto
        self.assertIn(self.backup_dir, result.stdout)

    def test_bundle_naming_convention(self):
        """Debe usar convención de nombres para bundles."""
        result = subprocess.run(
            [self.script_path, 'SPR-2025W44', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        # Formato: fi-{SPRINT}-{TAG}-{DATE}.bundle
        self.assertRegex(
            result.stdout,
            r'fi-SPR-2025W44-v\d+\.\d+\.\d+-\d{4}-\d{2}-\d{2}\.bundle'
        )

    def test_sha256_path_convention(self):
        """Debe crear archivo SHA256 con convención correcta."""
        result = subprocess.run(
            [self.script_path, 'SPR-2025W44', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        # En DRY_RUN el script menciona SHA256 pero no crea el archivo
        # Verificar que menciona SHA256 en output
        self.assertIn('SHA256', result.stdout)

    def test_retention_policy_mention(self):
        """Debe mencionar política de retención."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        self.assertIn('últimos 12 bundles', result.stdout)
        self.assertIn('Bundles actuales:', result.stdout)

    def test_timezone_america_mexico_city(self):
        """Debe usar timezone America/Mexico_City."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        self.assertIn('America/Mexico_City', result.stdout)

    def test_exit_code_success(self):
        """Debe retornar exit code 0 en éxito."""
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            cwd=self.repo_root
        )

        self.assertEqual(
            result.returncode,
            0,
            "Script should exit with code 0 on success"
        )

    def test_no_commits_scenario(self):
        """Debe manejar caso de no commits desde último tag."""
        # Este test es conceptual porque depende del estado real del repo
        # Solo verificamos que el script puede ejecutarse
        result = subprocess.run(
            [self.script_path, 'SPR-TEST', 'DRY_RUN'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

        # Si hay commits, debe mostrar count
        # Si no hay commits, debe mostrar "Sin cambios"
        self.assertTrue(
            'Commits desde tag:' in result.stdout or
            'Sin cambios' in result.stdout
        )


class TestSprintWorkflow(unittest.TestCase):
    """Tests para workflow completo de sprint."""

    @classmethod
    def setUpClass(cls):
        """Setup común."""
        cls.repo_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            text=True
        ).strip()

    def test_documentation_exists(self):
        """Debe existir documentación de cadencia."""
        docs = [
            'docs/sprint-cadence.md',
            'docs/cicd-pipeline.md',
        ]

        for doc in docs:
            path = os.path.join(self.repo_root, doc)
            self.assertTrue(
                os.path.exists(path),
                f"Documentation should exist: {doc}"
            )

    def test_sprint_plan_template_concepts(self):
        """Debe tener ejemplos de sprint plans."""
        # Verificar que existen sprints documentados (moved to docs/sprints/)
        sprint_files = [
            'docs/sprints/SPRINT_2_PLAN.md',
            'docs/sprints/SPRINT_2_TRACKER.md',
            'docs/sprints/SPRINT_ANALYSIS.md',
        ]

        found_any = False
        for file in sprint_files:
            path = os.path.join(self.repo_root, file)
            if os.path.exists(path):
                found_any = True
                break

        self.assertTrue(
            found_any,
            "Should have at least one sprint plan example in docs/sprints/"
        )

    def test_backups_directory_gitignored(self):
        """Backups directory debe estar en .gitignore."""
        gitignore_path = os.path.join(self.repo_root, '.gitignore')

        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                gitignore = f.read()

            self.assertIn(
                'backups/',
                gitignore,
                "backups/ should be gitignored"
            )


if __name__ == '__main__':
    unittest.main()

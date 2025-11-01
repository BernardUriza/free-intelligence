"""
Tests para Boot Map - Sistema de Seguimiento de Arranque

FI-DATA-FEAT-003: Mapa de boot cognitivo
"""

import unittest
from pathlib import Path

import h5py

from backend.boot_map import (
    append_boot_event,
    append_health_check,
    get_boot_map_stats,
    get_boot_sequence,
    get_core_functions,
    get_health_status,
    init_boot_map_group,
    register_core_function,
)


class TestBootMapInitialization(unittest.TestCase):
    """Tests para inicialización del boot map"""

    def setUp(self) -> None:
        """Crear archivo temporal para tests"""
        self.test_file = Path("storage/test_boot_map_init.h5")
        self.test_file.parent.mkdir(exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

    def tearDown(self) -> None:
        """Limpiar archivo temporal"""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_init_boot_map_group_creates_structure(self) -> None:
        """Test que init_boot_map_group crea la estructura correcta"""
        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)

            # Verificar grupo creado
            self.assertIn("/system/boot_map", h5f)

            # Verificar datasets
            boot_group = h5f["/system/boot_map"]
            self.assertIn("boot_sequence", boot_group)
            self.assertIn("core_functions", boot_group)
            self.assertIn("health_checks", boot_group)

            # Verificar metadata
            self.assertIn("created_at", boot_group.attrs)
            self.assertIn("schema_version", boot_group.attrs)
            self.assertIn("boot_map_version", boot_group.attrs)
            self.assertEqual(boot_group.attrs["schema_version"], "1.0")

    def test_init_boot_map_group_raises_if_exists(self) -> None:
        """Test que init_boot_map_group lanza error si ya existe"""
        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)

            # Intentar crear de nuevo
            with self.assertRaises(ValueError):
                init_boot_map_group(h5f)

    def test_boot_sequence_dataset_is_resizable(self) -> None:
        """Test que boot_sequence es redimensionable"""
        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)
            dataset = h5f["/system/boot_map/boot_sequence"]

            # Verificar shape inicial
            self.assertEqual(dataset.shape[0], 0)
            self.assertIsNone(dataset.maxshape[0])  # Unlimited

    def test_core_functions_dataset_has_correct_dtype(self) -> None:
        """Test que core_functions tiene dtype correcto"""
        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)
            dataset = h5f["/system/boot_map/core_functions"]

            # Verificar campos
            self.assertIn("function_name", dataset.dtype.names)
            self.assertIn("module_path", dataset.dtype.names)
            self.assertIn("category", dataset.dtype.names)
            self.assertIn("priority", dataset.dtype.names)
            self.assertIn("registered_at", dataset.dtype.names)
            self.assertIn("status", dataset.dtype.names)

    def test_health_checks_dataset_has_correct_dtype(self) -> None:
        """Test que health_checks tiene dtype correcto"""
        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)
            dataset = h5f["/system/boot_map/health_checks"]

            # Verificar campos
            self.assertIn("component", dataset.dtype.names)
            self.assertIn("status", dataset.dtype.names)
            self.assertIn("message", dataset.dtype.names)
            self.assertIn("checked_at", dataset.dtype.names)
            self.assertIn("duration_ms", dataset.dtype.names)


class TestBootEvents(unittest.TestCase):
    """Tests para eventos de arranque"""

    def setUp(self) -> None:
        """Crear archivo temporal con boot map"""
        self.test_file = Path("storage/test_boot_events.h5")
        self.test_file.parent.mkdir(exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)

    def tearDown(self) -> None:
        """Limpiar archivo temporal"""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_append_boot_event_adds_entry(self) -> None:
        """Test que append_boot_event agrega evento correctamente"""
        with h5py.File(self.test_file, "a") as h5f:
            append_boot_event(h5f, "SYSTEM_START")

            dataset = h5f["/system/boot_map/boot_sequence"]
            self.assertEqual(dataset.shape[0], 1)

            # Verificar formato: timestamp|event
            entry = dataset[0].decode("utf-8")
            self.assertIn("|SYSTEM_START", entry)

    def test_append_boot_event_raises_without_init(self) -> None:
        """Test que append_boot_event lanza error sin init"""
        empty_file = Path("storage/test_boot_no_init.h5")
        if empty_file.exists():
            empty_file.unlink()

        try:
            with h5py.File(empty_file, "w") as h5f:
                with self.assertRaises(KeyError):
                    append_boot_event(h5f, "TEST_EVENT")
        finally:
            if empty_file.exists():
                empty_file.unlink()

    def test_multiple_boot_events_sequential(self) -> None:
        """Test que múltiples eventos se agregan secuencialmente"""
        events = ["SYSTEM_START", "CONFIG_LOADED", "LOGGER_INIT", "CORPUS_OPEN"]

        with h5py.File(self.test_file, "a") as h5f:
            for event in events:
                append_boot_event(h5f, event)

            dataset = h5f["/system/boot_map/boot_sequence"]
            self.assertEqual(dataset.shape[0], len(events))

            # Verificar todos los eventos
            for i, expected_event in enumerate(events):
                entry = dataset[i].decode("utf-8")
                self.assertIn(f"|{expected_event}", entry)


class TestCoreFunctions(unittest.TestCase):
    """Tests para registro de funciones core"""

    def setUp(self) -> None:
        """Crear archivo temporal con boot map"""
        self.test_file = Path("storage/test_core_functions.h5")
        self.test_file.parent.mkdir(exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)

    def tearDown(self) -> None:
        """Limpiar archivo temporal"""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_register_core_function_adds_entry(self) -> None:
        """Test que register_core_function agrega función correctamente"""
        with h5py.File(self.test_file, "a") as h5f:
            register_core_function(
                h5f, "init_corpus", "backend.corpus_schema", "DATA", 10, "REGISTERED"
            )

            dataset = h5f["/system/boot_map/core_functions"]
            self.assertEqual(dataset.shape[0], 1)

            entry = dataset[0]
            self.assertEqual(entry["function_name"].decode("utf-8"), "init_corpus")
            self.assertEqual(entry["module_path"].decode("utf-8"), "backend.corpus_schema")
            self.assertEqual(entry["category"].decode("utf-8"), "DATA")
            self.assertEqual(entry["priority"], 10)
            self.assertEqual(entry["status"].decode("utf-8"), "REGISTERED")

    def test_register_core_function_default_values(self) -> None:
        """Test que register_core_function usa defaults correctos"""
        with h5py.File(self.test_file, "a") as h5f:
            register_core_function(h5f, "test_func", "test.module", "CORE")

            dataset = h5f["/system/boot_map/core_functions"]
            entry = dataset[0]

            # Defaults
            self.assertEqual(entry["priority"], 100)
            self.assertEqual(entry["status"].decode("utf-8"), "REGISTERED")

    def test_multiple_core_functions_different_categories(self) -> None:
        """Test que se pueden registrar funciones de diferentes categorías"""
        functions = [
            ("init_corpus", "backend.corpus_schema", "DATA", 10),
            ("get_logger", "backend.logger", "CORE", 5),
            ("validate_corpus", "backend.corpus_ops", "DATA", 20),
            ("load_config", "backend.config_loader", "CORE", 1),
        ]

        with h5py.File(self.test_file, "a") as h5f:
            for name, module, category, priority in functions:
                register_core_function(h5f, name, module, category, priority)

            dataset = h5f["/system/boot_map/core_functions"]
            self.assertEqual(dataset.shape[0], len(functions))


class TestHealthChecks(unittest.TestCase):
    """Tests para health checks"""

    def setUp(self) -> None:
        """Crear archivo temporal con boot map"""
        self.test_file = Path("storage/test_health_checks.h5")
        self.test_file.parent.mkdir(exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)

    def tearDown(self) -> None:
        """Limpiar archivo temporal"""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_append_health_check_adds_entry(self) -> None:
        """Test que append_health_check agrega check correctamente"""
        with h5py.File(self.test_file, "a") as h5f:
            append_health_check(h5f, "CONFIG", "OK", "Configuration loaded successfully", 12.5)

            dataset = h5f["/system/boot_map/health_checks"]
            self.assertEqual(dataset.shape[0], 1)

            entry = dataset[0]
            self.assertEqual(entry["component"].decode("utf-8"), "CONFIG")
            self.assertEqual(entry["status"].decode("utf-8"), "OK")
            self.assertEqual(entry["message"].decode("utf-8"), "Configuration loaded successfully")
            self.assertAlmostEqual(entry["duration_ms"], 12.5, places=1)

    def test_append_health_check_default_duration(self) -> None:
        """Test que append_health_check usa duration default"""
        with h5py.File(self.test_file, "a") as h5f:
            append_health_check(h5f, "TEST", "OK", "Test message")

            dataset = h5f["/system/boot_map/health_checks"]
            entry = dataset[0]

            self.assertAlmostEqual(entry["duration_ms"], 0.0, places=1)

    def test_multiple_health_checks_different_statuses(self) -> None:
        """Test que se pueden registrar checks con diferentes estados"""
        checks = [
            ("CONFIG", "OK", "Configuration OK"),
            ("CORPUS", "OK", "Corpus accessible"),
            ("NETWORK", "WARNING", "Slow response"),
            ("DISK", "ERROR", "Low space"),
        ]

        with h5py.File(self.test_file, "a") as h5f:
            for component, status, message in checks:
                append_health_check(h5f, component, status, message, 10.0)

            dataset = h5f["/system/boot_map/health_checks"]
            self.assertEqual(dataset.shape[0], len(checks))


class TestBootMapQueries(unittest.TestCase):
    """Tests para queries del boot map"""

    def setUp(self) -> None:
        """Crear archivo temporal con datos de ejemplo"""
        self.test_file = Path("storage/test_boot_queries.h5")
        self.test_file.parent.mkdir(exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

        with h5py.File(self.test_file, "w") as h5f:
            init_boot_map_group(h5f)

            # Agregar datos de ejemplo
            append_boot_event(h5f, "SYSTEM_START")
            append_boot_event(h5f, "CONFIG_LOADED")

            register_core_function(h5f, "init_corpus", "backend.corpus_schema", "DATA", 10)
            register_core_function(h5f, "get_logger", "backend.logger", "CORE", 5)

            append_health_check(h5f, "CONFIG", "OK", "Config OK", 12.5)
            append_health_check(h5f, "CORPUS", "WARNING", "Slow access", 250.0)

    def tearDown(self) -> None:
        """Limpiar archivo temporal"""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_get_boot_sequence_returns_all_events(self) -> None:
        """Test que get_boot_sequence retorna todos los eventos"""
        with h5py.File(self.test_file, "r") as h5f:
            sequence = get_boot_sequence(h5f)

            self.assertEqual(len(sequence), 2)
            self.assertEqual(sequence[0][1], "SYSTEM_START")
            self.assertEqual(sequence[1][1], "CONFIG_LOADED")

    def test_get_core_functions_returns_all_functions(self) -> None:
        """Test que get_core_functions retorna todas las funciones"""
        with h5py.File(self.test_file, "r") as h5f:
            functions = get_core_functions(h5f)

            self.assertEqual(len(functions), 2)
            self.assertEqual(functions[0]["function_name"], "init_corpus")
            self.assertEqual(functions[1]["function_name"], "get_logger")

    def test_get_core_functions_filter_by_category(self) -> None:
        """Test que get_core_functions filtra por categoría"""
        with h5py.File(self.test_file, "r") as h5f:
            data_functions = get_core_functions(h5f, category="DATA")
            core_functions = get_core_functions(h5f, category="CORE")

            self.assertEqual(len(data_functions), 1)
            self.assertEqual(data_functions[0]["function_name"], "init_corpus")

            self.assertEqual(len(core_functions), 1)
            self.assertEqual(core_functions[0]["function_name"], "get_logger")

    def test_get_health_status_groups_by_status(self) -> None:
        """Test que get_health_status agrupa por estado"""
        with h5py.File(self.test_file, "r") as h5f:
            health = get_health_status(h5f)

            self.assertIn("OK", health)
            self.assertIn("WARNING", health)
            self.assertIn("ERROR", health)
            self.assertIn("CRITICAL", health)

            self.assertEqual(len(health["OK"]), 1)
            self.assertEqual(len(health["WARNING"]), 1)
            self.assertEqual(len(health["ERROR"]), 0)
            self.assertEqual(len(health["CRITICAL"]), 0)

    def test_get_boot_map_stats_returns_correct_counts(self) -> None:
        """Test que get_boot_map_stats retorna stats correctos"""
        with h5py.File(self.test_file, "r") as h5f:
            stats = get_boot_map_stats(h5f)

            self.assertEqual(stats["total_boot_events"], 2)
            self.assertEqual(stats["total_core_functions"], 2)
            self.assertEqual(stats["total_health_checks"], 2)
            self.assertEqual(stats["schema_version"], "1.0")
            self.assertIn("created_at", stats)


class TestBootMapErrors(unittest.TestCase):
    """Tests para manejo de errores"""

    def setUp(self) -> None:
        """Crear archivo sin boot map"""
        self.test_file = Path("storage/test_boot_errors.h5")
        self.test_file.parent.mkdir(exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

        # Archivo vacío, sin boot map
        with h5py.File(self.test_file, "w") as h5f:
            pass

    def tearDown(self) -> None:
        """Limpiar archivo temporal"""
        if self.test_file.exists():
            self.test_file.unlink()

    def test_operations_raise_without_init(self) -> None:
        """Test que operaciones lanzan error sin init"""
        with h5py.File(self.test_file, "a") as h5f:
            # Todas estas deben lanzar KeyError
            with self.assertRaises(KeyError):
                append_boot_event(h5f, "TEST")

            with self.assertRaises(KeyError):
                register_core_function(h5f, "test", "test", "TEST")

            with self.assertRaises(KeyError):
                append_health_check(h5f, "TEST", "OK", "Test")

            with self.assertRaises(KeyError):
                get_boot_sequence(h5f)

            with self.assertRaises(KeyError):
                get_core_functions(h5f)

            with self.assertRaises(KeyError):
                get_health_status(h5f)

            with self.assertRaises(KeyError):
                get_boot_map_stats(h5f)


if __name__ == "__main__":
    unittest.main()

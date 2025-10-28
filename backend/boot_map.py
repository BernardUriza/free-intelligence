"""
Boot Map - Sistema de Seguimiento de Arranque Cognitivo

Registra la secuencia de inicialización del sistema, funciones core,
y estado de salud inicial. Permite reconstrucción tras fallo o snapshot.

Parte de Free Intelligence v0.2.0 - Sprint 2 Tier 2
FI-DATA-FEAT-003: Mapa de boot cognitivo

Author: Bernard Uriza Orozco
License: MIT
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import h5py
import numpy as np

from backend.logger import get_logger
from backend.config_loader import load_config

logger = get_logger(__name__)


def init_boot_map_group(h5file: h5py.File) -> None:
    """
    Inicializa el grupo /system/boot_map/ en HDF5.

    Estructura:
    - boot_sequence: Secuencia de arranque del sistema
    - core_functions: Funciones críticas registradas
    - health_checks: Estado de salud inicial
    - metadata: Configuración de arranque

    Args:
        h5file: Handle abierto del archivo HDF5

    Raises:
        ValueError: Si el grupo ya existe
    """
    if "/system" in h5file:
        if "/system/boot_map" in h5file:
            logger.warning(
                "BOOT_MAP_GROUP_EXISTS",
                path="/system/boot_map"
            )
            raise ValueError("Boot map group already exists")
    else:
        h5file.create_group("/system")
        logger.info("SYSTEM_GROUP_CREATED", path="/system")

    boot_group = h5file.create_group("/system/boot_map")

    # Dataset: boot_sequence
    # Registra la secuencia temporal de inicialización
    boot_group.create_dataset(
        "boot_sequence",
        shape=(0,),
        maxshape=(None,),
        dtype=h5py.string_dtype(encoding='utf-8', length=200),
        chunks=True,
        compression="gzip",
        compression_opts=4
    )

    # Dataset: core_functions
    # Lista de funciones críticas del sistema
    dt_functions = np.dtype([
        ('function_name', h5py.string_dtype(encoding='utf-8', length=100)),
        ('module_path', h5py.string_dtype(encoding='utf-8', length=200)),
        ('category', h5py.string_dtype(encoding='utf-8', length=50)),
        ('priority', 'i4'),
        ('registered_at', h5py.string_dtype(encoding='utf-8', length=50)),
        ('status', h5py.string_dtype(encoding='utf-8', length=20))
    ])
    boot_group.create_dataset(
        "core_functions",
        shape=(0,),
        maxshape=(None,),
        dtype=dt_functions,
        chunks=True,
        compression="gzip",
        compression_opts=4
    )

    # Dataset: health_checks
    # Estado de salud de cada componente
    dt_health = np.dtype([
        ('component', h5py.string_dtype(encoding='utf-8', length=100)),
        ('status', h5py.string_dtype(encoding='utf-8', length=20)),
        ('message', h5py.string_dtype(encoding='utf-8', length=200)),
        ('checked_at', h5py.string_dtype(encoding='utf-8', length=50)),
        ('duration_ms', 'f4')
    ])
    boot_group.create_dataset(
        "health_checks",
        shape=(0,),
        maxshape=(None,),
        dtype=dt_health,
        chunks=True,
        compression="gzip",
        compression_opts=4
    )

    # Metadata del boot map
    boot_group.attrs['created_at'] = datetime.now(timezone.utc).isoformat()
    boot_group.attrs['schema_version'] = '1.0'
    boot_group.attrs['boot_map_version'] = '0.2.0'

    logger.info(
        "BOOT_MAP_GROUP_INITIALIZED",
        path="/system/boot_map",
        datasets=["boot_sequence", "core_functions", "health_checks"]
    )


def append_boot_event(
    h5file: h5py.File,
    event: str
) -> None:
    """
    Registra un evento en la secuencia de arranque.

    Args:
        h5file: Handle abierto del archivo HDF5
        event: Descripción del evento (ej: "CONFIG_LOADED", "LOGGER_INITIALIZED")

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    dataset = h5file["/system/boot_map/boot_sequence"]
    current_size = dataset.shape[0]
    dataset.resize((current_size + 1,))

    # Format: timestamp|event
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = f"{timestamp}|{event}"
    dataset[current_size] = entry

    logger.info(
        "BOOT_EVENT_APPENDED",
        boot_event=event,
        sequence_index=current_size
    )


def register_core_function(
    h5file: h5py.File,
    function_name: str,
    module_path: str,
    category: str,
    priority: int = 100,
    status: str = "REGISTERED"
) -> None:
    """
    Registra una función crítica del sistema.

    Args:
        h5file: Handle abierto del archivo HDF5
        function_name: Nombre de la función (ej: "init_corpus")
        module_path: Ruta del módulo (ej: "backend.corpus_schema")
        category: Categoría (DATA, CORE, SEC, API, UI, CLI)
        priority: Prioridad de carga (menor = más prioritario)
        status: Estado (REGISTERED, LOADED, FAILED)

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    dataset = h5file["/system/boot_map/core_functions"]
    current_size = dataset.shape[0]
    dataset.resize((current_size + 1,))

    timestamp = datetime.now(timezone.utc).isoformat()

    dataset[current_size] = (
        function_name,
        module_path,
        category,
        priority,
        timestamp,
        status
    )

    logger.info(
        "CORE_FUNCTION_REGISTERED",
        function=function_name,
        module=module_path,
        category=category,
        priority=priority
    )


def append_health_check(
    h5file: h5py.File,
    component: str,
    status: str,
    message: str,
    duration_ms: float = 0.0
) -> None:
    """
    Registra el resultado de un health check.

    Args:
        h5file: Handle abierto del archivo HDF5
        component: Nombre del componente (ej: "CONFIG", "CORPUS", "LOGGER")
        status: Estado (OK, WARNING, ERROR, CRITICAL)
        message: Mensaje descriptivo
        duration_ms: Duración del check en milisegundos

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    dataset = h5file["/system/boot_map/health_checks"]
    current_size = dataset.shape[0]
    dataset.resize((current_size + 1,))

    timestamp = datetime.now(timezone.utc).isoformat()

    dataset[current_size] = (
        component,
        status,
        message,
        timestamp,
        duration_ms
    )

    logger.info(
        "HEALTH_CHECK_RECORDED",
        component=component,
        status=status,
        duration_ms=duration_ms
    )


def get_boot_sequence(h5file: h5py.File) -> List[Tuple[str, str]]:
    """
    Recupera la secuencia de arranque completa.

    Returns:
        Lista de tuplas (timestamp, event)

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    dataset = h5file["/system/boot_map/boot_sequence"]
    sequence = []

    for entry in dataset:
        entry_str = entry.decode('utf-8') if isinstance(entry, bytes) else entry
        parts = entry_str.split('|', 1)
        if len(parts) == 2:
            sequence.append((parts[0], parts[1]))

    logger.info(
        "BOOT_SEQUENCE_READ",
        total_events=len(sequence)
    )

    return sequence


def get_core_functions(
    h5file: h5py.File,
    category: Optional[str] = None
) -> List[Dict]:
    """
    Recupera funciones core registradas.

    Args:
        h5file: Handle abierto del archivo HDF5
        category: Filtrar por categoría (opcional)

    Returns:
        Lista de diccionarios con función info

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    dataset = h5file["/system/boot_map/core_functions"]
    functions = []

    for entry in dataset:
        entry_category = entry['category'].decode('utf-8') if isinstance(entry['category'], bytes) else entry['category']

        func_dict = {
            'function_name': entry['function_name'].decode('utf-8') if isinstance(entry['function_name'], bytes) else entry['function_name'],
            'module_path': entry['module_path'].decode('utf-8') if isinstance(entry['module_path'], bytes) else entry['module_path'],
            'category': entry_category,
            'priority': int(entry['priority']),
            'registered_at': entry['registered_at'].decode('utf-8') if isinstance(entry['registered_at'], bytes) else entry['registered_at'],
            'status': entry['status'].decode('utf-8') if isinstance(entry['status'], bytes) else entry['status']
        }

        if category is None or entry_category == category:
            functions.append(func_dict)

    logger.info(
        "CORE_FUNCTIONS_READ",
        total_functions=len(functions),
        category=category or "all"
    )

    return functions


def get_health_status(h5file: h5py.File) -> Dict[str, List[Dict]]:
    """
    Recupera el estado de salud de todos los componentes.

    Returns:
        Diccionario agrupado por status (OK, WARNING, ERROR, CRITICAL)

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    dataset = h5file["/system/boot_map/health_checks"]
    health = {
        'OK': [],
        'WARNING': [],
        'ERROR': [],
        'CRITICAL': []
    }

    for entry in dataset:
        entry_status = entry['status'].decode('utf-8') if isinstance(entry['status'], bytes) else entry['status']

        check_dict = {
            'component': entry['component'].decode('utf-8') if isinstance(entry['component'], bytes) else entry['component'],
            'status': entry_status,
            'message': entry['message'].decode('utf-8') if isinstance(entry['message'], bytes) else entry['message'],
            'checked_at': entry['checked_at'].decode('utf-8') if isinstance(entry['checked_at'], bytes) else entry['checked_at'],
            'duration_ms': float(entry['duration_ms'])
        }

        if entry_status in health:
            health[entry_status].append(check_dict)

    logger.info(
        "HEALTH_STATUS_READ",
        ok=len(health['OK']),
        warning=len(health['WARNING']),
        error=len(health['ERROR']),
        critical=len(health['CRITICAL'])
    )

    return health


def get_boot_map_stats(h5file: h5py.File) -> Dict:
    """
    Obtiene estadísticas del boot map.

    Returns:
        Diccionario con stats generales

    Raises:
        KeyError: Si el grupo boot_map no existe
    """
    if "/system/boot_map" not in h5file:
        raise KeyError("Boot map group not initialized")

    boot_group = h5file["/system/boot_map"]

    stats = {
        'created_at': boot_group.attrs.get('created_at', 'unknown'),
        'schema_version': boot_group.attrs.get('schema_version', 'unknown'),
        'boot_map_version': boot_group.attrs.get('boot_map_version', 'unknown'),
        'total_boot_events': boot_group["boot_sequence"].shape[0],
        'total_core_functions': boot_group["core_functions"].shape[0],
        'total_health_checks': boot_group["health_checks"].shape[0]
    }

    logger.info("BOOT_MAP_STATS_RETRIEVED", **stats)

    return stats


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Demo
    print("🔧 Boot Map Demo\n")

    test_file = Path("storage/test_boot_map.h5")
    test_file.parent.mkdir(exist_ok=True)

    if test_file.exists():
        test_file.unlink()

    with h5py.File(test_file, "w") as h5f:
        print("Initializing boot map group...")
        init_boot_map_group(h5f)
        print("✅ Boot map initialized\n")

        print("Recording boot sequence...")
        append_boot_event(h5f, "SYSTEM_START")
        append_boot_event(h5f, "CONFIG_LOADED")
        append_boot_event(h5f, "LOGGER_INITIALIZED")
        append_boot_event(h5f, "CORPUS_OPENED")
        print("✅ Boot sequence recorded\n")

        print("Registering core functions...")
        register_core_function(h5f, "init_corpus", "backend.corpus_schema", "DATA", 10)
        register_core_function(h5f, "append_interaction", "backend.corpus_ops", "DATA", 20)
        register_core_function(h5f, "get_logger", "backend.logger", "CORE", 5)
        register_core_function(h5f, "load_config", "backend.config_loader", "CORE", 1)
        print("✅ Core functions registered\n")

        print("Running health checks...")
        append_health_check(h5f, "CONFIG", "OK", "Configuration loaded successfully", 12.5)
        append_health_check(h5f, "CORPUS", "OK", "Corpus file accessible", 8.3)
        append_health_check(h5f, "LOGGER", "OK", "Logging system operational", 3.1)
        print("✅ Health checks completed\n")

        print("📊 Boot Map Stats:")
        stats = get_boot_map_stats(h5f)
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\n📖 Boot Sequence:")
        sequence = get_boot_sequence(h5f)
        for i, (ts, event) in enumerate(sequence, 1):
            print(f"   [{i}] {ts[:19]} - {event}")

        print("\n🔧 Core Functions:")
        functions = get_core_functions(h5f)
        for func in functions:
            print(f"   • {func['function_name']} ({func['category']}, priority={func['priority']})")

        print("\n🏥 Health Status:")
        health = get_health_status(h5f)
        for status, checks in health.items():
            if checks:
                print(f"   {status}: {len(checks)} component(s)")
                for check in checks:
                    print(f"      - {check['component']}: {check['message']} ({check['duration_ms']}ms)")

    print(f"\n✅ Demo completed. Test file: {test_file}")

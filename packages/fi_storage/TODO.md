# fi_storage - Trabajo Pendiente

## Estado Actual
- ✅ Estructura de directorios creada
- ✅ Archivos copiados de backend/storage/
- ⚠️ Los archivos todavía importan de `backend.*`
- ❌ No es standalone aún

## Imports a Migrar

### Dependencias de logging (→ fi_observability)
```python
# ACTUAL
from backend.logger import get_logger
from backend.common.fi_common.logging.logger import get_logger

# OBJETIVO
from fi_observability import get_logger
```

### Dependencias de modelos (→ fi_common)
```python
# ACTUAL
from backend.models.task_type import TaskStatus, TaskType

# OBJETIVO
from fi_common.domain.entities import TaskStatus, TaskType
```

### Dependencias de policy (→ fi_common)
```python
# ACTUAL
from backend.append_only_policy import AppendOnlyPolicy

# OBJETIVO
from fi_common.policy import AppendOnlyPolicy
```

### Dependencias internas (→ fi_storage)
```python
# ACTUAL
from backend.storage.session_h5_manager import get_session_h5_path
from backend.storage.session_locks import locked_session_h5

# OBJETIVO
from fi_storage.infrastructure.hdf5.session_h5_manager import get_session_h5_path
from fi_storage.infrastructure.hdf5.session_locks import locked_session_h5
```

## Orden de Migración

1. **fi_observability** - Extraer logging primero (muy usado)
2. **fi_common/domain** - Mover TaskType, TaskStatus
3. **fi_common/policy** - Mover AppendOnlyPolicy
4. **fi_storage** - Actualizar imports internos
5. **backend/storage** - Convertir a compatibility layer

## Comandos para migrar imports

```bash
# En packages/fi_storage/
sed -i '' 's/from backend\.logger/from fi_observability/g' **/*.py
sed -i '' 's/from backend\.storage\./from fi_storage.infrastructure.hdf5./g' **/*.py
```

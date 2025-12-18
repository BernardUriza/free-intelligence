# fi_storage

Storage layer for Free Intelligence - HDF5 persistence, repositories, and session management.

## Installation

```bash
pip install -e packages/fi_storage
```

## Usage

```python
from fi_storage import TaskRepository, SessionH5Manager
from fi_storage.hdf5 import corpus_ops, sessions_store
```

## Structure

```
fi_storage/
├── domain/
│   ├── interfaces/     # Repository ABCs
│   └── entities/       # Session, Task entities
├── infrastructure/
│   └── hdf5/          # HDF5 implementations
├── adapters/          # FastAPI dependencies
└── tests/
```

## API

### Core Classes
- `TaskRepository` - Task persistence with HDF5
- `SessionH5Manager` - Session file management
- `SessionsStore` - Session CRUD operations

### HDF5 Operations
- `corpus_ops` - Append-only corpus operations
- `corpus_schema` - Schema definitions
- `search` - Semantic search utilities

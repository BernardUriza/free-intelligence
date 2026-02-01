# SQLite UUID Type Affinity Bug

**Date:** 2025-12-31
**Issue:** `/api/clinics` returning 500 Internal Server Error
**Root Cause:** SQLite stored UUID as float instead of string

## The Problem

SQLAlchemy threw:
```
AttributeError: 'float' object has no attribute 'replace'
```

When trying to parse a UUID from the database, Python's `uuid.py` called `.replace()` on what it expected to be a string, but received a float.

## Root Cause Analysis

1. **SQLite Type Affinity**: SQLite uses "type affinity" not strict types. A column declared as `UUID` still accepts ANY value type.

2. **Scientific Notation Parsing**: When a UUID like `11111111-1111-1111-1111-111111111111` was inserted, SQLite interpreted the leading digits as a number in scientific notation: `1.11111111111111e+31`

3. **Data Corruption**: The `clinic_id` was stored as `real` (float) type instead of `text`:
   ```sql
   SELECT clinic_id, typeof(clinic_id) FROM clinics;
   -- Result: 1.11111111111111e+31 | real
   ```

## The Fix

```sql
-- Backup first
cp aurity.db aurity.db.backup-before-uuid-fix

-- Fix corrupted UUIDs
UPDATE clinics
SET clinic_id = '11111111-1111-1111-1111-111111111111'
WHERE typeof(clinic_id) = 'real';

-- Verify
SELECT clinic_id, typeof(clinic_id) FROM clinics;
-- Result: 11111111-1111-1111-1111-111111111111 | text
```

## Prevention Strategies

### 1. Use Parameterized Queries (Best)
```python
# BAD - SQLite may interpret as number
cursor.execute(f"INSERT INTO clinics (clinic_id) VALUES ({uuid_value})")

# GOOD - Always parameterized
cursor.execute("INSERT INTO clinics (clinic_id) VALUES (?)", (str(uuid_value),))
```

### 2. Use SQLAlchemy String Type
```python
# Instead of:
clinic_id = Column(UUID)  # SQLite doesn't enforce this

# Use:
clinic_id = Column(String(36))  # Explicit string storage
```

### 3. Validate on Insert
```python
def validate_uuid(value):
    if not isinstance(value, str):
        raise ValueError(f"UUID must be string, got {type(value)}")
    uuid.UUID(value)  # Validates format
    return value
```

### 4. Use CHECK Constraint
```sql
CREATE TABLE clinics (
    clinic_id TEXT NOT NULL CHECK(typeof(clinic_id) = 'text'),
    ...
);
```

## Debugging Commands

```bash
# Check column types in SQLite
sqlite3 database.db "SELECT column_name, typeof(column_name) FROM table_name"

# Find all float UUIDs
sqlite3 database.db "SELECT * FROM clinics WHERE typeof(clinic_id) = 'real'"

# Check table schema
sqlite3 database.db ".schema clinics"
```

## Key Learnings

1. **SQLite is weakly typed** - Column types are suggestions, not enforcements
2. **UUIDs starting with digits are risky** - `11111111-...` looks like a number to SQLite
3. **Always use parameterized queries** - Prevents type inference issues
4. **typeof() is your friend** - Use it to debug type mismatches
5. **Backup before data fixes** - Always `cp database.db database.db.backup` first

## Related Files

- `backend/database.py:15` - DATABASE_URL configuration
- `backend/models/checkin_models.py:141-175` - Clinic SQLAlchemy model
- `backend/src/fi_clinic/api/public/clinics.py:223-241` - list_clinics endpoint

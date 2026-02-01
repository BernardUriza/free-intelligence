# Multi-Tenancy Phase 2: Repository Filtering (Pending)

**Created:** 2026-01-29
**Status:** Phase 1 Complete (Extraction), Phase 2 Pending (Filtering)
**Estimated Time:** 2-3 hours

---

## Phase 1 Complete ✅

**Commit:** 430052d9 (2026-01-29)

**Changes:**
1. Added `clinic_id: str | None` field to User entity
2. Extracted clinic_id from Auth0 `app_metadata.clinic_id` in Auth0Provider
3. Updated documents API to use `current_user.clinic_id`
4. Logged clinic_id in auth0_token_validated events

**Result:**
- Every authenticated request now has `current_user.clinic_id` available
- Backward compatible: Falls back to empty string if not set (single-tenant legacy)

---

## Phase 2 Scope: Repository Layer Filtering

**Goal:** Ensure data isolation - Doctor A cannot access Clinic B's data

**Files Requiring clinic_id Filtering:** 19 total

### Category 1: High Priority (Data Leakage Risk)

**backend/services/document/api/public/documents.py**
- Functions: `list_documents()`, `search_documents_by_embedding()`
- Current: No clinic_id filter → returns ALL documents
- Fix: Add `WHERE clinic_id = :clinic_id` to queries
- SUPERADMIN: Bypass filter (can see all clinics)

**backend/services/assistant/api/public/assistant/chat.py**
- Function: `_handle_receptionist_mode()`
- Current: clinic_id from receptionist_config (user-provided, NOT validated)
- Fix: Validate `request.receptionist_config["clinic_id"] == current_user.clinic_id`
- Security: Prevent impersonation (user claiming wrong clinic_id)

**backend/services/checkin/api/public/checkin.py**
- Functions: `list_appointments()`, `get_appointment_details()`
- Current: No clinic_id filter → patient can see other clinics' appointments
- Fix: Add clinic_id filter to CheckinRepository queries

**backend/api/routers/clinic/public/clinics.py**
- Functions: `get_clinics()`, `get_clinic_by_id()`
- Current: Returns all clinics (no isolation)
- Fix: Filter by current_user.clinic_id OR allow SUPERADMIN to see all

**backend/api/routers/user/public/user_clinic.py**
- Functions: User-clinic associations
- Current: No clinic_id validation
- Fix: Ensure users can only be assigned to their own clinic

### Category 2: Medium Priority (Audit/Reporting)

**backend/api/payment/api/public/payments.py**
- Functions: Payment processing
- Current: No clinic_id isolation → billing leakage
- Fix: Filter payments by clinic_id

**backend/api/license/api/public/renewal.py**
- Functions: License renewal
- Current: No clinic_id validation
- Fix: Validate license belongs to user's clinic

**backend/core/domain/clinic/services/doctor_limits.py**
- Functions: Doctor quota enforcement
- Current: No clinic_id isolation
- Fix: Enforce quotas per-clinic (not global)

**backend/utils/common/api/public/notifications.py**
- Functions: Notification delivery
- Current: No clinic_id filter
- Fix: Only send notifications within clinic

### Category 3: Low Priority (Seed Data/Scripts)

**backend/scripts/seed_data.py**
- One-time script, no runtime risk
- Document expected clinic_id values

**backend/scripts/init_checkin_db.py**
- One-time script, no runtime risk
- Document expected clinic_id values

**backend/alembic/versions/*.py**
- Database migrations
- No changes needed (schema already has clinic_id columns)

---

## Implementation Pattern

### Standard Repository Filter

**Before:**
```python
def list_documents(owner_user_id: str) -> list[Document]:
    # Query all documents for user (NO clinic isolation)
    return db.query(Document).filter(Document.owner_user_id == owner_user_id).all()
```

**After:**
```python
def list_documents(owner_user_id: str, clinic_id: str) -> list[Document]:
    # Query only documents within clinic (real isolation)
    query = db.query(Document).filter(
        Document.owner_user_id == owner_user_id,
        Document.clinic_id == clinic_id,  # ← NEW: Multi-tenancy filter
    )
    return query.all()
```

### SUPERADMIN Bypass Pattern

```python
def list_documents(owner_user_id: str, clinic_id: str | None, user_roles: list[UserRole]) -> list[Document]:
    query = db.query(Document).filter(Document.owner_user_id == owner_user_id)

    # SUPERADMIN can see all clinics
    if UserRole.SUPERADMIN not in user_roles:
        # Regular users: filter by clinic
        if not clinic_id:
            raise ValueError("clinic_id required for non-SUPERADMIN users")
        query = query.filter(Document.clinic_id == clinic_id)

    return query.all()
```

### Validation Pattern (User-Provided clinic_id)

**Before:**
```python
# SECURITY ISSUE: User-provided clinic_id NOT validated
clinic_id = request.receptionist_config.get("clinic_id")
appointment = fetch_appointment(clinic_id=clinic_id)  # ← Impersonation risk!
```

**After:**
```python
# Validate user-provided clinic_id matches Auth0 token
requested_clinic_id = request.receptionist_config.get("clinic_id")
if requested_clinic_id != current_user.clinic_id:
    raise HTTPException(
        status_code=403,
        detail="Cannot access appointments from other clinics"
    )

appointment = fetch_appointment(clinic_id=requested_clinic_id)  # ← Safe
```

---

## Testing Strategy

### Unit Tests

```python
def test_document_isolation():
    # User A (clinic-1) creates document
    user_a = User(id="user-a", clinic_id="clinic-1")
    doc = create_document(..., clinic_id=user_a.clinic_id)

    # User B (clinic-2) tries to access → Should FAIL
    user_b = User(id="user-b", clinic_id="clinic-2")
    result = get_document(doc.id, clinic_id=user_b.clinic_id)
    assert result is None, "Data leakage: User B can see Clinic A's document"

def test_superadmin_bypass():
    # SUPERADMIN can see all clinics
    superadmin = User(id="admin", roles=[UserRole.SUPERADMIN])
    all_docs = list_documents(user_id=superadmin.id, clinic_id=None, roles=superadmin.roles)
    assert len(all_docs) > 0, "SUPERADMIN should see all clinics"
```

### Integration Tests

1. **Create 2 test clinics:**
   - clinic-test-1 (Doctor A, Patient A1, Patient A2)
   - clinic-test-2 (Doctor B, Patient B1, Patient B2)

2. **Test data isolation:**
   - Doctor A lists patients → Only sees A1, A2 (NOT B1, B2)
   - Doctor A searches documents → Only sees clinic-1 documents
   - Doctor A views appointments → Only sees clinic-1 appointments

3. **Test impersonation prevention:**
   - Doctor A sends request with `{"clinic_id": "clinic-test-2"}` → 403 Forbidden
   - Doctor A tries to access Patient B1 session → 404 Not Found

---

## Security Considerations

### Attack Vectors to Prevent

1. **Horizontal Privilege Escalation:**
   - Doctor A modifies request to include `clinic_id: "clinic-2"`
   - Mitigation: Validate ALL user-provided clinic_id against `current_user.clinic_id`

2. **Data Leakage via Search:**
   - Semantic search returns documents from all clinics
   - Mitigation: Add clinic_id filter to vector search queries

3. **Audit Trail Pollution:**
   - User actions logged without clinic_id → can't trace per-clinic
   - Mitigation: Include clinic_id in all audit events (Phase 3: Audit Logging)

4. **SUPERADMIN Abuse:**
   - SUPERADMIN switches clinics without logging
   - Mitigation: Log `clinic_id_accessed` in admin actions (forensics)

---

## Rollout Plan

### Step 1: Add clinic_id Parameter (No Breaking Changes)

```python
# OLD signature (still works)
def list_documents(owner_user_id: str) -> list[Document]:
    pass

# NEW signature (backward compatible via default)
def list_documents(owner_user_id: str, clinic_id: str | None = None) -> list[Document]:
    if clinic_id:
        # Apply filter
        ...
    # Legacy path (no filter)
    ...
```

### Step 2: Deprecate Unfiltered Queries

```python
def list_documents(owner_user_id: str, clinic_id: str | None = None) -> list[Document]:
    if clinic_id is None:
        logger.warning("DEPRECATED: list_documents without clinic_id (data leakage risk)")
        # Still works but logged
    ...
```

### Step 3: Enforce clinic_id Required

```python
def list_documents(owner_user_id: str, clinic_id: str) -> list[Document]:
    # clinic_id now required (breaking change)
    ...
```

---

## Verification Checklist

Before deploying Phase 2:

- [ ] All 19 files audited for clinic_id usage
- [ ] High-priority endpoints (documents, appointments, users) have clinic_id filters
- [ ] SUPERADMIN bypass logic tested (can see all clinics)
- [ ] User-provided clinic_id validated against Auth0 token
- [ ] Integration tests pass (2 test clinics, data isolation verified)
- [ ] Security review: No horizontal privilege escalation possible
- [ ] Audit logging includes clinic_id in all events (Phase 3)

---

## Next Steps (After Phase 2)

**Phase 3: Audit Logging Centralization**
- Centralize all audit events via AuditService
- Include clinic_id in every audit event
- Enable per-clinic audit trail queries

**Phase 4: Admin Dashboard**
- SUPERADMIN can switch clinics (view-only mode)
- Clinic-level analytics (patients, sessions, storage usage)
- Clinic isolation metrics (verify no leaks)

---

## References

- Phase 1 Commit: 430052d9 (Auth0 clinic_id extraction)
- User Entity: `backend/infrastructure/auth/domain/entities/user.py:51`
- Auth0Provider: `backend/infrastructure/auth/infrastructure/auth0/auth0_provider.py:32-33`
- Documents API: `backend/services/document/api/public/documents.py:277`
- Questionnaire Response: "Extract clinic_id from Auth0 app_metadata"

---

**Status:** Phase 1 Complete ✅, Phase 2 Documented (Ready for Implementation)
**Estimated Effort:** 2-3 hours (19 files, pattern-based refactor)
**Risk:** High (data leakage if not implemented correctly)

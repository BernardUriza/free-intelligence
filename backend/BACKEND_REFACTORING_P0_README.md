# Free Intelligence Backend Refactoring - Phase 0 (P0)

This document summarizes the Phase 0 refactoring of the Free Intelligence backend, focusing on organizing services and APIs into a modular, domain-driven architecture.

## Objectives

1. **Analyze existing structure**: Catalog all services and API endpoints
2. **Classify by domain**: Group functionality by business domain
3. **Create migration plan**: Define mapping and strategy for moving to new structure
4. **Generate automation**: Create scripts to assist with migration process

## Deliverables

### 1. SERVICES_MIGRATION_MAP.md
- Located at: `backend/SERVICES_MIGRATION_MAP.md`
- Contains detailed mapping of all services from `backend/services/` to `backend/src/fi_DOMAIN/services/`
- Services classified by domain (auth, storage, llm, transcription, soap_generation, etc.)
- Includes dependency considerations and migration order

### 2. API_MIGRATION_MAP.md
- Located at: `backend/API_MIGRATION_MAP.md`
- Contains mapping of API endpoints from `backend/api/` to `backend/src/fi_DOMAIN/api/(public|internal)/`
- Distinguishes between public (CORS-enabled) and internal (localhost-only) endpoints
- Organized by functional areas and subdomains

### 3. migration_p0.sh
- Located at: `backend/migration_p0.sh`
- Bash script that automates the migration of files to new structure
- Updates import statements to reflect new module paths
- Preserves functionality while improving organization

## Key Changes in New Structure

### Services Organization
- Each domain gets its own module: `fi_domain_name`
- Services organized under `backend/src/fi_DOMAIN/services/`
- Related subcomponents grouped appropriately (e.g., `fi_llm/services/persona/`)

### API Organization
- Public APIs under `backend/src/fi_DOMAIN/api/public/`
- Internal APIs under `backend/src/fi_DOMAIN/api/internal/`
- Clear separation between external and internal functionality

## Migration Strategy

1. **Create new directory structure**
2. **Move services with import updates**
3. **Update cross-module dependencies**
4. **Verify functionality after each migration step**
5. **Update tests and documentation**

## Next Steps

1. Review the generated mapping documents for accuracy
2. Test the migration script in a development environment
3. Execute migration in phases with thorough testing
4. Update documentation to reflect new structure
5. Adjust CI/CD pipelines for new file locations

## Validation Checklist

- [ ] All services mapped correctly in `SERVICES_MIGRATION_MAP.md`
- [ ] All API endpoints mapped correctly in `API_MIGRATION_MAP.md`
- [ ] Migration script is executable and functional
- [ ] Import statements are updated to use new paths
- [ ] Cross-module dependencies are maintained
- [ ] Tests pass after migration
- [ ] Documentation updated to reflect new structure

## Notes

This refactoring maintains all existing functionality while improving maintainability and scalability through clearer domain separation. The migration script is provided for automation but should be tested thoroughly in a development environment before production use.
# Backend Refactoring Plan

## Current State Analysis

### Directory Structure
The backend currently has a hybrid architecture with both legacy and modern components:
- **Legacy Directories**: Traditional Django/Flask-style directories (api, services, models, etc.)
- **Modern Packages**: Modular, domain-driven design packages in `src/`

### File Count Summary
Based on analysis of the backend directory:

#### Legacy Directories (Traditional Structure):
- api/: 90 Python files (public and internal API routes/endpoints)
- services/: 80 Python files (business logic)
- models/: 8 Python files (data models)
- repositories/: 5 Python files (data access layer)
- schemas/: 15 Python files (validation schemas, JSON schemas, etc.)
- middleware/: 4 Python files (request/response processing)
- config/: 2 Python files (configuration management)
- utils/: 9 Python files (utility functions)
- security/: 3 Python files (security-related utilities)
- workers/: 2 Python files (async/background job processors)
- providers/: 6 Python files (external service integrations)
- observability/: 3 Python files (logging, monitoring)
- policy/: 5 Python files (policy enforcement)
- validators/: 1 Python file (validation logic)
- clients/: 1 Python file (client SDKs for internal services)
- debug/: 3 Python files (debugging tools)
- scripts/: 4 Python files (admin scripts)
- tools/: 7 Python files (development utilities)
- cli/: 4 Python files (command-line interface)
- workflows_core/: 1 Python file (workflow engine)
- tests/: 21 Python files (unit and integration tests)

#### Modern Packages (Domain-Driven Design):
- src/fi_auth/: 23 Python files (authentication & authorization)
- src/fi_cli/: 12 Python files (command line interfaces)
- src/fi_coder/: 49 Python files (code analysis and manipulation)
- src/fi_common/: 23 Python files (common utilities & shared code)
- src/fi_devtools/: 35 Python files (development tools)
- src/fi_observability/: 12 Python files (monitoring & observability)
- src/fi_storage/: 25 Python files (data persistence & storage)

### Identified Issues

#### 1. Duplication and Conflicts
- Authentication logic exists in both `backend/auth` (legacy) and `backend/src/fi_auth` (modern)
- Storage/handling logic potentially duplicated between `backend/storage` and `backend/src/fi_storage`
- Common utilities scattered across `backend/utils` (legacy) and `backend/src/fi_common` (modern)
- Client implementations in both `backend/clients` (legacy) and potentially `backend/src/fi_common` (modern)
- Based on project documentation, there's also potential overlap in:
  - LLM integration services between legacy `providers/llm.py` and modern packages
  - Audio transcription services between legacy `services/transcription_service.py` and modern storage packages
  - Audit functionality across legacy `repositories/audit_repository.py` and `services/audit_service.py` vs modern packages

#### 2. Unclear Boundaries
- Business logic is mixed between services (legacy) and domain packages (modern)
- API endpoints reference both legacy models and modern packages inconsistently
- Configuration is spread across both legacy (`config/`) and modern structures
- According to project documentation, there are also:
  - Two API layers (Public API and Internal API) that may not align well with the modern package structure
  - Event-sourced architecture with HDF5 storage that should be consolidated in the modern `fi_storage` package

#### 3. Maintenance Challenges
- Developers must navigate both legacy and modern structures
- Risk of implementing features in wrong layer
- Hard to maintain consistent coding standards across both approaches
- Testing becomes complex due to dual architecture
- New team members face confusion about which components to use

## Refactoring Objectives

1. **Consolidate Codebase**: Move all functionality to the modern `src/` structure
2. **Eliminate Duplications**: Merge overlapping functionality
3. **Establish Clear Architecture**: Define clear boundaries between domains
4. **Improve Maintainability**: Single source of truth for each responsibility
5. **Align with HIPAA/Event-Sourcing Goals**: Ensure the modern structure supports the project's event-sourced, HIPAA-compliant architecture using HDF5 storage
6. **Streamline API Operations**: Create clear pathways between public/internal APIs and underlying services

## Refactoring Plan

### Phase 1: Assessment & Preparation (P0 - Immediate Priority)
1. **Audit Dependencies**: Map all inter-dependencies between legacy and modern packages
2. **Identify Entry Points**: Locate all API endpoints and their respective service dependencies
3. **Backup Current State**: Ensure we have a working backup before changes
4. **Create Migration Checklist**: Detailed list of modules to migrate

### Phase 2: Core Service Migration (P0 - Critical Path)
1. **Migrate Services Layer**:
   - Move business logic from `backend/services` to appropriate modern packages
   - Create new service classes within modern packages if needed
   - Update API endpoints to reference new service locations
   - Pay special attention to critical services like `transcription_service.py`, `llm_model_service.py`, `session_service.py`, and `audit_service.py`
2. **Update API Layer**:
   - Refactor API endpoints to use modern service packages
   - Apply consistent error handling patterns from modern packages
   - Implement proper dependency injection
   - Ensure both Public API (`/api/workflows/aurity/*`) and Internal API (`/internal/*`) correctly integrate with modern packages
3. **Migrate Data Access**:
   - Integrate repositories/models into modern packages where appropriate
   - Consider whether to merge with `fi_storage` or create domain-specific repos
   - Ensure HDF5-based append-only storage policies are handled consistently in the modern `fi_storage` package

### Phase 3: Infrastructure Migration (P1 - High Priority)
1. **Configuration Management**:
   - Consolidate config packages to use modern approach
   - Update environment variable handling
2. **Middleware Integration**:
   - Adapt legacy middleware to work with modern architecture
   - Consider converting to decorators or similar patterns from modern packages
3. **Utilities Unification**:
   - Move utilities from `backend/utils` to `backend/src/fi_common`
   - Remove redundant functionality

### Phase 4: Domain Package Enhancement (P1 - High Priority)
1. **Expand Package Scope**:
   - Extend `fi_coder`, `fi_observability`, `fi_storage` to handle more responsibilities
   - Ensure each package follows single-responsibility principle
2. **Standardize Interfaces**:
   - Apply consistent API patterns across all packages
   - Implement common base classes where appropriate

### Phase 5: Legacy Code Removal (P2 - Lower Priority)
1. **Remove Obsolete Directories**:
   - Delete `backend/api`, `backend/services`, `backend/models`, etc. after full migration
   - Handle any remaining references carefully
2. **Clean Up Dependencies**:
   - Update import paths throughout codebase
   - Remove legacy-specific configurations

## Priority Classifications

### P0 (Immediate/Mandatory for stability)
1. Migrate core services (especially transcription_service, llm_model_service, session_service, audit_service) - these are critical for the AI consultation workflow
2. Update API endpoints to modern service packages, ensuring both Public API (`/api/workflows/aurity/*`) and Internal API (`/internal/*`) work correctly
3. Integrate authentication systems between legacy and modern packages, ensuring HIPAA compliance is maintained
4. Resolve any circular dependencies, particularly those involving the HDF5-based storage system
5. Ensure event-sourced architecture with append-only policies continue to work properly after migration

### P1 (High importance for maintainability)
1. Consolidate data models and repositories
2. Standardize configuration handling
3. Migrate utility functions to modern packages
4. Enhance observability across all packages

### P2 (Improvements for long-term sustainability)
1. Clean up deprecated code paths
2. Refactor testing structure to align with new architecture
3. Documentation updates
4. Performance optimizations based on new architecture

## Risk Mitigation

### Potential Risks
1. **Breaking API Changes**: Migrating services might affect API contracts
2. **Performance Degradation**: New architecture could introduce inefficiencies
3. **Dependency Complexity**: Moving code might create new dependency chains
4. **Team Learning Curve**: Developers need to adapt to new architecture

### Mitigation Strategies
1. **Gradual Migration**: Use feature flags and gradual rollouts
2. **Comprehensive Testing**: Maintain test coverage during migration
3. **Documentation**: Update architecture documentation
4. **Monitoring**: Implement metrics to detect performance regressions
5. **Rollback Plan**: Maintain ability to revert migrations if needed

## Success Metrics

1. **Code Quality**: Reduced complexity scores, improved maintainability
2. **Performance**: Same or improved response times
3. **Test Coverage**: Maintain or improve test coverage percentages
4. **Developer Productivity**: Reduced time to implement new features
5. **Architecture Clarity**: Clear boundaries between domains
6. **HIPAA Compliance**: Continued adherence to privacy and security requirements
7. **Workflow Integrity**: Smooth operation of AI consultation flows (audio transcription, SOAP note generation, etc.)
8. **Data Integrity**: Proper functioning of event-sourced HDF5 storage with append-only policies
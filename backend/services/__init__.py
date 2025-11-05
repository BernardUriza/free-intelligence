"""Service layer for business logic.

Contains domain services that orchestrate repository operations
and implement business rules.

Clean Code Principles:
- Separation of Concerns: Business logic separated from persistence
- Single Responsibility: Each service handles one domain
- Dependency Injection: Services receive dependencies, don't create them
"""

# Services are imported on-demand by containers and dependency injection
# This prevents circular imports during module initialization

__all__ = []

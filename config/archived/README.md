# Archived Configuration Files

This folder contains historical configuration files that were removed during codebase cleanup but may be useful for reference.

## Files

### `error_budgets.yaml`
- **Original location**: `observability/error_budgets.yaml`
- **Removed**: 2025-11-17 (commit 4383c3d)
- **Purpose**: Error budget definitions for observability and SLO monitoring
- **Status**: Archived for reference (observability/ folder removed during mega cleanup)

### `Pulumi.yaml` and `Pulumi.dev.yaml`
- **Original location**: `pulumi-do/Pulumi.yaml`, `pulumi-do/Pulumi.dev.yaml`
- **Removed**: 2025-11-17 (commit 4383c3d)
- **Purpose**: Infrastructure as Code configuration for DigitalOcean deployment
- **Status**: Archived (IaC moved to manual deployment scripts)

## Notes

- These files are kept for **historical reference only**
- Not actively used in current deployment workflow
- Current deployment uses: `scripts/deploy-*.py` (manual SCP deployment)
- For active policies, see: `config/fi.policy.yaml`

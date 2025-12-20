# fi_cli

CLI unificada para AURITY (multi-dominio), diseñada para consolidar y migrar
scripts legacy dispersos hacia un sistema tipado, testeable y extensible.

## Ejecución

- `PYTHONPATH=backend/src python3.14 -m fi_cli --help`
- `PYTHONPATH=backend/src python3.14 -m fi_cli dev all`

## Dominios

- `dev`: flujos locales (arranque/parada).
- `ops`: inspección operativa y health checks.
- `deploy`: despliegues/restarts.
- `auth`: Auth0/RBAC.
- `data`: HDF5/corpus/migraciones.
- `infra`: NAS/NFS/SMB, firewall, TLS.

## Estado de migración

Migración en progreso (AUR-PROMPT-CLI-1.0). Comandos migrados desde `scripts/`:

### ✅ Completado
**Dev (6 scripts):**
- `scripts/dev-all.sh` → `fi_cli dev all`
- `scripts/dev-start.sh` → `fi_cli dev start`
- `scripts/dev-stop.sh` → `fi_cli dev stop`
- `scripts/sprint-close.sh` → `fi_cli dev sprint-close`
- `scripts/install_hooks.sh` → `fi_cli dev install-hooks`
- `scripts/validate_commit_message.py` → `fi_cli dev validate-commit-message`

**Ops (16 scripts):**
- `scripts/tail-backend-logs*.py` → `fi_cli ops tail-backend-logs`
- `scripts/get-backend-startup-logs.py` → `fi_cli ops backend-startup-logs`
- `scripts/verify-backend-health.py` → `fi_cli ops backend-health`
- `scripts/check-backend-logs.py` → `fi_cli ops check-backend-logs`
- `scripts/check-prod-logs-detailed.py` → `fi_cli ops check-prod-logs-detailed`
- `scripts/check-recent-errors.py` → `fi_cli ops check-recent-errors`
- `scripts/diagnose-nginx-static.py` → `fi_cli ops diagnose-nginx-static`
- `scripts/fix-auth0-audience.py` → `fi_cli ops fix-auth0-audience`
- `scripts/fix-firewall-production.py` → `fi_cli ops fix-firewall-production`
- `scripts/fix-nginx-cache-headers.py` → `fi_cli ops fix-nginx-cache-headers`
- `scripts/fix-permissions-images.py` → `fi_cli ops fix-permissions-images`
- `scripts/tail-backend-logs-live.py` → `fi_cli ops tail-backend-logs-live`
- `scripts/tail-backend-logs.py` → `fi_cli ops tail-backend-logs`
- `scripts/check-missing-files.py` → `fi_cli ops check-missing-files`
- `scripts/test-assistant-api.sh` → `fi_cli ops test-assistant-api`
- `scripts/manual_e2e_curl.sh` → `fi_cli ops test-e2e-curl`

**Auth (6 scripts):**
- `scripts/assign_superadmin_role.py` → `fi_cli auth assign-superadmin`
- `scripts/link_auth0_accounts.py` → `fi_cli auth link-accounts`
- `scripts/verify-auth0-audience.py` → `fi_cli auth verify-audience`
- `scripts/setup_auth0_action.py` → `fi_cli auth setup-auth0-action`
- `scripts/migrate_roles_fm_to_fi.py` → `fi_cli auth migrate-roles-fm-to-fi`
- `scripts/patch-auth0-config-server.py` → `fi_cli auth patch-auth0-config`

**Deploy (10 scripts):**
- `scripts/restart-backend-production.py` → `fi_cli deploy restart-backend-production`
- `scripts/setup-backend-service.sh` → `fi_cli deploy setup-backend-service`
- `scripts/setup-https-app-aurity.py` → `fi_cli deploy setup-https-production`
- `scripts/start-backend-production.py` → `fi_cli deploy start-backend-production`
- `scripts/deploy-auth0-config-fix.py` → `fi_cli deploy auth0-config-fix`
- `scripts/deploy-auth0-correct-domain.py` → `fi_cli deploy auth0-correct-domain`
- `scripts/deploy-backend-fix-hdf5.py` → `fi_cli deploy backend-fix-hdf5`
- `scripts/deploy-frontend-eruda.py` → `fi_cli deploy deploy-frontend-eruda`
- `scripts/deploy-ds923.sh` → `fi_cli deploy deploy-ds923`
- `scripts/setup-app-aurity-ssl.sh` → `fi_cli deploy setup-ssl-production`

**Data (8 scripts):**
- `scripts/consolidate_sessions.py` → `fi_cli data consolidate-sessions`
- `scripts/inspect_corpus.py` → `fi_cli data inspect-corpus`
- `scripts/check-h5-chunks.py` → `fi_cli data check-chunks`
- `scripts/process_remaining_chunks.py` → `fi_cli data process-remaining-chunks`
- `scripts/migrate_conversation_capture.py` → `fi_cli data migrate-conversation-capture`
- `scripts/create_test_appointments.sh` → `fi_cli data create-test-appointments`
- `scripts/migrate_tv_content_seeds.py` → `fi_cli data migrate-tv-content-seeds`
- `scripts/test-appointments-api.sh` → `fi_cli data test-appointments-api`

**Infra (8 scripts):**
- `scripts/nas-setup.sh` → `fi_cli infra nas-setup`
- `scripts/ufw-setup.sh` → `fi_cli infra setup-firewall`
- `scripts/generate-tls-cert.sh` → `fi_cli infra tls-cert`
- `scripts/fix-firewall-production.py` → `fi_cli infra fix-firewall`
- `scripts/nfs-setup.sh` → `fi_cli infra setup-nfs`
- `scripts/smb-setup.sh` → `fi_cli infra setup-smb`
- `scripts/validate-nas-deployment.sh` → `fi_cli infra validate-nas-deployment`
- `scripts/test-tls.sh` → `fi_cli infra test-tls`

### ✅ Migración completada (2025-12-18)

**Subdirectorios movidos:**
- `scripts/debug/` → `backend/debug/` (3 archivos)
- `scripts/dev-tests/` → `backend/tests/integration/` (3 archivos)
- `scripts/hooks/` → `.git/hooks/` (2 archivos)

**Total migrado:** 60+ scripts → 55+ comandos CLI + 8 archivos auxiliares relocalizados.

Directorio `scripts/` eliminado del repositorio.

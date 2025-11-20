#!/usr/bin/env python3
"""
Migrate Auth0 roles from FM-* (FerboliMovil) to FI-* (Free Intelligence)

This script:
1. Gets all users with FM-* roles
2. Maps FM-* to FI-* equivalents
3. Removes old FM-* roles and assigns new FI-* roles
4. Assigns FI-superadmin to bernarduriza@gmail.com

Usage:
    python3 scripts/migrate_roles_fm_to_fi.py

Author: Bernard Uriza
Date: 2025-11-20
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from backend.services.auth0_management import get_auth0_service

logger = structlog.get_logger(__name__)

# Role mapping: FM-* → FI-*
ROLE_MAPPING = {
    "FM-Admin": "FI-admin",
    "FM-Doctor": "FI-doctor",
    "FM-Nurse": "FI-nurse",
    "FM-Staff": "FI-staff",
}

# Superadmin email
SUPERADMIN_EMAIL = "bernarduriza@gmail.com"


def migrate_roles():
    """Migrate all users from FM-* to FI-* roles"""

    service = get_auth0_service()

    print("=" * 70)
    print("🔄 MIGRACIÓN DE ROLES: FM-* → FI-*")
    print("=" * 70)
    print()

    # Step 1: Get all available roles
    print("📋 Obteniendo roles disponibles...")
    all_roles = service.list_roles()
    role_name_to_id = {r["name"]: r["id"] for r in all_roles}

    print(f"✅ Encontrados {len(all_roles)} roles totales")
    print(f"   Roles FI-*: {[r for r in role_name_to_id if r.startswith('FI-')]}")
    print(f"   Roles FM-*: {[r for r in role_name_to_id if r.startswith('FM-')]}")
    print()

    # Verify all FI-* roles exist
    missing_roles = []
    for fi_role in ROLE_MAPPING.values():
        if fi_role not in role_name_to_id:
            missing_roles.append(fi_role)

    if missing_roles:
        print("❌ ERROR: Faltan roles FI-* en Auth0:")
        for role in missing_roles:
            print(f"   - {role}")
        print()
        print("⚠️  Debes crear estos roles en Auth0 Dashboard primero:")
        print("   Auth0 Dashboard → User Management → Roles → Create Role")
        return

    # Step 2: Get all users
    print("👥 Obteniendo usuarios...")
    response = service.list_users(per_page=100)
    users = response.get("users", [])
    print(f"✅ Encontrados {len(users)} usuarios")
    print()

    # Step 3: Migrate each user
    migrated_count = 0
    skipped_count = 0
    superadmin_assigned = False

    for user in users:
        user_id = user["user_id"]
        email = user["email"]

        # Get current roles
        current_roles = service.get_user_roles(user_id)
        current_role_names = [r["name"] for r in current_roles]

        # Check if user has FM-* roles
        fm_roles = [r for r in current_role_names if r.startswith("FM-")]

        if not fm_roles and email != SUPERADMIN_EMAIL:
            print(f"⏭️  {email:40} → Sin roles FM-*, skipping")
            skipped_count += 1
            continue

        print(f"🔄 {email:40}")
        print(f"   Roles actuales: {', '.join(current_role_names) or '(ninguno)'}")

        # Build new role set
        roles_to_remove = []
        roles_to_add = []

        # Map FM-* to FI-*
        for fm_role in fm_roles:
            if fm_role in ROLE_MAPPING:
                fi_role = ROLE_MAPPING[fm_role]

                # Get role IDs
                fm_role_id = role_name_to_id[fm_role]
                fi_role_id = role_name_to_id[fi_role]

                roles_to_remove.append(fm_role_id)
                roles_to_add.append(fi_role_id)

                print(f"   📝 {fm_role} → {fi_role}")

        # Add FI-superadmin to bernarduriza@gmail.com
        if email == SUPERADMIN_EMAIL:
            if "FI-superadmin" in role_name_to_id:
                superadmin_id = role_name_to_id["FI-superadmin"]
                if superadmin_id not in roles_to_add:
                    roles_to_add.append(superadmin_id)
                    print("   ⭐ Asignando FI-superadmin")
                    superadmin_assigned = True

        # Execute migration
        try:
            if roles_to_remove:
                service.remove_roles(user_id, roles_to_remove)
                print(f"   ✅ Removidos {len(roles_to_remove)} roles FM-*")

            if roles_to_add:
                service.assign_roles(user_id, roles_to_add)
                print(f"   ✅ Asignados {len(roles_to_add)} roles FI-*")

            migrated_count += 1
            print()

        except Exception as e:
            print(f"   ❌ ERROR: {e!s}")
            print()
            continue

    # Summary
    print("=" * 70)
    print("📊 RESUMEN DE MIGRACIÓN")
    print("=" * 70)
    print(f"✅ Usuarios migrados: {migrated_count}")
    print(f"⏭️  Usuarios sin cambios: {skipped_count}")
    print(f"⭐ Superadmin asignado: {'Sí' if superadmin_assigned else 'No'}")
    print()
    print("🎉 Migración completada exitosamente!")
    print()

    # Verify
    print("🔍 Verificando resultados...")
    response = service.list_users(per_page=100)
    users = response.get("users", [])

    fi_role_count = 0
    fm_role_count = 0

    for user in users:
        roles = service.get_user_roles(user["user_id"])
        role_names = [r["name"] for r in roles]

        fi_roles = [r for r in role_names if r.startswith("FI-")]
        fm_roles = [r for r in role_names if r.startswith("FM-")]

        fi_role_count += len(fi_roles)
        fm_role_count += len(fm_roles)

    print(f"   Total roles FI-*: {fi_role_count}")
    print(f"   Total roles FM-*: {fm_role_count}")
    print()

    if fm_role_count > 0:
        print("⚠️  Aún existen roles FM-* asignados")
    else:
        print("✅ Todos los roles FM-* han sido migrados")


if __name__ == "__main__":
    try:
        migrate_roles()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migración cancelada por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR FATAL: {e!s}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

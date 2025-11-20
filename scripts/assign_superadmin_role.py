#!/usr/bin/env python3
"""
Assign FI-superadmin role to a user

This script:
1. Creates the FI-superadmin role if it doesn't exist
2. Assigns the role to the specified user (by email)

Usage:
    python3 scripts/assign_superadmin_role.py bernarduriza@gmail.com

Author: Bernard Uriza
Date: 2025-11-20
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.auth0_management import get_auth0_service


def main():
    """Assign superadmin role to user"""
    if len(sys.argv) < 2:
        print("❌ Usage: python3 scripts/assign_superadmin_role.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    print(f"🔧 Assigning FI-superadmin role to: {email}")
    print()

    try:
        service = get_auth0_service()

        # 1. Find user by email
        print(f"🔍 Searching for user: {email}...")
        response = service.list_users(search=f'email:"{email}"', per_page=1)
        users = response.get("users", [])

        if not users:
            print(f"❌ User not found: {email}")
            sys.exit(1)

        user = users[0]
        user_id = user["user_id"]
        print(f"✅ Found user: {user_id} ({user.get('name', 'No name')})")
        print()

        # 2. List all roles to find FI-superadmin
        print("🔍 Checking for FI-superadmin role...")
        all_roles = service.list_roles()
        superadmin_role = None

        for role in all_roles:
            if role["name"] == "FI-superadmin":
                superadmin_role = role
                break

        if not superadmin_role:
            # Create the role if it doesn't exist
            print("📝 Creating FI-superadmin role...")
            superadmin_role = service.create_role(
                name="FI-superadmin",
                description="Free Intelligence Superadmin - Full system access for user management and configuration",
            )
            print(f"✅ Role created: {superadmin_role['id']}")
        else:
            print(f"✅ Role exists: {superadmin_role['id']}")

        print()

        # 3. Check if user already has the role
        print("🔍 Checking current user roles...")
        current_roles = service.get_user_roles(user_id)
        role_names = [r.get("name") for r in current_roles]

        print(f"   Current roles: {role_names}")

        if "FI-superadmin" in role_names:
            print("⚠️  User already has FI-superadmin role!")
        else:
            # Assign the role
            print()
            print(f"🔗 Assigning FI-superadmin role to {email}...")
            service.assign_roles(user_id, [superadmin_role["id"]])
            print("✅ Role assigned successfully!")

        print()
        print("=" * 70)
        print("✅ SUPERADMIN ROLE ASSIGNMENT COMPLETE")
        print("=" * 70)
        print()
        print("🎯 Next steps:")
        print("   1. User must LOGOUT from AURITY")
        print("   2. User must LOGIN again to get a new JWT token with the role")
        print("   3. The token will now include the FI-superadmin role")
        print("   4. User Management page should now work")
        print()
        print(f"📧 User email: {email}")
        print(f"🆔 User ID: {user_id}")
        print(f"🔑 Role: FI-superadmin")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

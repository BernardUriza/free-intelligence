#!/usr/bin/env python3
"""
Link Auth0 Accounts (Merge Identities)

This script links two Auth0 accounts with the same email address,
consolidating them into a single user profile with multiple login methods.

Usage:
    python3 scripts/link_auth0_accounts.py

Primary account: google-oauth2|106469404976909684198 (keep this one)
Secondary account: auth0|652b5142ab01a819c304abe5 (will be linked to primary)

After linking:
- User can login with Google OR email/password
- Both methods access the same account
- Roles and metadata are preserved
- Secondary account becomes a "linked identity"

Author: Bernard Uriza
Date: 2025-11-20
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.auth0_management import get_auth0_service


def main():
    """Link Auth0 accounts"""
    # Primary account (Google OAuth - keep this one)
    primary_user_id = "google-oauth2|106469404976909684198"

    # Secondary account (Email/Password - will become linked identity)
    secondary_user_id = "auth0|652b5142ab01a819c304abe5"

    print("=" * 70)
    print("🔗 VINCULAR CUENTAS DE AUTH0")
    print("=" * 70)
    print()
    print("⚠️  ADVERTENCIA: Esta operación es IRREVERSIBLE")
    print()
    print(f"📧 Email: bernarduriza@gmail.com")
    print()
    print("🎯 Cuenta Principal (se mantiene):")
    print(f"   ID: {primary_user_id}")
    print("   Método: Google OAuth")
    print("   Roles: Superadministrador, Administrador")
    print()
    print("🔗 Cuenta Secundaria (se vincula):")
    print(f"   ID: {secondary_user_id}")
    print("   Método: Email/Password")
    print("   → Se convertirá en identidad alternativa")
    print()
    print("✅ Resultado:")
    print("   - Podrás hacer login con Google O email/password")
    print("   - Ambos métodos accederán a LA MISMA cuenta")
    print("   - Los roles se preservan en la cuenta principal")
    print()

    # Ask for confirmation
    response = input("¿Deseas continuar? (escribe 'VINCULAR' para confirmar): ")

    if response != "VINCULAR":
        print("\n❌ Operación cancelada")
        sys.exit(0)

    print()
    print("🔧 Procesando...")
    print()

    try:
        service = get_auth0_service()

        # Link the accounts
        # The secondary account's identity will be added to the primary account
        service.link_user_account(
            primary_user_id=primary_user_id,
            secondary_user_id=secondary_user_id
        )

        print("=" * 70)
        print("✅ CUENTAS VINCULADAS EXITOSAMENTE")
        print("=" * 70)
        print()
        print("🎯 Ahora puedes hacer login con:")
        print("   1. Google OAuth (bernarduriza@gmail.com)")
        print("   2. Email/Password (bernarduriza@gmail.com)")
        print()
        print("   → Ambos métodos accederán a LA MISMA cuenta")
        print()
        print("📝 Nota:")
        print("   - En User Management verás solo 1 cuenta")
        print("   - Esa cuenta tendrá 2 identidades vinculadas")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
